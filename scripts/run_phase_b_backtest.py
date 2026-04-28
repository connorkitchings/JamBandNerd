"""Phase B per-band backtest runner.

Runs a walk-forward backtest for a specific predictor class and writes a
BacktestSummary JSON for use with promote_phase_b_winner.py.

Usage:
  uv run python scripts/run_phase_b_backtest.py \\
      --band goose \\
      --predictor jambandnerd.models.goose.model.GoosePredictor \\
      --shows 100 \\
      --out-dir backtests/

The resulting files are:
  backtests/goose_<model_version>_100shows.jsonl   (per-show metrics)
  backtests/goose_<model_version>_summary.json     (BacktestSummary)
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Type

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.models.accuracy import (
    BacktestSummary,
    aggregate_metrics,
    compute_per_show_metrics,
    compute_weighted_precision_score,
    dual_objective_score_for_band,
)
from jambandnerd.models.base import PredictionModel
from jambandnerd.models.evaluation import (
    get_evaluation_reference_date,
    list_completed_shows,
    select_target_shows,
)
from jambandnerd.transformations.gaps import generate_model_data
from scripts.common import fetch_table, prepare_band_data


def _load_predictor_class(dotted_path: str) -> Type[PredictionModel]:
    """Import a predictor class from a dotted module path."""
    if ":" in dotted_path:
        module_path, class_name = dotted_path.rsplit(":", 1)
    else:
        module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, PredictionModel)):
        raise TypeError(f"{dotted_path} must be a PredictionModel subclass")
    return cls


def run_phase_b_backtest(
    *,
    band: str,
    predictor_class: Type[PredictionModel],
    shows: int = 100,
    snapshot_root: str | None = None,
    out_dir: str = "backtests",
) -> BacktestSummary:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

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

    # Instantiate predictor — never persist artifacts during backtesting
    predictor = predictor_class(band=band, persist_artifacts=False)
    model_version: str = getattr(predictor, "MODEL_VERSION", "unknown")

    print(
        f"[{band.upper()}/{model_version}] Backtesting {len(target_shows)} shows "
        f"({target_shows['show_date'].min()} – {target_shows['show_date'].max()})"
    )

    per_show_records: list[dict[str, Any]] = []
    total = len(target_shows)

    for idx, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        ref_date = show_row["show_date"]
        show_id = str(show_row["show_id"])
        if not isinstance(ref_date, date):
            ref_date = pd.Timestamp(ref_date).date()

        print(
            f"  [{idx}/{total}] {ref_date} (show_id={show_id})",
            end="\r",
            flush=True,
        )

        actual_songs = (
            sets_df.loc[sets_df["show_id"] == show_id, "song_name"]
            .dropna()
            .unique()
            .tolist()
        )
        if not actual_songs or len(actual_songs) <= 2:
            continue

        prediction_date = get_evaluation_reference_date(ref_date)

        try:
            model_data = generate_model_data(
                shows_df, sets_df, prediction_date, band=band
            )
            predictor.train(model_data)
            predictions = predictor.predict(model_data, top_k=50)
            if not predictions:
                continue
            pred_songs = [p.song_name for p in predictions]
        except Exception as exc:
            print(f"\n  [WARN] {show_id}: {exc}")
            continue

        metrics_by_k = {
            k: compute_per_show_metrics(pred_songs, actual_songs, k)
            for k in [10, 25, 50]
        }
        per_show_records.append(
            {
                "show_id": show_id,
                "target_show_date": ref_date.isoformat(),
                "reference_date": prediction_date.isoformat(),
                "actual_song_count": len(actual_songs),
                "prediction_count": len(pred_songs),
                "metrics": {f"k{k}": v for k, v in metrics_by_k.items()},
            }
        )

    print()  # newline after progress line

    if not per_show_records:
        raise RuntimeError("Backtest produced no scored records.")

    # Write per-show JSONL
    per_show_path = out_path / f"{band}_{model_version}_{len(target_shows)}shows.jsonl"
    with per_show_path.open("w") as fh:
        for record in per_show_records:
            fh.write(json.dumps(record) + "\n")

    # Aggregate metrics
    n = len(per_show_records)
    agg: dict[int, Any] = {}
    for k in [10, 25, 50]:
        agg[k] = aggregate_metrics([r["metrics"][f"k{k}"] for r in per_show_records], k)

    p10 = agg[10].precision
    p25 = agg[25].precision
    p50 = agg[50].precision
    r10 = agg[10].recall
    r25 = agg[25].recall
    r50 = agg[50].recall
    weighted = compute_weighted_precision_score(p10, p25, p50)
    dual = dual_objective_score_for_band(p10, r50, band)

    summary = BacktestSummary(
        band=band,
        model_version=model_version,
        n_shows=n,
        p10=p10,
        p25=p25,
        p50=p50,
        r10=r10,
        r25=r25,
        r50=r50,
        weighted_score=weighted,
        dual_score=dual,
    )

    # Write BacktestSummary JSON
    summary_path = out_path / f"{band}_{model_version}_summary.json"
    import dataclasses

    summary_path.write_text(json.dumps(dataclasses.asdict(summary), indent=2))

    # Print summary
    print(f"\n[{band.upper()}/{model_version}] --- Aggregate Metrics (n={n}) ---")
    for k in [10, 25, 50]:
        m = agg[k]
        print(
            f"  K={k}: hit={m.hit_rate:.3f} matches={m.avg_matches:.3f} "
            f"p={m.precision:.3f} r={m.recall:.3f} f1={m.f1:.3f}"
        )
    print(
        f"\n  DUAL OBJECTIVE | {band} | p@10={p10:.3f} | r@50={r50:.3f} | "
        f"dual={dual:.3f} | weighted_p={weighted:.3f} | n={n}"
    )
    print(f"\n  Summary written to: {summary_path}")
    print(f"  Per-show metrics:   {per_show_path}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase B per-band backtest runner. Writes BacktestSummary JSON."
    )
    parser.add_argument(
        "--band", required=True, help="Band identifier (goose, phish, …)"
    )
    parser.add_argument(
        "--predictor",
        required=True,
        help=(
            "Dotted import path to a PredictionModel subclass, e.g. "
            "jambandnerd.models.goose.model.GoosePredictor"
        ),
    )
    parser.add_argument(
        "--shows", type=int, default=100, help="Number of recent shows to score."
    )
    parser.add_argument(
        "--snapshot-root", default=None, help="Local snapshot directory for raw tables."
    )
    parser.add_argument(
        "--out-dir", default="backtests", help="Output directory for result files."
    )
    args = parser.parse_args()

    predictor_class = _load_predictor_class(args.predictor)
    run_phase_b_backtest(
        band=args.band,
        predictor_class=predictor_class,
        shows=args.shows,
        snapshot_root=args.snapshot_root,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
