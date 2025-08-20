"""Compute and save CK+ accuracy for the last 50 completed Goose shows."""
from __future__ import annotations

from typing import Any, Dict, List
import os
import sys

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.models.ckplus.model import CKPlusPredictor  # noqa: E402
from src.jambandnerd.models.accuracy import compute_per_show_metrics, aggregate_metrics  # noqa: E402


def _fetch_table(table: str, select: str = "*") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table(table).select(select).execute()
    return res.data or []


def main() -> None:
    client = get_supabase_client()
    shows_df = pd.DataFrame(_fetch_table("goose_shows_raw"))
    sets_df = pd.DataFrame(_fetch_table("goose_setlists_raw"))

    if shows_df.empty or sets_df.empty:
        print("No data to compute accuracy")
        return

    shows_df["_dt"] = pd.to_datetime(shows_df["show_date"]).dt.date

    # Determine last 50 completed show dates (those that exist in setlists)
    sets_df["show_id"] = sets_df["show_id"].astype(str)
    completed_ids = sets_df["show_id"].dropna().astype(str).unique().tolist()
    completed = shows_df[shows_df["show_id"].astype(str).isin(completed_ids)].copy()
    completed = completed.sort_values(["_dt", "show_id"])
    last50 = completed.tail(50)
    ref_dates = last50["_dt"].tolist()

    predictor = CKPlusPredictor()
    per_k: Dict[int, List[Dict[str, float]]] = {10: [], 25: [], 50: []}

    # Precompute actual unique songs per show date
    showdate_by_id = {str(r["show_id"]): r["show_date"] for _, r in shows_df[["show_id", "show_date"]].iterrows()}
    sets_df["show_date_str"] = sets_df["show_id"].map(showdate_by_id)
    sets_df["_dt"] = pd.to_datetime(sets_df["show_date_str"]).dt.date

    for ref_date in ref_dates:
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
        for k in per_k.keys():
            per_k[k].append(compute_per_show_metrics(pred_songs, actual, k))

    # Aggregate
    agg10 = aggregate_metrics(per_k[10], 10)
    agg25 = aggregate_metrics(per_k[25], 25)
    agg50 = aggregate_metrics(per_k[50], 50)

    record = {
        "band": "goose",
        "model_version": "ckplus_v1",
        "window_start": str(ref_dates[0]) if ref_dates else None,
        "window_end": str(ref_dates[-1]) if ref_dates else None,
        "num_shows": len(ref_dates),
        "k10_hit_rate": agg10.hit_rate,
        "k10_avg_matches": agg10.avg_matches,
        "k10_precision": agg10.precision,
        "k10_recall": agg10.recall,
        "k10_f1": agg10.f1,
        "k25_hit_rate": agg25.hit_rate,
        "k25_avg_matches": agg25.avg_matches,
        "k25_precision": agg25.precision,
        "k25_recall": agg25.recall,
        "k25_f1": agg25.f1,
        "k50_hit_rate": agg50.hit_rate,
        "k50_avg_matches": agg50.avg_matches,
        "k50_precision": agg50.precision,
        "k50_recall": agg50.recall,
        "k50_f1": agg50.f1,
    }
    client.table("accuracy_ckplus").insert(record).execute()
    print("Saved CK+ accuracy summary.")


if __name__ == "__main__":
    main()



