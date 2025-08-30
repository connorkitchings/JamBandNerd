"""Backtest WSP CK+ model over historical shows and save per-show accuracy."""
from __future__ import annotations

import argparse
from datetime import date, timedelta, timezone
from typing import Any, Dict, List
import os
import sys

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.models.accuracy import compute_per_show_metrics, aggregate_metrics
from src.jambandnerd.transformations.gaps import generate_model_data
from scripts.common import fetch_table


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backtest WSP CK+ model and save per-show accuracy"
    )
    parser.add_argument("--start", help="Start show date YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", help="End show date YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--shows",
        type=int,
        help="Limit to the last N completed shows (overrides start/end if provided)",
    )
    args = parser.parse_args()

    shows_df = pd.DataFrame(fetch_table("wsp_shows_raw"))
    sets_df = pd.DataFrame(fetch_table("wsp_setlists_raw"))

    if shows_df.empty or sets_df.empty:
        print("No data to backtest")
        return

    shows_df["_dt"] = pd.to_datetime(shows_df["show_date"]).dt.date
    shows_df["show_id"] = shows_df["show_id"].astype(str)

    # Determine target shows
    # Use only completed shows (i.e., appear in setlists table)
    completed_show_ids = (
        sets_df["show_id"].dropna().astype(str).unique().tolist()
    )
    completed_shows = (
        shows_df[shows_df["show_id"].astype(str).isin(completed_show_ids)]
        .copy()
        .sort_values(["_dt", "show_id"])  # chronological
    )

    if args.shows and args.shows > 0:
        target_shows = completed_shows.tail(args.shows)
        window_start = target_shows["_dt"].min()
        window_end = target_shows["_dt"].max()
        print(
            f"Backtesting WSP (CK+) on last {len(target_shows)} completed shows from {window_start} to {window_end}"
        )
    else:
        start_d = pd.to_datetime(args.start).date() if args.start else (date.today() - timedelta(days=365 * 5))
        end_d = pd.to_datetime(args.end).date() if args.end else date.today()
        target_shows = completed_shows[(completed_shows["_dt"] >= start_d) & (completed_shows["_dt"] <= end_d)]
        print(
            f"Backtesting WSP (CK+) on {len(target_shows)} completed shows from {start_d} to {end_d}"
        )

    predictor = CKPlusPredictor(retired_gap_threshold=150)
    per_show_results: List[Dict[str, Any]] = []

    show_info_map = shows_df.set_index("show_id")["show_date"].to_dict()
    sets_df["show_id"] = sets_df["show_id"].astype(str)
    sets_df["show_date"] = sets_df["show_id"].map(show_info_map)
    sets_df["_dt"] = pd.to_datetime(sets_df["show_date"], errors='coerce').dt.date

    for _, show_row in target_shows.iterrows():
        ref_date = show_row["_dt"]
        show_id = str(show_row["show_id"])  # already string

        # Actual setlist strictly for this show_id (avoid mixing multi-show dates)
        actual_songs = (
            sets_df.loc[sets_df["show_id"] == show_id, "song_name"].dropna().unique().tolist()
        )
        if not actual_songs:
            continue
        # Exclude shows with 5 or fewer total songs
        if len(actual_songs) <= 5:
            continue

        try:
            model_data = generate_model_data(shows_df, sets_df, ref_date)
            preds = predictor.predict(model_data=model_data, top_k=50)
            pred_songs = [p.song_name for p in preds]
        except ValueError as e:
            print(f"Skipping date {ref_date}: {e}")
            continue

        show_metrics = {
            "band": "wsp",
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

    print("\n--- Aggregate Metrics for Window (CK+)")
    for k in [10, 25, 50]:
        agg_metrics_k = aggregate_metrics([
            {"hit": r[f"k{k}_hit"], "matches": r[f"k{k}_matches"], "precision": r[f"k{k}_precision"], "recall": r[f"k{k}_recall"], "f1": r[f"k{k}_f1"]}
            for r in per_show_results
        ], k)
        print(f"K={k}: hit_rate={agg_metrics_k.hit_rate:.3f} avg_matches={agg_metrics_k.avg_matches:.3f} precision={agg_metrics_k.precision:.3f} recall={agg_metrics_k.recall:.3f} f1={agg_metrics_k.f1:.3f}")


if __name__ == "__main__":
    main()
