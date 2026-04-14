"""
Unified script to generate predictions for any band and model combination.

This script replaces the individual `generate_<band>_<model>_predictions.py` files
by accepting `--band` and `--model` arguments.

Usage:
  # Generate Notebook predictions for Goose
  uv run python scripts/generate_predictions.py --band goose --model notebook

  # Generate Deal predictions for Phish for a specific date
  uv run python scripts/generate_predictions.py --band phish --model deal --date 2024-08-01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any, List

import numpy as np
import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data, resolve_reference_date
from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.db.operations import (
    replace_prediction_projection,
    upsert_dataframe,
)
from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    list_model_slugs,
    serialize_model_predictions,
)
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


def generate_predictions(
    band: str,
    model: str,
    date_str: str | None,
    exclusion_window: int | None,
    retrain: bool = False,
    require_output: bool = False,
) -> bool:
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
            print(
                f"[{band.upper()}/{model.upper()}] Warning: could not load upcoming shows ({exc})."
            )
            upcoming_df = None

    if shows_df.empty or setlists_df.empty:
        message = f"{log_prefix} Error: Could not fetch raw data. Aborting."
        print(message)
        if require_output:
            raise RuntimeError(message)
        return False

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df, band=band)
    reference_date = resolve_reference_date(date_str, shows_df, upcoming_df=upcoming_df)
    print(
        f"{log_prefix} Generating predictions for reference date: {reference_date.isoformat()}"
    )

    model_data = generate_model_data(
        shows_df,
        setlists_df,
        reference_date,
        exclusion_window=exclusion_window,
        band=band,
    )

    # 2. Select and run model
    model_definition = get_model_definition(model)
    predictor_kwargs: dict[str, Any] = {}
    if model_definition.supports_training and not retrain:
        predictor_kwargs["persist_artifacts"] = False
        print(
            f"{log_prefix} Training-capable model will run with in-memory fresh training; cached artifacts are disabled for this prediction run."
        )
    predictor = build_predictor(model, band=band, **predictor_kwargs)
    predictions: List[Any] = []

    if model_definition.supports_training:
        if retrain:
            print(f"{log_prefix} Force retrain enabled, clearing model cache...")
            get_model_path = getattr(predictor, "_get_model_path", None)
            if callable(get_model_path):
                model_path = get_model_path(band)
                if model_path.exists():
                    model_path.unlink()
        else:
            print(
                f"{log_prefix} Training {model_definition.display_name} from the current reference-date snapshot."
            )
        predictor.train(model_data)

    prediction_output = predictor.predict(
        model_data=model_data,
        top_k=model_definition.default_top_k,
    )
    if isinstance(prediction_output, tuple):
        predictions, diagnostics = prediction_output
        print(f"{log_prefix} --- Model Diagnostics ---")
        print(json.dumps(diagnostics, indent=2, cls=NpEncoder))
        print(
            f"{log_prefix} Recently played songs (excluded): {model_data.recently_played_songs}"
        )
        print(f"{log_prefix} -------------------------")
    else:
        predictions = prediction_output

    if not predictions:
        message = f"{log_prefix} No predictions were generated."
        print(message)
        if require_output:
            raise RuntimeError(message)
        return False

    # 3. Format and save results
    predictions_list = serialize_model_predictions(model, predictions)
    table_name = model_definition.prediction_table
    model_version = model_definition.version

    predicted_at = datetime.now(timezone.utc).isoformat()
    output_row = {
        "band": band,
        "model_slug": model,
        "reference_date": reference_date.isoformat(),
        "model_version": model_version,
        "top_k": len(predictions_list),
        "predictions": json.loads(json.dumps(predictions_list, cls=NpEncoder)),
        "predicted_at": predicted_at,
    }

    output_df = pd.DataFrame([output_row])

    print(
        f"{log_prefix} Generated {len(predictions_list)} predictions. Saving to {table_name}..."
    )
    # Two-step write sequence:
    # 1. Upsert the canonical JSON row (predictions_notebook / predictions_ckplus).
    #    This is the source-of-truth prediction record keyed on
    #    (band, reference_date, model_version).
    # 2. Replace the derived prediction_songs projection for the same key.
    #    prediction_songs is a flat per-song table consumed by the website.
    #    The replace call also triggers stale-row cleanup for older
    #    reference_date entries (>30 days, never the most recent).
    upsert_dataframe(
        table_name=table_name,
        df=output_df,
        conflict_columns=["band", "model_slug", "reference_date", "model_version"],
    )
    replace_prediction_projection(
        band=band,
        model_slug=model,
        model_version=model_version,
        reference_date=reference_date.isoformat(),
        predicted_at=predicted_at,
        predictions=output_row["predictions"],
    )
    print(f"{log_prefix} Successfully saved predictions.")
    return True


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate predictions for a specific band and model."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        choices=get_active_bands(),
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=list_model_slugs(),
        help="The model to use for predictions.",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Force retrain for training-capable models.",
    )
    parser.add_argument(
        "--date",
        help="Reference date in YYYY-MM-DD format. Defaults to next upcoming show.",
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=None,
        help="Number of recent shows to exclude songs from. Defaults to band-specific config.",
    )
    parser.add_argument(
        "--require-output",
        action="store_true",
        help="Exit non-zero if the run would otherwise finish without writing predictions.",
    )
    args = parser.parse_args()

    model_definition = get_model_definition(args.model)
    if args.retrain and not model_definition.supports_training:
        parser.error(
            f"--retrain is only supported for training-capable models; got {args.model}"
        )

    generate_predictions(
        band=args.band,
        model=args.model,
        date_str=args.date,
        exclusion_window=args.exclusion_window,
        retrain=args.retrain,
        require_output=args.require_output,
    )


if __name__ == "__main__":
    main()
