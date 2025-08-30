from __future__ import annotations

"""Generate baseline Widespread Panic next-song predictions using the notebook predictor."""

import argparse
import os
import sys
from datetime import datetime, timezone, date
import json

import pandas as pd
import numpy as np

# Align sys.path with other scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.transformations.gaps import generate_model_data
from scripts.common import resolve_reference_date, fetch_table


def main(date_str: str | None) -> None:
    """Generate and save notebook predictions for a given date for Widespread Panic."""
    shows_df = pd.DataFrame(fetch_table("wsp_shows_raw"))
    setlists_df = pd.DataFrame(fetch_table("wsp_setlists_raw"))

    if shows_df.empty or setlists_df.empty:
        print("Error: Could not fetch raw data from Supabase. Aborting.")
        return

    reference_date = resolve_reference_date(date_str, shows_df)

    print(f"Generating Notebook predictions for Widespread Panic, reference date: {reference_date.isoformat()}")

    model_data = generate_model_data(shows_df, setlists_df, reference_date)

    predictor = NotebookPredictor()
    predictions, diagnostics = predictor.predict(model_data=model_data, top_k=50)

    # A simple helper to convert numpy types to native Python types for JSON serialization
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super(NpEncoder, self).default(obj)

    print("--- Model Diagnostics ---")
    print(json.dumps(diagnostics, indent=2, cls=NpEncoder))
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

    # Print Top 25 to stdout
    if predictions_list:
        print("Top 25 Notebook predictions (Widespread Panic):")
        for item in predictions_list[:25]:
            print(f"{item['rank']:>2}. {item['song_name']} (plays_past_year={item['plays_past_year']}, gap={item['current_gap']})")

    output_row = {
        "band": "wsp",
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
    print("Successfully saved Widespread Panic predictions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Widespread Panic Notebook predictions.")
    parser.add_argument("--date", help="Reference date in YYYY-MM-DD format. Defaults to next upcoming show.")
    args = parser.parse_args()
    main(args.date)