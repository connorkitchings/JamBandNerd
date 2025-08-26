from __future__ import annotations

import argparse
import os
import sys
from datetime import timezone
from typing import Any, Dict, List

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.models.accuracy import compute_per_show_metrics
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.transformations.gaps import generate_model_data
from scripts.common import fetch_table, prepare_band_data


def main() -> None:
    """Run a historical backtest for the Phish CK+ model."""
    parser = argparse.ArgumentParser(
        description="Run Phish CK+ model backtest and save per-show accuracy."
    )
    parser.add_argument(
        "--shows",
        type=int,
        default=100,
        help="Number of recent completed shows to evaluate.",
    )
    args = parser.parse_args()

    print("Fetching Phish data for backtest...")
    shows_df = pd.DataFrame(fetch_table("phish_shows_raw"))
    sets_df = pd.DataFrame(fetch_table("phish_setlists_raw"))

    if shows_df.empty or sets_df.empty:
        print("No data found for Phish. Aborting backtest.")
        return

    shows_df, sets_df = prepare_band_data(shows_df, sets_df)

    completed_show_ids = sets_df["show_id"].dropna().astype(str).unique().tolist()
    completed_shows = shows_df[shows_df["show_id"].isin(completed_show_ids)].copy()
    completed_shows = completed_shows.sort_values(["show_date", "show_id"])
    last_n_shows = completed_shows.tail(args.shows)
    ref_dates = sorted(last_n_shows["show_date"].unique())

    if not ref_dates:
        print("No completed show dates found to evaluate.")
        return

    print("Starting Phish CK+ model backtest...")

    predictor = CKPlusPredictor(min_plays_threshold=2, retired_gap_threshold=500)
    per_show_results: List[Dict[str, Any]] = []

    show_id_map = shows_df.set_index("show_date")["show_id"].to_dict()

    for ref_date in ref_dates:
        actual_songs = (
            sets_df.loc[sets_df["show_date"] == ref_date, "song_name"
        )
        .dropna()
        .unique()
        .tolist()
        if not actual_songs:
            continue

        show_id = show_id_map.get(ref_date)
        if not show_id:
            continue

        try:
            model_data = generate_model_data(shows_df, sets_df, ref_date)
            preds = predictor.predict(model_data=model_data, top_k=50)
            pred_songs = [p.song_name for p in preds]
        except ValueError as e:
            print(f"Skipping date {ref_date}: {e}")
            continue

        show_metrics = {
            "band": "phish",
            "model_version": "ckplus_v1",
            "show_id": int(show_id),
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

    if per_show_results:
        results_df = pd.DataFrame(per_show_results)
        print(f"Saving {len(results_df)} per-show accuracy records to the database...")
        upsert_dataframe(
            table_name="accuracy_per_show",
            df=results_df,
            conflict_columns=["band", "model_version", "show_id"],
        )
        print("Save complete.")

    print("\nBacktest data saved.")


if __name__ == "__main__":
    main()
