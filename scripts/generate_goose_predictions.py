"""Generate baseline Goose next-song predictions using the notebook predictor."""
from __future__ import annotations

from typing import Any, Dict, List
import argparse
import os
import sys

import pandas as pd

# Align sys.path with other scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.models.notebook.model import NotebookPredictor  # noqa: E402
from src.jambandnerd.transformations.gaps import aggregate_past_year_for_notebook  # noqa: E402


def _fetch_table(table: str, select: str = "*") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table(table).select(select).execute()
    return res.data or []


def _resolve_reference_show_date() -> str:
    from datetime import date
    client = get_supabase_client()
    shows_rows = client.table("goose_shows_raw").select("show_date,show_id").execute().data
    df = pd.DataFrame(shows_rows)
    df["_dt"] = pd.to_datetime(df["show_date"]).dt.date
    today = date.today()
    upcoming = df[df["_dt"] >= today].sort_values(["_dt", "show_id"])  # pick earliest show date >= today
    if not upcoming.empty:
        d = upcoming.iloc[0]["_dt"]
    else:
        # No future shows; fall back to latest known show date
        d = df["_dt"].max()
    return d.isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Goose notebook predictions")
    parser.add_argument("--date", dest="date", help="Reference show date YYYY-MM-DD", required=False)
    args = parser.parse_args()
    print("Loading Goose raw tables from Supabase...")
    shows_rows = _fetch_table("goose_shows_raw")
    setlists_rows = _fetch_table("goose_setlists_raw")
    shows_df = pd.DataFrame(shows_rows)
    setlists_df = pd.DataFrame(setlists_rows)
    print(f"Loaded shows={len(shows_df)}, setlists={len(setlists_df)}")

    reference_date_str = args.date or _resolve_reference_show_date()
    predictor = NotebookPredictor()
    predictions = predictor.predict(
        shows_df=shows_df,
        setlists_df=setlists_df,
        top_k=50,
        reference_show_date=pd.to_datetime(reference_date_str).date(),
    )
    print("Top predictions:")
    for rank, p in enumerate(predictions, start=1):
        # Format LTP as mm/dd/yyyy
        ltp = None
        if p.last_played_date:
            try:
                parts = p.last_played_date.split("-")
                ltp = f"{parts[1]}/{parts[2]}/{parts[0]}"
            except Exception:
                ltp = p.last_played_date
        print(f"{rank:2d}. {p.song_name}  (plays={p.plays_past_year}, current_gap={p.current_gap}, LTP={ltp})")

    # Persist to Supabase notebook predictions table
    agg = aggregate_past_year_for_notebook(
        shows_df=shows_df, setlists_df=setlists_df, reference_show_date=pd.to_datetime(reference_date_str).date()
    )
    payload = [
        {
            "rank": i + 1,
            "song_name": p.song_name,
            "plays_past_year": p.plays_past_year,
            "current_gap": p.current_gap,
            "LTP": (f"{p.last_played_date.split('-')[1]}/{p.last_played_date.split('-')[2]}/{p.last_played_date.split('-')[0]}" if p.last_played_date else None),
        }
        for i, p in enumerate(predictions)
    ]
    client = get_supabase_client()
    record = {
        "band": "goose",
        "reference_date": agg.latest_show_date.isoformat(),
        "predictions": payload,
        "top_k": len(payload),
        "model_version": "notebook_v1",
        "collected_at": None,  # optionally populated by a separate query if desired
        "predicted_at": pd.Timestamp.utcnow().isoformat(),
    }
    # Upsert by unique (band, reference_date, model_version)
    client.table("goose_notebook_predictions").upsert(record, on_conflict="band,reference_date,model_version").execute()
    print("Saved predictions to goose_notebook_predictions.")


if __name__ == "__main__":
    main()


