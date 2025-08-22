"""Generate Goose predictions using the CK+ model."""
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
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.db.operations import upsert_dataframe
from scripts.common import resolve_reference_date

def fetch_raw_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch all raw shows and setlists data from Supabase."""
    client = get_supabase_client()
    shows_resp = client.table("goose_shows_raw").select("*").execute()
    setlists_resp = client.table("goose_setlists_raw").select("*").execute()
    return pd.DataFrame(shows_resp.data), pd.DataFrame(setlists_resp.data)

def main(date_str: str | None) -> None:
    """Generate and save CK+ predictions for a given date."""
    shows_df, setlists_df = fetch_raw_data()
    if shows_df.empty or setlists_df.empty:
        print("Error: Could not fetch raw data from Supabase. Aborting.")
        return

    reference_date = resolve_reference_date(date_str, shows_df)

    print(f"Generating CK+ predictions for reference date: {reference_date.isoformat()}")

    predictor = CKPlusPredictor()
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
            "times_played": p.times_played,
            "current_gap": p.current_gap,
            "avg_gap": p.avg_gap,
            "gap_ratio": p.gap_ratio,
            "gap_z_score": p.gap_z_score,
            "ckplus_score": p.ckplus_score,
            "LTP": p.LTP,
        })

    output_row = {
        "band": "goose",
        "reference_date": reference_date.isoformat(),
        "model_version": "ckplus_v1",
        "top_k": len(predictions_list),
        "predictions": json.dumps(predictions_list),
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    }

    output_df = pd.DataFrame([output_row])
    
    print(f"Generated {len(predictions_list)} predictions. Saving to Supabase...")
    upsert_dataframe(
        table_name="predictions_ckplus",
        df=output_df,
        conflict_columns=["band", "reference_date", "model_version"],
    )
    print("Successfully saved predictions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Goose CK+ predictions.")
    parser.add_argument("--date", help="Reference date in YYYY-MM-DD format. Defaults to next upcoming show.")
    args = parser.parse_args()
    main(args.date)
