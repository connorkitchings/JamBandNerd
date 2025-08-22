"""Generate baseline Goose next-song predictions using the notebook predictor."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timezone
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
    """Fetch all raw shows and setlists data from Supabase."""
    client = get_supabase_client()
    shows_resp = client.table("goose_shows_raw").select("*").execute()
    setlists_resp = client.table("goose_setlists_raw").select("*").execute()
    return pd.DataFrame(shows_resp.data), pd.DataFrame(setlists_resp.data)


def main(date_str: str | None) -> None:
    """Generate and save notebook predictions for a given date."""
    shows_df, setlists_df = fetch_raw_data()
    if shows_df.empty or setlists_df.empty:
        print("Error: Could not fetch raw data from Supabase. Aborting.")
        return

    reference_date = resolve_reference_date(date_str, shows_df)
    
    print(f"Generating Notebook predictions for reference date: {reference_date.isoformat()}")

    predictor = NotebookPredictor()
    predictions = predictor.predict(
        shows_df=shows_df,
        setlists_df=setlists_df,
        top_k=50,
        reference_show_date=reference_date,
    )

    if not predictions:
        print("No predictions were generated. This could be due to lack of data for the reference date.")
        return

    # Format for Supabase
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
        "band": "goose",
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
    print("Successfully saved predictions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Goose Notebook predictions.")
    parser.add_argument("--date", help="Reference date in YYYY-MM-DD format. Defaults to today.")
    args = parser.parse_args()
    main(args.date)