"""Compute and save aggregate accuracy for the CK+ model over the last N completed shows."""
from __future__ import annotations

import argparse
from typing import Any, Dict, List
import pandas as pd
import os
import sys
from datetime import timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.models.accuracy import compute_per_show_metrics, aggregate_metrics
from src.jambandnerd.transformations.gaps import generate_model_data
from scripts.common import fetch_table


def main(args: argparse.Namespace) -> None:

    band = args.band.lower()
    client = get_supabase_client()
    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    sets_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))

    if shows_df.empty or sets_df.empty:
        print(f"No data to process for {band}.")
        return

    # Normalize column names for Phish data
    if "api_show_id" in shows_df.columns and "show_id" not in shows_df.columns:
        shows_df["show_id"] = shows_df["api_show_id"]
    if "api_show_id" in sets_df.columns and "show_id" not in sets_df.columns:
        sets_df["show_id"] = sets_df["api_show_id"]
    if "showdate" in shows_df.columns and "show_date" not in shows_df.columns:
        shows_df["show_date"] = shows_df["showdate"]
    if "song" in sets_df.columns and "song_name" not in sets_df.columns:
        sets_df["song_name"] = sets_df["song"]

    shows_df["_dt"] = pd.to_datetime(shows_df["show_date"]).dt.date
    sets_df["show_id"] = sets_df["show_id"].astype(str)

    # Exclude shows with <=5 unique songs
    unique_song_counts = (
        sets_df.groupby("show_id")["song_name"].nunique().rename("unique_song_count")
    )
    valid_show_ids = set(unique_song_counts[unique_song_counts > 5].index.astype(str))

    # Get the last N completed valid show dates (mirror notebook logic)
    completed_show_ids = sets_df["show_id"].dropna().astype(str).unique().tolist()
    completed_shows = shows_df[shows_df["show_id"].astype(str).isin(completed_show_ids)].copy()
    completed_shows = completed_shows.sort_values(["_dt", "show_id"])  # chronological
    completed_shows["show_id"] = completed_shows["show_id"].astype(str)
    valid_completed_shows = completed_shows[completed_shows["show_id"].isin(valid_show_ids)]
    last_n_shows = valid_completed_shows.tail(args.shows)
    # Keep both dates and show_ids to avoid ambiguity on same-date multi-shows
    ref_dates = last_n_shows["_dt"].tolist()
    ref_show_ids = last_n_shows["show_id"].astype(str).tolist()

    if not ref_dates:
        print(f"No completed show dates found to evaluate for {band}.")
        return

    window_start = min(ref_dates)
    window_end = max(ref_dates)
    print(f"Evaluating last {len(ref_dates)} completed shows for {band} from {window_start} to {window_end}")

    predictor = CKPlusPredictor(alpha=0.7, min_plays_threshold=3, retired_gap_threshold=200)
    per_k_metrics: Dict[int, List[Dict[str, float]]] = {10: [], 25: [], 50: []}

    showdate_by_id = {str(r["show_id"]): r["show_date"] for _, r in shows_df[["show_id", "show_date"]].iterrows()}
    sets_df["show_date_str"] = sets_df["show_id"].map(showdate_by_id)
    sets_df["_dt"] = pd.to_datetime(sets_df["show_date_str"], errors='coerce').dt.date

    for ref_date, show_id in zip(ref_dates, ref_show_ids):
        if pd.isna(ref_date):
            continue
        # Evaluate accuracy against the specific show_id to avoid cross-show contamination
        actual = (
            sets_df.loc[sets_df["show_id"] == str(show_id), "song_name"].dropna().unique().tolist()
        )
        # Skip shows with <=5 total songs in the setlist
        if len(actual) <= 5:
            continue
        if not actual:
            continue

        model_data = generate_model_data(shows_df, sets_df, ref_date)
        preds = predictor.predict(model_data=model_data, top_k=50)
        pred_songs = [p.song_name for p in preds]

        for k in per_k_metrics.keys():
            per_k_metrics[k].append(compute_per_show_metrics(pred_songs, actual, k))

    # Aggregate and build record
    record = {
        "band": band,
        "model_version": "ckplus_v1",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "num_shows": len(ref_dates),
        "evaluated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
    }
    for k in [10, 25, 50]:
        agg = aggregate_metrics(per_k_metrics[k], k)
        record[f"k{k}_hit_rate"] = agg.hit_rate
        record[f"k{k}_avg_matches"] = agg.avg_matches
        record[f"k{k}_precision"] = agg.precision
        record[f"k{k}_recall"] = agg.recall
        record[f"k{k}_f1"] = agg.f1

    table_name = "accuracy_ckplus"
    client.table(table_name).upsert(record, on_conflict="band,model_version,window_start,window_end").execute()
    print(f"Saved accuracy summary to {table_name} for {band}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save aggregate CK+ model accuracy for a specific band.")
    parser.add_argument("--band", type=str, required=True, help="The band to process (e.g., 'goose', 'phish').")
    parser.add_argument("--shows", type=int, default=50, help="Number of recent shows to average over.")
    args = parser.parse_args()
    main(args)