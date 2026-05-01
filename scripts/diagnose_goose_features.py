"""Goose feature diagnostics — descriptives, decile lift, and GBM importance.

Builds the augmented training frame for the last N target shows (using the same
predictor wiring as run_phase_b_backtest), then reports for each feature:

  * Descriptives: count, mean, std, min, max
  * Zero rate, NaN rate
  * Pearson correlation with the binary label
  * Decile-binned positive rate + Spearman monotonicity score
  * LightGBM gain / split importance (when the predictor is GBM-based)

Output is a markdown report under ``--out-dir`` (defaults to a
``diagnostics/`` subdir of ``--snapshot-root``).

Usage:
    uv run python scripts/diagnose_goose_features.py \\
        --band goose \\
        --predictor jambandnerd.models.goose.model.GooseGbmV2Predictor \\
        --shows 50 \\
        --snapshot-root .snapshots/goose_phase_b
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Type

import numpy as np
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.models.base import PredictionModel
from jambandnerd.models.evaluation import (
    get_evaluation_reference_date,
    list_completed_shows,
    select_target_shows,
)
from jambandnerd.models.gbm.predictor import BandGbmPredictor
from jambandnerd.transformations.gaps import generate_model_data
from scripts.common import fetch_table, prepare_band_data

try:
    import lightgbm as lgb

    _LGB_AVAILABLE = True
except ImportError:  # pragma: no cover
    lgb = None  # type: ignore[assignment]
    _LGB_AVAILABLE = False


@dataclass
class FeatureStats:
    name: str
    count: int
    mean: float
    std: float
    min_v: float
    max_v: float
    zero_rate: float
    nan_rate: float
    label_corr: float
    monotonicity: float
    gain_importance: float | None
    split_importance: float | None
    decile_positive_rates: list[float]


def _load_predictor_class(dotted_path: str) -> Type[PredictionModel]:
    if ":" in dotted_path:
        module_path, class_name = dotted_path.rsplit(":", 1)
    else:
        module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, PredictionModel)):
        raise TypeError(f"{dotted_path} must be a PredictionModel subclass")
    return cls


def _collect_training_frames(
    *,
    band: str,
    predictor: PredictionModel,
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    target_shows: pd.DataFrame,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    total = len(target_shows)
    for idx, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        ref_date = show_row["show_date"]
        if not isinstance(ref_date, date):
            ref_date = pd.Timestamp(ref_date).date()
        prediction_date = get_evaluation_reference_date(ref_date)
        print(
            f"  [{idx}/{total}] {ref_date} (show_id={show_row['show_id']})",
            end="\r",
            flush=True,
        )
        try:
            model_data = generate_model_data(
                shows_df,
                sets_df,
                prediction_date,
                band=band,
                target_show_context=show_row,
            )
            frame, _summary = predictor._build_training_frame(model_data)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"\n  [WARN] {show_row['show_id']}: {exc}")
            continue

        if frame is None or frame.empty:
            continue
        frame = frame.copy()
        frame["_target_show_id"] = str(show_row["show_id"])
        frames.append(frame)

    print()  # newline after progress
    if not frames:
        raise RuntimeError("No training frames produced — check snapshot/data.")
    return pd.concat(frames, ignore_index=True)


def _decile_lift(values: pd.Series, labels: pd.Series) -> tuple[list[float], float]:
    """Return (per-decile positive rate, Spearman monotonicity score).

    Empty buckets are dropped via duplicates='drop'. Monotonicity is the
    Spearman correlation between bucket index and per-bucket positive rate;
    NaN/0.0 when fewer than 2 buckets remain.
    """
    df = pd.DataFrame({"v": values.astype(float), "y": labels.astype(float)})
    df = df.dropna(subset=["v", "y"])
    if df.empty:
        return [], 0.0
    try:
        df["bin"] = pd.qcut(df["v"], q=10, duplicates="drop", labels=False)
    except ValueError:
        return [], 0.0
    if df["bin"].nunique() < 2:
        return [float(df["y"].mean())], 0.0
    grouped = df.groupby("bin")["y"].mean().sort_index()
    rates = [float(x) for x in grouped.tolist()]
    if len(rates) < 2:
        return rates, 0.0
    rank_idx = pd.Series(range(len(rates)))
    rank_rate = pd.Series(rates)
    mono = float(rank_idx.corr(rank_rate, method="spearman"))
    if np.isnan(mono):
        mono = 0.0
    return rates, mono


def _train_gbm_for_importance(
    frame: pd.DataFrame,
    feature_columns: list[str],
    *,
    n_estimators: int,
    num_leaves: int,
    learning_rate: float,
    min_data_in_leaf: int,
) -> tuple[dict[str, float], dict[str, float]] | None:
    if not _LGB_AVAILABLE:
        return None
    if "label" not in frame.columns or "target_show_index" not in frame.columns:
        return None
    sorted_frame = frame.sort_values("target_show_index").reset_index(drop=True)
    groups = sorted_frame.groupby("target_show_index", sort=False).size().tolist()
    X = sorted_frame[feature_columns].fillna(0.0).to_numpy(dtype=float)
    y = sorted_frame["label"].to_numpy(dtype=int)
    if y.sum() == 0:
        return None
    train_set = lgb.Dataset(X, label=y, group=groups, free_raw_data=False)
    params: dict[str, Any] = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "num_leaves": num_leaves,
        "learning_rate": learning_rate,
        "min_data_in_leaf": min_data_in_leaf,
        "verbose": -1,
    }
    booster = lgb.train(params, train_set, num_boost_round=n_estimators)
    gain = booster.feature_importance(importance_type="gain").tolist()
    split = booster.feature_importance(importance_type="split").tolist()
    return (
        dict(zip(feature_columns, [float(v) for v in gain])),
        dict(zip(feature_columns, [float(v) for v in split])),
    )


def _compute_feature_stats(
    frame: pd.DataFrame,
    feature_columns: list[str],
    *,
    gain_importance: dict[str, float] | None,
    split_importance: dict[str, float] | None,
) -> list[FeatureStats]:
    labels = frame["label"].astype(float)
    stats: list[FeatureStats] = []
    n = len(frame)
    for col in feature_columns:
        if col not in frame.columns:
            continue
        s = frame[col]
        s_num = pd.to_numeric(s, errors="coerce")
        nan_rate = float(s_num.isna().mean())
        s_filled = s_num.fillna(0.0)
        zero_rate = float((s_filled == 0).mean())
        try:
            corr = float(s_filled.corr(labels))
            if np.isnan(corr):
                corr = 0.0
        except Exception:  # pragma: no cover - defensive
            corr = 0.0
        rates, mono = _decile_lift(s_num, labels)
        stats.append(
            FeatureStats(
                name=col,
                count=n,
                mean=float(s_filled.mean()),
                std=float(s_filled.std(ddof=0)),
                min_v=float(s_filled.min()),
                max_v=float(s_filled.max()),
                zero_rate=zero_rate,
                nan_rate=nan_rate,
                label_corr=corr,
                monotonicity=mono,
                gain_importance=(
                    gain_importance.get(col) if gain_importance is not None else None
                ),
                split_importance=(
                    split_importance.get(col) if split_importance is not None else None
                ),
                decile_positive_rates=rates,
            )
        )
    return stats


def _format_optional(value: float | None, fmt: str = "{:.2f}") -> str:
    if value is None:
        return "n/a"
    return fmt.format(value)


def _render_markdown(
    *,
    band: str,
    model_version: str,
    predictor_path: str,
    shows: int,
    n_rows: int,
    positive_rate: float,
    feature_columns: list[str],
    stats: list[FeatureStats],
    gbm_used: bool,
) -> str:
    sort_key = (
        (lambda s: -(s.gain_importance or 0.0))
        if gbm_used
        else (lambda s: -abs(s.label_corr))
    )
    sorted_stats = sorted(stats, key=sort_key)

    lines: list[str] = []
    lines.append(f"# Goose feature diagnostics — `{model_version}`")
    lines.append("")
    lines.append(f"- predictor: `{predictor_path}`")
    lines.append(f"- band: `{band}`")
    lines.append(f"- shows analyzed: {shows}")
    lines.append(f"- training rows: {n_rows}")
    lines.append(f"- overall positive rate: {positive_rate:.4f}")
    lines.append(f"- feature count: {len(feature_columns)}")
    lines.append(
        "- gbm importance: " + ("yes" if gbm_used else "n/a (non-GBM predictor)")
    )
    lines.append("")
    lines.append("## Per-feature summary")
    lines.append("")
    lines.append(
        "Sorted by "
        + (
            "LightGBM gain importance (desc)."
            if gbm_used
            else "|label correlation| (desc)."
        )
    )
    lines.append("")
    lines.append(
        "| feature | mean | std | zero% | nan% | corr(label) | monotonicity | gain | split |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for s in sorted_stats:
        lines.append(
            "| `{name}` | {mean:.3f} | {std:.3f} | {zero:.1%} | {nan:.1%} "
            "| {corr:+.3f} | {mono:+.3f} | {gain} | {split} |".format(
                name=s.name,
                mean=s.mean,
                std=s.std,
                zero=s.zero_rate,
                nan=s.nan_rate,
                corr=s.label_corr,
                mono=s.monotonicity,
                gain=_format_optional(s.gain_importance, "{:.0f}"),
                split=_format_optional(s.split_importance, "{:.0f}"),
            )
        )

    lines.append("")
    lines.append("## Decile positive-rate lift")
    lines.append("")
    lines.append(
        "Each row shows the per-decile fraction of rows that were actually played "
        "(label=1). Bins collapse via `qcut(duplicates='drop')` for features with "
        "tied or sparse values; fewer than 10 cells means qcut collapsed buckets."
    )
    lines.append("")
    for s in sorted_stats:
        cells = " | ".join(f"{r:.3f}" for r in s.decile_positive_rates) or "—"
        lines.append(f"### `{s.name}`  (mono={s.monotonicity:+.3f})")
        lines.append("")
        lines.append(
            f"| {' | '.join(f'd{i + 1}' for i in range(len(s.decile_positive_rates)))} |"
        )
        if s.decile_positive_rates:
            lines.append(
                "| " + " | ".join(["---:"] * len(s.decile_positive_rates)) + " |"
            )
            lines.append(f"| {cells} |")
        else:
            lines.append("| — |")
            lines.append("| — |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def diagnose(
    *,
    band: str,
    predictor_path: str,
    shows: int,
    snapshot_root: str | None,
    out_path: Path,
) -> Path:
    predictor_class = _load_predictor_class(predictor_path)

    if snapshot_root:
        shows_rows = fetch_table(f"{band}_shows_raw", snapshot_root=snapshot_root)
        setlist_rows = fetch_table(f"{band}_setlists_raw", snapshot_root=snapshot_root)
    else:
        shows_rows = fetch_table(f"{band}_shows_raw")
        setlist_rows = fetch_table(f"{band}_setlists_raw")

    shows_df = pd.DataFrame(shows_rows)
    sets_df = pd.DataFrame(setlist_rows)
    if shows_df.empty or sets_df.empty:
        raise RuntimeError(f"No data found for band '{band}'.")

    shows_df, sets_df = prepare_band_data(shows_df, sets_df, band=band)
    completed = list_completed_shows(shows_df, sets_df)
    target_shows = select_target_shows(completed, shows=shows)
    if target_shows.empty:
        raise RuntimeError(f"No completed shows found for band '{band}'.")

    predictor = predictor_class(band=band, persist_artifacts=False)
    model_version: str = getattr(predictor, "MODEL_VERSION", "unknown")
    feature_columns = list(predictor.feature_columns)

    print(
        f"[{band.upper()}/{model_version}] Diagnosing {len(target_shows)} shows "
        f"({target_shows['show_date'].min()} – {target_shows['show_date'].max()}) "
        f"over {len(feature_columns)} features"
    )

    frame = _collect_training_frames(
        band=band,
        predictor=predictor,
        shows_df=shows_df,
        sets_df=sets_df,
        target_shows=target_shows,
    )

    n_rows = len(frame)
    positive_rate = float(frame["label"].mean()) if "label" in frame else 0.0

    importance: tuple[dict[str, float], dict[str, float]] | None = None
    gbm_used = False
    if isinstance(predictor, BandGbmPredictor):
        importance = _train_gbm_for_importance(
            frame,
            feature_columns,
            n_estimators=predictor.n_estimators,
            num_leaves=predictor.num_leaves,
            learning_rate=predictor.learning_rate,
            min_data_in_leaf=predictor.min_data_in_leaf,
        )
        gbm_used = importance is not None

    gain_importance, split_importance = (
        importance if importance is not None else (None, None)
    )

    stats = _compute_feature_stats(
        frame,
        feature_columns,
        gain_importance=gain_importance,
        split_importance=split_importance,
    )

    markdown = _render_markdown(
        band=band,
        model_version=model_version,
        predictor_path=predictor_path,
        shows=len(target_shows),
        n_rows=n_rows,
        positive_rate=positive_rate,
        feature_columns=feature_columns,
        stats=stats,
        gbm_used=gbm_used,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown)
    print(f"Wrote diagnostic report to {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--band", default="goose")
    parser.add_argument(
        "--predictor",
        default="jambandnerd.models.goose.model.GooseGbmV2Predictor",
        help="Dotted path to a PredictionModel subclass.",
    )
    parser.add_argument("--shows", type=int, default=50)
    parser.add_argument(
        "--snapshot-root",
        default=".snapshots/goose_phase_b",
        help="Local snapshot root (set to empty string to use Supabase).",
    )
    parser.add_argument(
        "--out-path",
        default=None,
        help=(
            "Markdown output path. Defaults to "
            "<snapshot-root>/diagnostics/<model_version>_<shows>shows.md"
        ),
    )
    args = parser.parse_args()

    snapshot_root = args.snapshot_root or None

    if args.out_path:
        out_path = Path(args.out_path)
    else:
        # Resolve model version by lightly inspecting the class
        cls = _load_predictor_class(args.predictor)
        model_version = getattr(cls, "MODEL_VERSION", "unknown")
        base = Path(snapshot_root or ".") / "diagnostics"
        out_path = base / f"{args.band}_{model_version}_{args.shows}shows.md"

    diagnose(
        band=args.band,
        predictor_path=args.predictor,
        shows=args.shows,
        snapshot_root=snapshot_root,
        out_path=out_path,
    )


if __name__ == "__main__":
    main()
