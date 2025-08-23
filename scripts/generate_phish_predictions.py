"""Generate baseline Phish next-song predictions using the notebook predictor."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
import json

import pandas as pd

# Align sys.path with other scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.db.operations import upsert_dataframe
from scripts.common import resolve_reference_date


def fetch_raw_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch all raw shows and setlists data for Phish from Supabase."""
    client = get_supabase_client()
    shows_resp = client.table("phish_shows_raw").select("*").execute()
    setlists_resp = client.table("phish_setlists_raw").select("*").execute()
    shows_df = pd.DataFrame(shows_resp.data)
    sets_df = pd.DataFrame(setlists_resp.data)
    if not shows_df.empty and "show_id" not in shows_df.columns and "api_show_id" in shows_df.columns:
        shows_df["show_id"] = shows_df["api_show_id"]
    if not sets_df.empty and "show_id" not in sets_df.columns and "api_show_id" in sets_df.columns:
        sets_df["show_id"] = sets_df["api_show_id"]
    return shows_df, sets_df


def main(date_str: str | None) -> None:
    """Generate and save notebook predictions for a given date for Phish."""
    shows_df, setlists_df = fetch_raw_data()
    if shows_df.empty or setlists_df.empty:
        print("Error: Could not fetch raw data from Supabase. Aborting.")
        return

    reference_date = resolve_reference_date(date_str, shows_df)

    print(f"Generating Notebook predictions for Phish, reference date: {reference_date.isoformat()}")

    predictor = NotebookPredictor()
    predictions, diagnostics = predictor.predict(
        shows_df=shows_df,
        setlists_df=setlists_df,
        top_k=50,
        reference_show_date=reference_date,
    )

    print("--- Model Diagnostics ---")
    print(f"Window Start: {diagnostics.get('window_start')}")
    print(f"Window End:   {diagnostics.get('window_end')}")
    print(f"Total song plays in window: {diagnostics.get('plays_in_window')}")
    print(f"Unique songs in window:     {diagnostics.get('unique_songs_in_window')}")
    print(f"Excluded recent songs count:  {len(diagnostics.get('excluded_recent_songs', []))}")
    print("-------------------------")

    if not predictions:
        print("No predictions were generated. This could be due to lack of data for the reference date.")
        return

    # Format for Supabase unified table
    predictions_list = []
    for i, p in enumerate(predictions):
        predictions_list.append({
            "rank": i + 1,
            "song_name": p.song_name,
            "plays_past_year": p.plays_past_year,
            "current_gap": p.current_gap,
            "last_played_date": p.last_played_date,
        })

    output_row = {
        "band": "phish",
        "reference_date": reference_date.isoformat(),
        "model_version": "notebook_v1",
        "top_k": len(predictions_list),
        "predictions": json.dumps(predictions_list),
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    }

    output_df = pd.DataFrame([output_row])

    print(f"Generated {len(predictions_list)} predictions. Saving to Supabase...")
    upsert_dataframe(
        table_name="predictions_notebook",
        df=output_df,
        conflict_columns=["band", "reference_date", "model_version"],
    )
    print("Successfully saved Phish predictions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Phish Notebook predictions.")
    parser.add_argument("--date", help="Reference date in YYYY-MM-DD format. Defaults to next upcoming show.")
    args = parser.parse_args()
    main(args.date)


