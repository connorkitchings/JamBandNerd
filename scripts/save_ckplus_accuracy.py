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
from scripts.common import fetch_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Save aggregate CK+ model accuracy for a specific band.")
    parser.add_argument("--band", type=str, required=True, help="The band to process (e.g., 'goose', 'phish').")
    parser.add_argument("--shows", type=int, default=50, help="Number of recent shows to average over.")
    args = parser.parse_args()

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

    # Get the last N completed show dates
    completed_show_ids = sets_df["show_id"].unique()
    completed_shows = shows_df[shows_df["show_id"].isin(completed_show_ids)]
    last_n_dates = sorted(completed_shows["_dt"].unique(), reverse=True)[:args.shows]

    if not last_n_dates:
        print(f"No completed show dates found to evaluate for {band}.")
        return

    window_start = min(last_n_dates)
    window_end = max(last_n_dates)
    print(f"Evaluating last {len(last_n_dates)} completed shows for {band} from {window_start} to {window_end}")

    predictor = CKPlusPredictor(alpha=0.7, min_plays_threshold=3, retired_gap_threshold=200)
    per_k_metrics: Dict[int, List[Dict[str, float]]] = {10: [], 25: [], 50: []}

    showdate_by_id = {str(r["show_id"]): r["show_date"] for _, r in shows_df[["show_id", "show_date"]].iterrows()}
    sets_df["show_date_str"] = sets_df["show_id"].map(showdate_by_id)
    sets_df["_dt"] = pd.to_datetime(sets_df["show_date_str"], errors='coerce').dt.date

    for ref_date in last_n_dates:
        if pd.isna(ref_date):
            continue
        actual = sets_df.loc[sets_df["_dt"] == ref_date, "song_name"].dropna().unique().tolist()
        if not actual:
            continue

        preds = predictor.predict(
            shows_df=shows_df,
            setlists_df=sets_df,
            top_k=50,
            reference_show_date=ref_date,
        )
        pred_songs = [p.song_name for p in preds]

        for k in per_k_metrics.keys():
            per_k_metrics[k].append(compute_per_show_metrics(pred_songs, actual, k))

    # Aggregate and build record
    record = {
        "band": band,
        "model_version": "ckplus_v1",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "num_shows": len(last_n_dates),
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
    main()