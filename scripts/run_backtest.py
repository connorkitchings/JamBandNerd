"""
Unified script to run a historical backtest for any band and model combination.

This script replaces the individual `backtest_<band>_<model>.py` files.
It iterates through historical shows, generates predictions for each, compares them
against the actual setlist, and saves the per-show accuracy metrics to the
`accuracy_per_show` table.

Usage:
  # Backtest the last 50 WSP shows with the CK+ model
  uv run python scripts/run_backtest.py --band wsp --model ckplus --shows 50

  # Backtest the Goose Notebook model over a specific date range
  uv run python scripts/run_backtest.py --band goose --model notebook --start 2023-01-01 --end 2023-12-31
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta, timezone
from typing import Any, Dict, List

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data
from src.jambandnerd.config import HISTORICAL_PREDICTION_RUNS_TABLE
from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.db.operations import (
    upsert_dataframe,
    upsert_historical_prediction_run,
)
from src.jambandnerd.models.accuracy import aggregate_metrics, compute_per_show_metrics
from src.jambandnerd.models.evaluation import (
    get_evaluation_reference_date,
    list_completed_shows,
    select_target_shows,
)
from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    list_backtest_models,
    serialize_model_predictions,
)
from src.jambandnerd.transformations.gaps import generate_model_data


def run_backtest(
    band: str,
    model: str,
    start: str | None,
    end: str | None,
    shows: int | None,
    exclusion_window: int,
    all_history: bool = False,
) -> None:
    """Run a backtest for a given band and model."""
    log_prefix = f"[{band.upper()}/{model.upper()}]"

    # 1. Fetch and prepare data
    print(f"{log_prefix} Fetching raw data...")
    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    sets_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))

    if shows_df.empty or sets_df.empty:
        print(f"{log_prefix} No data to backtest. Aborting.")
        return

    shows_df, sets_df = prepare_band_data(shows_df, sets_df, band=band)

    # 2. Determine target shows for backtesting
    completed_shows = list_completed_shows(shows_df, sets_df)

    if all_history:
        target_shows = select_target_shows(completed_shows, all_history=True)
        window_start = target_shows["show_date"].min()
        window_end = target_shows["show_date"].max()
        print(
            f"{log_prefix} Backtesting across full completed-show history: {len(target_shows)} shows from {window_start} to {window_end}"
        )
    elif shows and shows > 0:
        target_shows = select_target_shows(completed_shows, shows=shows)
        window_start = target_shows["show_date"].min()
        window_end = target_shows["show_date"].max()
        print(
            f"{log_prefix} Backtesting on last {len(target_shows)} completed shows from {window_start} to {window_end}"
        )
    else:
        start_d = (
            pd.to_datetime(start).date()
            if start
            else (date.today() - timedelta(days=365 * 10))
        )
        end_d = pd.to_datetime(end).date() if end else date.today()
        target_shows = select_target_shows(completed_shows, start=start, end=end)
        print(
            f"{log_prefix} Backtesting on {len(target_shows)} completed shows from {start_d} to {end_d}"
        )

    if target_shows.empty:
        print(f"{log_prefix} No shows found in the specified window.")
        return

    # 3. Initialize predictor
    definition = get_model_definition(model)
    if not definition.supports_backtest:
        raise ValueError(f"Model does not support backtests: {model}")
    kwargs: dict[str, Any] = {}
    if definition.supports_training:
        kwargs["persist_artifacts"] = False
    predictor = build_predictor(model, band=band, **kwargs)
    model_version = definition.version

    # 4. Run backtest loop
    per_show_results: List[Dict[str, Any]] = []
    for _, show_row in target_shows.iterrows():
        ref_date = show_row["show_date"]
        show_id = str(show_row["show_id"])

        # Stricter validation to skip rows with invalid date types
        if not isinstance(ref_date, date):
            print(
                f"{log_prefix} Skipping show_id {show_id} due to invalid date type: {type(ref_date)} (value: {ref_date})"
            )
            continue

        actual_songs = (
            sets_df.loc[sets_df["show_id"] == show_id, "song_name"]
            .dropna()
            .unique()
            .tolist()
        )
        # Skip shows with insufficient songs (but be more permissive)
        if not actual_songs or len(actual_songs) <= 2:
            print(
                f"{log_prefix} Skipping show {show_id} on {ref_date}: only {len(actual_songs)} songs"
            )
            continue

        try:
            prediction_date = get_evaluation_reference_date(ref_date)
            model_data = generate_model_data(
                shows_df,
                sets_df,
                prediction_date,
                exclusion_window=exclusion_window,
                band=band,
            )

            if definition.supports_training:
                predictor.train(model_data)
            prediction_output = predictor.predict(
                model_data=model_data,
                top_k=definition.default_top_k,
            )
            preds = (
                prediction_output[0]
                if isinstance(prediction_output, tuple)
                else prediction_output
            )

            if not preds:
                print(f"{log_prefix} No predictions generated for {ref_date}, skipping")
                continue

            serialized_predictions = serialize_model_predictions(model, preds)
            pred_songs = [
                prediction["song_name"] for prediction in serialized_predictions
            ]
        except (ValueError, AttributeError, KeyError, TypeError) as e:
            print(f"{log_prefix} Error generating predictions for {ref_date}: {e}")
            continue
        except Exception as e:
            print(f"{log_prefix} Unexpected error for {ref_date}: {e}")
            continue

        generated_at = pd.Timestamp.now(tz=timezone.utc).isoformat()
        prediction_run_id = upsert_historical_prediction_run(
            band=band,
            model_slug=model,
            model_version=model_version,
            reference_date=prediction_date.isoformat(),
            target_show_id=show_id,
            target_show_date=ref_date.isoformat(),
            generated_at=generated_at,
            predictions=serialized_predictions,
            actual_songs=actual_songs,
            table_name=HISTORICAL_PREDICTION_RUNS_TABLE,
        )

        show_metrics = {
            "band": band,
            "model_version": model_version,
            "show_id": show_id,
            "show_date": ref_date.isoformat(),
            "actual_song_count": len(actual_songs),
            "prediction_run_id": prediction_run_id,
            "evaluated_at": generated_at,
        }

        for k in [10, 25, 50]:
            metrics = compute_per_show_metrics(pred_songs, actual_songs, k)
            show_metrics[f"k{k}_hit"] = int(metrics["hit"])
            show_metrics[f"k{k}_matches"] = int(metrics["matches"])
            show_metrics[f"k{k}_precision"] = metrics["precision"]
            show_metrics[f"k{k}_recall"] = metrics["recall"]
            show_metrics[f"k{k}_f1"] = metrics["f1"]

        per_show_results.append(show_metrics)

    # 5. Save results and print summary
    if per_show_results:
        results_df = pd.DataFrame(per_show_results)
        print(
            f"{log_prefix} Saving {len(results_df)} per-show accuracy records to the database..."
        )
        upsert_dataframe(
            table_name="accuracy_per_show",
            df=results_df,
            conflict_columns=["band", "model_version", "show_id"],
        )
        print(f"{log_prefix} Save complete.")

        print(f"\n{log_prefix} --- Aggregate Metrics for Window ---")
        for k in [10, 25, 50]:
            agg_metrics_k = aggregate_metrics(
                [
                    {
                        "hit": r[f"k{k}_hit"],
                        "matches": r[f"k{k}_matches"],
                        "precision": r[f"k{k}_precision"],
                        "recall": r[f"k{k}_recall"],
                        "f1": r[f"k{k}_f1"],
                    }
                    for r in per_show_results
                ],
                k,
            )
            print(
                f"{log_prefix} K={k}: hit_rate={agg_metrics_k.hit_rate:.3f} avg_matches={agg_metrics_k.avg_matches:.3f} "
                f"precision={agg_metrics_k.precision:.3f} recall={agg_metrics_k.recall:.3f} f1={agg_metrics_k.f1:.3f}"
            )
    else:
        print(f"{log_prefix} No results generated from backtest.")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run a historical backtest for a specific band and model."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        choices=get_active_bands(),
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=[definition.slug for definition in list_backtest_models()],
        help="The model to backtest.",
    )
    parser.add_argument("--start", help="Start date for backtest window (YYYY-MM-DD).")
    parser.add_argument("--end", help="End date for backtest window (YYYY-MM-DD).")
    parser.add_argument(
        "--shows",
        type=int,
        help="Limit to the last N completed shows (overrides start/end).",
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=3,
        help="Number of recent shows to exclude songs from (default: 3).",
    )
    parser.add_argument(
        "--all-history",
        action="store_true",
        help="Backtest across all completed shows, ignoring --shows and date window arguments.",
    )
    args = parser.parse_args()

    run_backtest(
        band=args.band,
        model=args.model,
        start=args.start,
        end=args.end,
        shows=args.shows,
        exclusion_window=args.exclusion_window,
        all_history=args.all_history,
    )


if __name__ == "__main__":
    main()
