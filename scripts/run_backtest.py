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
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.models.accuracy import aggregate_metrics, compute_per_show_metrics
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.transformations.gaps import generate_model_data


def run_backtest(
    band: str,
    model: str,
    start: str | None,
    end: str | None,
    shows: int | None,
    exclusion_window: int,
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

    shows_df, sets_df = prepare_band_data(shows_df, sets_df)

    # 2. Determine target shows for backtesting
    completed_show_ids = sets_df["show_id"].dropna().astype(str).unique().tolist()
    completed_shows = (
        shows_df[shows_df["show_id"].isin(completed_show_ids)]
        .copy()
        .sort_values(["show_date", "show_id"])
    )

    if shows and shows > 0:
        target_shows = completed_shows.tail(shows)
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
        target_shows = completed_shows[
            (completed_shows["show_date"] >= start_d)
            & (completed_shows["show_date"] <= end_d)
        ]
        print(
            f"{log_prefix} Backtesting on {len(target_shows)} completed shows from {start_d} to {end_d}"
        )

    if target_shows.empty:
        print(f"{log_prefix} No shows found in the specified window.")
        return

    # 3. Initialize predictor
    if model == "notebook":
        predictor = NotebookPredictor()
        model_version = "notebook_v1"
    elif model == "ckplus":
        predictor = CKPlusPredictor(band=band)
        model_version = "ckplus_v1"
    else:
        raise ValueError(f"Invalid model: {model}")

    # 4. Run backtest loop
    per_show_results: List[Dict[str, Any]] = []
    for _, show_row in target_shows.iterrows():
        ref_date = show_row["show_date"]
        show_id = str(show_row["show_id"])

        # Stricter validation to skip rows with invalid date types
        if not isinstance(ref_date, date):
            print(f"{log_prefix} Skipping show_id {show_id} due to invalid date type: {type(ref_date)} (value: {ref_date})")
            continue

        actual_songs = (
            sets_df.loc[sets_df["show_id"] == show_id, "song_name"]
            .dropna()
            .unique()
            .tolist()
        )
        # Skip shows with insufficient songs (but be more permissive)
        if not actual_songs or len(actual_songs) <= 2:
            print(f"{log_prefix} Skipping show {show_id} on {ref_date}: only {len(actual_songs)} songs")
            continue

        try:
            # Use the day before the show for more realistic backtesting
            # This prevents data leakage from the actual show date
            prediction_date = ref_date - timedelta(days=1) if isinstance(ref_date, date) else ref_date
            model_data = generate_model_data(
                shows_df, sets_df, prediction_date, exclusion_window=exclusion_window
            )
            
            if model == "notebook":
                preds, _ = predictor.predict(model_data=model_data, top_k=50)
            else:
                preds = predictor.predict(model_data=model_data, top_k=50)
                
            if not preds:
                print(f"{log_prefix} No predictions generated for {ref_date}, skipping")
                continue
                
            pred_songs = [p.song_name for p in preds]
        except (ValueError, AttributeError, KeyError, TypeError) as e:
            print(f"{log_prefix} Error generating predictions for {ref_date}: {e}")
            continue
        except Exception as e:
            print(f"{log_prefix} Unexpected error for {ref_date}: {e}")
            continue

        # Convert show_id safely - handle both numeric and string IDs
        try:
            show_id_int = int(show_id)
        except (ValueError, TypeError):
            # If show_id is non-numeric (e.g., date strings), hash it to an integer
            import hashlib
            show_id_int = int(hashlib.md5(show_id.encode()).hexdigest()[:8], 16)
        
        show_metrics = {
            "band": band,
            "model_version": model_version,
            "show_id": show_id_int,
            "show_date": ref_date.isoformat(),
            "actual_song_count": len(actual_songs),
            "evaluated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
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
        choices=["goose", "eggy", "phish", "wsp", "billy", "um"],
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=["notebook", "ckplus"],
        help="The model to backtest.",
    )
    parser.add_argument(
        "--start", help="Start date for backtest window (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--end", help="End date for backtest window (YYYY-MM-DD)."
    )
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
    args = parser.parse_args()

    run_backtest(
        band=args.band,
        model=args.model,
        start=args.start,
        end=args.end,
        shows=args.shows,
        exclusion_window=args.exclusion_window,
    )


if __name__ == "__main__":
    main()
