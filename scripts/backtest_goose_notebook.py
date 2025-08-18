"""Backtest Goose notebook model over historical shows.

For each show date in a specified window, use that date as the reference_show_date, generate
top-50 predictions, compare against the show's actual setlist (unique songs), and compute
top-k metrics for k in {10, 25, 50}. Prints aggregated metrics at the end.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.models.notebook.model import NotebookPredictor  # noqa: E402
from src.jambandnerd.models.accuracy import compute_per_show_metrics, aggregate_metrics  # noqa: E402


def _fetch_table(table: str, select: str = "*") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table(table).select(select).execute()
    return res.data or []


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest Goose notebook model")
    parser.add_argument("--start", help="Start show date YYYY-MM-DD (inclusive)", required=False)
    parser.add_argument("--end", help="End show date YYYY-MM-DD (inclusive)", required=False)
    args = parser.parse_args()

    shows_df = pd.DataFrame(_fetch_table("goose_shows_raw"))
    sets_df = pd.DataFrame(_fetch_table("goose_setlists_raw"))

    if shows_df.empty or sets_df.empty:
        print("No data to backtest")
        return

    shows_df["_dt"] = pd.to_datetime(shows_df["show_date"]).dt.date

    # Build list of reference show dates in window
    if args.start:
        start_d = pd.to_datetime(args.start).date()
    else:
        start_d = (date.today() - timedelta(days=365))
    if args.end:
        end_d = pd.to_datetime(args.end).date()
    else:
        end_d = date.today()

    # We only test on show dates that exist in shows
    ref_dates = sorted(d for d in set(shows_df["_dt"]) if start_d <= d <= end_d)
    print(f"Backtesting on {len(ref_dates)} show dates from {start_d} to {end_d}")

    predictor = NotebookPredictor()
    per_k_metrics: Dict[int, List[Dict[str, float]]] = {10: [], 25: [], 50: []}

    # Precompute actual setlist songs per show date (unique)
    sets_df["show_id"] = sets_df["show_id"].astype(str)
    # Map date -> set of songs
    showdate_by_id = {str(r["show_id"]): r["show_date"] for _, r in shows_df[["show_id", "show_date"]].iterrows()}
    sets_df["show_date_str"] = sets_df["show_id"].map(showdate_by_id)
    sets_df["_dt"] = pd.to_datetime(sets_df["show_date_str"]).dt.date

    for ref_date in ref_dates:
        # Actual unique songs for the show on ref_date
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

    # Aggregate and print
    for k in [10, 25, 50]:
        agg = aggregate_metrics(per_k_metrics[k], k)
        print(f"K={k}: hit_rate={agg.hit_rate:.3f} avg_matches={agg.avg_matches:.3f} precision={agg.precision:.3f} recall={agg.recall:.3f} f1={agg.f1:.3f}")


if __name__ == "__main__":
    main()


