"""Reusable Phase B feature diagnostics.

Builds labeled training frames for recent target shows and reports feature
descriptives, label lift, and diagnostic LightGBM importance. Predictors can
expose a ``build_diagnostic_training_frame(model_data)`` method for custom
diagnostic-only features; otherwise this falls back to Deal/GBM-style
``_build_training_frame(model_data)``.

Usage:
    uv run python scripts/diagnose_phase_b_features.py \\
        --band billy \\
        --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictor \\
        --shows 100 \\
        --snapshot-root .snapshots/billy_phase_b
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import asdict, dataclass
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


def _build_predictor(
    predictor_class: Type[PredictionModel],
    *,
    band: str,
) -> PredictionModel:
    try:
        return predictor_class(band=band, persist_artifacts=False)
    except TypeError:
        return predictor_class(band=band)


def _load_frames(
    band: str,
    *,
    snapshot_root: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    return prepare_band_data(shows_df, sets_df, band=band)


def _feature_columns(predictor: PredictionModel, frame: pd.DataFrame) -> list[str]:
    configured = getattr(predictor, "diagnostic_feature_columns", None)
    if configured is None:
        configured = getattr(predictor, "feature_columns", None)
    if configured is not None:
        return [column for column in configured if column in frame.columns]

    excluded = {
        "song_name",
        "label",
        "target_show_index",
        "target_show_date",
        "_target_show_id",
    }
    return [
        column
        for column in frame.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(frame[column])
    ]


def _training_frame_for_model_data(
    predictor: PredictionModel,
    model_data: Any,
) -> pd.DataFrame:
    builder = getattr(predictor, "build_diagnostic_training_frame", None)
    if callable(builder):
        return builder(model_data)

    fallback = getattr(predictor, "_build_training_frame", None)
    if callable(fallback):
        frame, _summary = fallback(model_data)
        return frame

    raise TypeError(
        f"{type(predictor).__name__} does not expose a diagnostic training frame."
    )


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
    for index, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        target_show_date = show_row["show_date"]
        if not isinstance(target_show_date, date):
            target_show_date = pd.Timestamp(target_show_date).date()
        prediction_date = get_evaluation_reference_date(target_show_date)
        print(
            f"  [{index}/{total}] {target_show_date} "
            f"(show_id={show_row['show_id']})",
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
            frame = _training_frame_for_model_data(predictor, model_data)
        except Exception as exc:  # pragma: no cover - defensive CLI path
            print(f"\n  [WARN] {show_row['show_id']}: {exc}")
            continue

        if frame is None or frame.empty:
            continue
        frame = frame.copy()
        frame["_outer_target_show_id"] = str(show_row["show_id"])
        frame["_outer_target_show_date"] = target_show_date.isoformat()
        if "target_show_index" in frame.columns:
            frame["_diagnostic_group_id"] = (
                frame["_outer_target_show_id"].astype(str)
                + ":"
                + frame["target_show_index"].astype(str)
            )
        frames.append(frame)

    print()
    if not frames:
        raise RuntimeError("No diagnostic training frames produced.")
    return pd.concat(frames, ignore_index=True)


def _decile_lift(values: pd.Series, labels: pd.Series) -> tuple[list[float], float]:
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
    rates = [float(value) for value in grouped.tolist()]
    if len(rates) < 2:
        return rates, 0.0
    monotonicity = float(
        pd.Series(range(len(rates))).corr(pd.Series(rates), method="spearman")
    )
    if np.isnan(monotonicity):
        monotonicity = 0.0
    return rates, monotonicity


def _train_lgb_importance(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[dict[str, float], dict[str, float]] | None:
    if not _LGB_AVAILABLE:
        return None
    group_column = (
        "_diagnostic_group_id"
        if "_diagnostic_group_id" in frame.columns
        else "target_show_index"
    )
    required = {"label", group_column}
    if not required.issubset(frame.columns):
        return None

    sorted_frame = frame.sort_values(group_column).reset_index(drop=True)
    groups = sorted_frame.groupby(group_column, sort=False).size().tolist()
    labels = sorted_frame["label"].to_numpy(dtype=int)
    if labels.sum() == 0:
        return None

    x_values = sorted_frame[feature_columns].fillna(0.0).to_numpy(dtype=float)
    train_set = lgb.Dataset(x_values, label=labels, group=groups, free_raw_data=False)
    booster = lgb.train(
        {
            "objective": "rank_xendcg",
            "metric": "ndcg",
            "eval_at": [10, 25, 50],
            "num_leaves": 31,
            "learning_rate": 0.05,
            "min_data_in_leaf": 5,
            "verbose": -1,
            "seed": 42,
        },
        train_set,
        num_boost_round=200,
    )
    gain = booster.feature_importance(importance_type="gain").tolist()
    split = booster.feature_importance(importance_type="split").tolist()
    return (
        dict(zip(feature_columns, [float(value) for value in gain])),
        dict(zip(feature_columns, [float(value) for value in split])),
    )


def _compute_feature_stats(
    frame: pd.DataFrame,
    feature_columns: list[str],
    *,
    gain_importance: dict[str, float] | None,
    split_importance: dict[str, float] | None,
) -> list[FeatureStats]:
    labels = frame["label"].astype(float)
    n_rows = len(frame)
    stats: list[FeatureStats] = []
    for column in feature_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        nan_rate = float(values.isna().mean())
        filled = values.fillna(0.0)
        zero_rate = float((filled == 0).mean())
        if filled.nunique(dropna=False) < 2 or labels.nunique(dropna=False) < 2:
            corr = 0.0
        else:
            corr = float(filled.corr(labels))
            if np.isnan(corr):
                corr = 0.0
        rates, monotonicity = _decile_lift(values, labels)
        stats.append(
            FeatureStats(
                name=column,
                count=n_rows,
                mean=float(filled.mean()),
                std=float(filled.std(ddof=0)),
                min_v=float(filled.min()),
                max_v=float(filled.max()),
                zero_rate=zero_rate,
                nan_rate=nan_rate,
                label_corr=corr,
                monotonicity=monotonicity,
                gain_importance=(
                    gain_importance.get(column) if gain_importance is not None else None
                ),
                split_importance=(
                    split_importance.get(column)
                    if split_importance is not None
                    else None
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
    sorted_stats = sorted(stats, key=lambda item: -(item.gain_importance or 0.0))

    lines: list[str] = [
        f"# Phase B feature diagnostics - `{band}` / `{model_version}`",
        "",
        f"- predictor: `{predictor_path}`",
        f"- shows analyzed: {shows}",
        f"- training rows: {n_rows}",
        f"- overall positive rate: {positive_rate:.4f}",
        f"- feature count: {len(feature_columns)}",
        "- diagnostic LightGBM importance: " + ("yes" if gbm_used else "n/a"),
        "",
        "## Per-feature summary",
        "",
        "| feature | mean | std | zero% | nan% | corr(label) | monotonicity | gain | split |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for stat in sorted_stats:
        lines.append(
            "| `{name}` | {mean:.3f} | {std:.3f} | {zero:.1%} | {nan:.1%} "
            "| {corr:+.3f} | {mono:+.3f} | {gain} | {split} |".format(
                name=stat.name,
                mean=stat.mean,
                std=stat.std,
                zero=stat.zero_rate,
                nan=stat.nan_rate,
                corr=stat.label_corr,
                mono=stat.monotonicity,
                gain=_format_optional(stat.gain_importance, "{:.0f}"),
                split=_format_optional(stat.split_importance, "{:.0f}"),
            )
        )

    lines.extend(
        [
            "",
            "## Decile positive-rate lift",
            "",
            "Each row shows the per-decile fraction of rows that were actually "
            "played. Fewer than 10 cells means tied values collapsed buckets.",
            "",
        ]
    )
    for stat in sorted_stats:
        lines.append(f"### `{stat.name}` (mono={stat.monotonicity:+.3f})")
        lines.append("")
        if stat.decile_positive_rates:
            header = " | ".join(
                f"d{index + 1}" for index in range(len(stat.decile_positive_rates))
            )
            cells = " | ".join(f"{rate:.3f}" for rate in stat.decile_positive_rates)
            lines.append(f"| {header} |")
            lines.append(
                "| " + " | ".join(["---:"] * len(stat.decile_positive_rates)) + " |"
            )
            lines.append(f"| {cells} |")
        else:
            lines.append("| - |")
            lines.append("| ---: |")
            lines.append("| - |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def diagnose(
    *,
    band: str,
    predictor_path: str,
    shows: int,
    snapshot_root: str | None,
    out_dir: Path,
) -> tuple[Path, Path]:
    predictor_class = _load_predictor_class(predictor_path)
    shows_df, sets_df = _load_frames(band, snapshot_root=snapshot_root)
    completed = list_completed_shows(shows_df, sets_df)
    target_shows = select_target_shows(completed, shows=shows)
    if target_shows.empty:
        raise RuntimeError(f"No completed shows found for band '{band}'.")

    predictor = _build_predictor(predictor_class, band=band)
    model_version = str(getattr(predictor, "MODEL_VERSION", "unknown"))
    print(
        f"[{band.upper()}/{model_version}] Diagnosing {len(target_shows)} shows "
        f"({target_shows['show_date'].min()} - {target_shows['show_date'].max()})"
    )

    frame = _collect_training_frames(
        band=band,
        predictor=predictor,
        shows_df=shows_df,
        sets_df=sets_df,
        target_shows=target_shows,
    )
    if "label" not in frame.columns:
        raise RuntimeError("Diagnostic frame is missing required 'label' column.")

    feature_columns = _feature_columns(predictor, frame)
    if not feature_columns:
        raise RuntimeError("No numeric diagnostic feature columns found.")

    n_rows = len(frame)
    positive_rate = float(frame["label"].mean())
    importance = _train_lgb_importance(frame, feature_columns)
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

    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{band}_{model_version}_{len(target_shows)}shows"
    markdown_path = out_dir / f"{base_name}.md"
    json_path = out_dir / f"{base_name}.json"

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
    markdown_path.write_text(markdown)

    payload = {
        "band": band,
        "model_version": model_version,
        "predictor": predictor_path,
        "shows_analyzed": int(len(target_shows)),
        "training_rows": int(n_rows),
        "positive_rate": positive_rate,
        "feature_columns": feature_columns,
        "diagnostic_lightgbm_importance": gbm_used,
        "features": [asdict(stat) for stat in stats],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote diagnostic markdown to {markdown_path}")
    print(f"Wrote diagnostic JSON to {json_path}")
    return markdown_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--band", required=True)
    parser.add_argument(
        "--predictor",
        required=True,
        help="Dotted path to a PredictionModel subclass.",
    )
    parser.add_argument("--shows", type=int, default=50)
    parser.add_argument(
        "--snapshot-root",
        default=None,
        help="Local raw-table snapshot root. Omit to read from Supabase.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help=(
            "Output directory. Defaults to <snapshot-root>/diagnostics when a "
            "snapshot is used, otherwise diagnostics/."
        ),
    )
    args = parser.parse_args()

    snapshot_root = args.snapshot_root or None
    if args.out_dir:
        out_dir = Path(args.out_dir)
    elif snapshot_root:
        out_dir = Path(snapshot_root) / "diagnostics"
    else:
        out_dir = Path("diagnostics")

    diagnose(
        band=args.band,
        predictor_path=args.predictor,
        shows=args.shows,
        snapshot_root=snapshot_root,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
