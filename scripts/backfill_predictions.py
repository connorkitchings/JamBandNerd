"""
Backfill predictions that may be stale due to new setlist data.

This script identifies predictions where new setlist data has become available
for shows that occurred before the prediction's reference_date, but weren't
available at the time the original prediction was made.

Usage:
    # Backfill all bands
    uv run python scripts/backfill_predictions.py --band all

    # Backfill specific band and model
    uv run python scripts/backfill_predictions.py --band wsp --model ckplus
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.common import fetch_table, prepare_band_data
from src.jambandnerd.config import BAND_EXCLUSION_WINDOWS
from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.db.operations import (
    replace_prediction_projection,
    upsert_dataframe,
)
from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    list_backfill_models,
    serialize_model_predictions,
)
from src.jambandnerd.transformations.gaps import generate_model_data

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def check_stale_predictions(
    band: str,
    model: str,
    prediction_table: str,
) -> list[dict]:
    """Find predictions that may need refreshing due to new setlist data.

    Heuristic: If shows occurred between consecutive predictions and now have setlists,
    the later prediction is stale because it was made without that information.
    """

    logger.info(f"[{band}/{model}] Checking for stale predictions...")

    predictions = fetch_table(prediction_table)
    pred_df = pd.DataFrame(predictions)
    if pred_df.empty:
        logger.info(f"[{band}/{model}] No predictions found")
        return []

    pred_df = pred_df[pred_df["band"] == band].copy()
    pred_df = pred_df.sort_values("reference_date").reset_index(drop=True)

    shows_raw = fetch_table(f"{band}_shows_raw")
    shows_df = pd.DataFrame(shows_raw)

    setlists_raw = fetch_table(f"{band}_setlists_raw")
    setlists_df = pd.DataFrame(setlists_raw)

    if shows_df.empty or setlists_df.empty:
        logger.info(f"[{band}/{model}] No shows or setlists found")
        return []

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df, band=band)

    shows_df["show_date_str"] = shows_df["show_date"].astype(str)
    setlist_show_ids = set(setlists_df["show_id"].unique())

    stale_predictions = []

    for i, pred in pred_df.iterrows():
        reference_date_str = pred.get("reference_date")
        predicted_at_str = pred.get("predicted_at")

        if not reference_date_str:
            continue

        if i == 0:
            previous_ref_date = None
        else:
            prev_ref = pred_df.iloc[i - 1].get("reference_date")
            try:
                previous_ref_date = (
                    datetime.strptime(prev_ref, "%Y-%m-%d").date() if prev_ref else None
                )
            except (ValueError, TypeError):
                previous_ref_date = None

        if previous_ref_date is None:
            continue

        shows_on_prev_day = shows_df[
            shows_df["show_date_str"] == str(previous_ref_date)
        ]

        if shows_on_prev_day.empty:
            continue

        shows_with_setlist = shows_on_prev_day[
            shows_on_prev_day["show_id"].isin(setlist_show_ids)
        ]

        if not shows_with_setlist.empty:
            stale_predictions.append(
                {
                    "reference_date": reference_date_str,
                    "predicted_at": predicted_at_str,
                    "new_shows_with_setlists": len(shows_with_setlist),
                    "model_version": pred.get("model_version"),
                }
            )
            logger.info(
                f"[{band}/{model}] Stale: {reference_date_str} - setlist for {previous_ref_date} now available"
            )

    return stale_predictions


def regenerate_prediction(
    band: str,
    model: str,
    reference_date_str: str,
    exclusion_window: int,
) -> bool:
    """Regenerate a prediction for a specific reference date."""
    try:
        reference_date = datetime.strptime(reference_date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Invalid reference date: {reference_date_str}")
        return False

    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))

    if shows_df.empty or setlists_df.empty:
        logger.error(f"No data available for {band}")
        return False

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df, band=band)

    try:
        model_data = generate_model_data(
            shows_df,
            setlists_df,
            reference_date,
            exclusion_window=exclusion_window,
            band=band,
        )
    except Exception as e:
        logger.error(f"Failed to generate model data: {e}")
        return False

    model_definition = get_model_definition(model)
    predictor = build_predictor(model, band=band)
    prediction_output = predictor.predict(
        model_data=model_data,
        top_k=model_definition.default_top_k,
    )
    predictions = prediction_output[0] if isinstance(prediction_output, tuple) else prediction_output

    if not predictions:
        logger.error(f"No predictions generated for {reference_date_str}")
        return False

    predictions_list = serialize_model_predictions(model, predictions)
    table_name = model_definition.prediction_table
    model_version = model_definition.version

    predicted_at = datetime.now(timezone.utc).isoformat()
    output_row = {
        "band": band,
        "reference_date": reference_date_str,
        "model_version": model_version,
        "top_k": len(predictions_list),
        "predictions": predictions_list,
        "predicted_at": predicted_at,
    }

    output_df = pd.DataFrame([output_row])

    try:
        upsert_dataframe(
            table_name=table_name,
            df=output_df,
            conflict_columns=["band", "reference_date", "model_version"],
        )
        replace_prediction_projection(
            band=band,
            model_slug=model,
            model_version=model_version,
            reference_date=reference_date_str,
            predicted_at=predicted_at,
            predictions=output_row["predictions"],
        )
        logger.info(f"[{band}/{model}] Regenerated prediction for {reference_date_str}")
        return True
    except Exception as e:
        logger.error(f"Failed to save prediction: {e}")
        return False


def backfill_band(
    band: str,
    model: str,
    dry_run: bool = False,
) -> dict:
    """Backfill stale predictions for a single band and model."""

    model_definition = get_model_definition(model)
    prediction_table = model_definition.prediction_table
    exclusion_window = BAND_EXCLUSION_WINDOWS.get(band, 3)

    stale = check_stale_predictions(band, model, prediction_table)

    if not stale:
        return {"band": band, "model": model, "stale_count": 0, "regenerated": 0}

    logger.info(f"[{band}/{model}] Found {len(stale)} stale predictions")

    if dry_run:
        return {
            "band": band,
            "model": model,
            "stale_count": len(stale),
            "regenerated": 0,
        }

    regenerated = 0
    for stale_pred in stale:
        success = regenerate_prediction(
            band,
            model,
            stale_pred["reference_date"],
            exclusion_window,
        )
        if success:
            regenerated += 1

    return {
        "band": band,
        "model": model,
        "stale_count": len(stale),
        "regenerated": regenerated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill predictions that may be stale due to new setlist data."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        help="Band to process (or 'all' for all bands)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ckplus",
        choices=[definition.slug for definition in list_backfill_models()],
        help="Model to process (default: ckplus)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for stale predictions without regenerating",
    )
    args = parser.parse_args()

    bands = get_active_bands() if args.band == "all" else [args.band]

    if args.band != "all" and args.band not in get_active_bands():
        logger.error(f"Unknown band: {args.band}")
        sys.exit(1)

    results = []
    for band in bands:
        result = backfill_band(band, args.model, dry_run=args.dry_run)
        results.append(result)
        if args.dry_run:
            logger.info(
                f"[DRY RUN] {band}/{args.model}: {result['stale_count']} stale predictions found"
            )
        else:
            logger.info(
                f"{band}/{args.model}: {result['stale_count']} stale, {result['regenerated']} regenerated"
            )

    total_stale = sum(r["stale_count"] for r in results)
    total_regenerated = sum(r["regenerated"] for r in results)

    logger.info(f"Total: {total_stale} stale, {total_regenerated} regenerated")


if __name__ == "__main__":
    main()
