"""
Band-agnostic prediction export logic for saving predictions to Supabase.
"""
import numpy as np
import pandas as pd

from jambandnerd.db.supabase_client import create_supabase_client
from jambandnerd.logging_utils import get_logger

logger = get_logger(__name__)


def save_predictions_to_supabase(
    predictions_df: pd.DataFrame, table_name: str
) -> bool:
    """
    Save predictions to a model-specific Supabase table with band-agnostic logic.

    This function uses 'upsert' with a composite unique key on
    (prediction_date, band, song_name) to prevent duplicate entries for daily runs.

    Args:
        predictions_df: DataFrame with the song predictions.
        table_name: Name of the Supabase table (e.g., 'predictions_ckplus').

    Returns:
        True if successful, False otherwise.
    """
    if predictions_df is None or predictions_df.empty:
        logger.warning("No predictions to save.")
        return False

    logger.info(
        "Saving %d predictions to Supabase table '%s'...",
        len(predictions_df),
        table_name,
    )
    supabase = create_supabase_client()

    # Define columns for each model table to ensure schema alignment
    schema_columns = {
        "predictions_ckplus": [
            "prediction_date", "band", "song_id", "song_name", "last_played_date",
            "times_played_total", "current_gap", "avg_gap", "gap_ratio",
            "gap_z_score", "ckplus_score"
        ],
        "predictions_notebook": [
            "prediction_date", "band", "song_name", "last_played_date",
            "times_played_last_year", "current_gap", "avg_gap", "median_gap"
        ],
        "phish_predictions_ckplus": [
            "prediction_date", "band", "song_name", "last_played_date",
            "times_played_total", "current_gap", "avg_gap", "gap_ratio",
            "gap_z_score", "ckplus_score"
        ],
        "phish_predictions_notebook": [
            "prediction_date", "band", "song_name", "last_played_date",
            "times_played_last_year", "current_gap", "avg_gap", "median_gap"
        ],
        "goose_predictions_ckplus": [
            "prediction_date", "band", "song_name", "last_played_date",
            "times_played_total", "current_gap", "avg_gap", "gap_ratio",
            "gap_z_score", "ckplus_score"
        ],
        "goose_predictions_notebook": [
            "prediction_date", "band", "song_name", "last_played_date",
            "times_played_last_year", "current_gap", "avg_gap", "median_gap"
        ],
    }

    if table_name not in schema_columns:
        logger.error("Unknown table name '%s'. Cannot determine schema.", table_name)
        return False

    try:
        df_clean = predictions_df.copy()

        # Standardize date columns: 'ltp_date' -> 'last_played_date'
        if "ltp_date" in df_clean.columns:
            df_clean.rename(columns={"ltp_date": "last_played_date"}, inplace=True)
        if "last_time_played_date" in df_clean.columns:
            df_clean.rename(columns={"last_time_played_date": "last_played_date"}, inplace=True)

        # Select and reorder columns to match the target table schema exactly
        target_columns = schema_columns[table_name]
        # Filter df_clean to only include columns that are expected in the target table
        existing_columns = [col for col in target_columns if col in df_clean.columns]
        df_clean = df_clean[existing_columns]

        # Clean data before converting to JSON to prevent serialization errors
        # Replace infinity with NaN, then NaN with None (which becomes null in JSON)
        # Clean data before converting to JSON to prevent serialization errors
        # Replace infinity with NaN, then NaN with None (which becomes null in JSON)
        df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
        records = df_clean.where(pd.notnull(df_clean), None).to_dict(orient="records")

        if not records:
            logger.warning("No valid records to upsert after cleaning. Aborting save.")
            return False

        logger.info("Upserting %d records to '%s'.", len(records), table_name)

        # All tables use song_name for the unique constraint
        on_conflict_columns = "prediction_date,band,song_name"

        # Upsert the predictions using the appropriate composite unique key
        response = (
            supabase.table(table_name)
            .upsert(records, on_conflict=on_conflict_columns)
            .execute()
        )

        logger.info(
            "Successfully saved %d predictions to '%s'",
            len(response.data),
            table_name,
        )
        return True

    except Exception as e:
        logger.error("Failed to save predictions to Supabase table '%s': %s", table_name, e)
        # For debugging, re-raise the exception
        raise
