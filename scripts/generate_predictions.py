"""
Unified script to generate predictions for any band and model combination.

This script replaces the individual `generate_<band>_<model>_predictions.py` files
by accepting `--band` and `--model` arguments.

Usage:
  # Generate Notebook predictions for Goose
  uv run python scripts/generate_predictions.py --band goose --model notebook

  # Generate CK+ predictions for Phish for a specific date
  uv run python scripts/generate_predictions.py --band phish --model ckplus --date 2024-08-01
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data, resolve_reference_date
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.transformations.gaps import generate_model_data


class NpEncoder(json.JSONEncoder):
    """Helper to convert numpy types to native Python types for JSON serialization."""

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


def generate_predictions(band: str, model: str, date_str: str | None, exclusion_window: int):
    """Generate and save predictions for a given band and model."""
    band = band.lower()
    model = model.lower()

    # 1. Fetch and prepare data
    log_prefix = f"[{band.upper()}/{model.upper()}]"
    print(f"{log_prefix} Fetching raw data...")
    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))
    upcoming_df: pd.DataFrame | None = None
    if date_str is None and band == "um":
        try:
            upcoming_df = pd.DataFrame(fetch_table("um_upcoming_shows"))
        except Exception as exc:  # pragma: no cover - Supabase connectivity
            print(f"[{band.upper()}/{model.upper()}] Warning: could not load upcoming shows ({exc}).")
            upcoming_df = None

    if shows_df.empty or setlists_df.empty:
        print(f"{log_prefix} Error: Could not fetch raw data. Aborting.")
        return

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df)
    reference_date = resolve_reference_date(date_str, shows_df, upcoming_df=upcoming_df)
    print(f"{log_prefix} Generating predictions for reference date: {reference_date.isoformat()}")

    model_data = generate_model_data(
        shows_df, setlists_df, reference_date, exclusion_window=exclusion_window
    )

    # 2. Select and run model
    predictions: List[Any] = []
    if model == "notebook":
        predictor = NotebookPredictor(band=band)
        preds, diagnostics = predictor.predict(model_data=model_data, top_k=50)
        predictions = preds
        print(f"{log_prefix} --- Model Diagnostics ---")
        print(json.dumps(diagnostics, indent=2, cls=NpEncoder))
        print(f"{log_prefix} Recently played songs (excluded): {model_data.recently_played_songs}")
        print(f"{log_prefix} -------------------------")
    elif model == "ckplus":
        predictor = CKPlusPredictor(band=band)
        predictions = predictor.predict(model_data=model_data, top_k=50)

    if not predictions:
        print(f"{log_prefix} No predictions were generated.")
        return

    # 3. Format and save results
    if model == "notebook":
        predictions_list = [
            {
                "rank": i + 1,
                "song_name": p.song_name,
                "plays_past_year": p.plays_past_year,
                "current_gap": p.current_gap,
                "last_played_date": p.last_played_date,
            }
            for i, p in enumerate(predictions)
        ]
        table_name = "predictions_notebook"
        model_version = "notebook_v1"
    elif model == "ckplus":
        predictions_list = [
            {
                "rank": i + 1,
                "song_name": p.song_name,
                "times_played": p.times_played,
                "current_gap": p.current_gap,
                "avg_gap": p.avg_gap,
                "gap_ratio": p.gap_ratio,
                "gap_z_score": p.gap_z_score,
                "ckplus_score": p.ckplus_score,
                "LTP": p.LTP,
            }
            for i, p in enumerate(predictions)
        ]
        table_name = "predictions_ckplus"
        model_version = "ckplus_v1"
    else:
        raise ValueError("Invalid model type")

    output_row = {
        "band": band,
        "reference_date": reference_date.isoformat(),
        "model_version": model_version,
        "top_k": len(predictions_list),
        "predictions": json.dumps(predictions_list, cls=NpEncoder),
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    }

    output_df = pd.DataFrame([output_row])

    print(f"{log_prefix} Generated {len(predictions_list)} predictions. Saving to {table_name}...")
    upsert_dataframe(
        table_name=table_name,
        df=output_df,
        conflict_columns=["band", "reference_date", "model_version"],
    )
    print(f"{log_prefix} Successfully saved predictions.")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate predictions for a specific band and model."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        choices=["goose", "eggy", "phish", "wsp", "billy", "um"],
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=["notebook", "ckplus"],
        help="The model to use for predictions.",
    )
    parser.add_argument(
        "--date",
        help="Reference date in YYYY-MM-DD format. Defaults to next upcoming show.",
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=3,
        help="Number of recent shows to exclude songs from (default: 3).",
    )
    args = parser.parse_args()

    generate_predictions(
        band=args.band,
        model=args.model,
        date_str=args.date,
        exclusion_window=args.exclusion_window,
    )


if __name__ == "__main__":
    main()
