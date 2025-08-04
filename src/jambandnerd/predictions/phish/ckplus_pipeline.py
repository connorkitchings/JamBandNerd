"""
Phish CK+ prediction pipeline.

This module orchestrates the CK+ model prediction process for Phish:
1. Load and transform data
2. Run CK+ model
3. Export predictions to Supabase
"""

import logging

from jambandnerd.models.ckplus_model import run_ckplus_model
from jambandnerd.models.prediction_exporter import save_predictions_to_supabase

from .data_transformer import get_band_config, prepare_data_for_ckplus_model

logger = logging.getLogger(__name__)


def run_phish_ckplus_predictions() -> bool:
    """
    Run the complete Phish CK+ prediction pipeline.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        logger.info("Starting Phish CK+ prediction pipeline...")

        # Step 1: Load and transform data
        logger.info("Loading and transforming Phish data...")
        (
            song_data,
            show_data,
            venue_data,
            setlist_data,
            transition_data,
        ) = prepare_data_for_ckplus_model()

        # Step 2: Get band configuration
        config = get_band_config()

        # Step 3: Run CK+ model
        logger.info("Running CK+ model...")
        predictions_df = run_ckplus_model(
            song_data=song_data,
            show_data=show_data,
            venue_data=venue_data,
            setlist_data=setlist_data,
            transition_data=transition_data,
            gap_threshold=config["gap_threshold_ckplus"],
            top_n=config["top_predictions"],
        )

        if predictions_df is None or predictions_df.empty:
            logger.error("CK+ model returned no predictions")
            return False

        # Step 4: Export predictions to Supabase
        logger.info("Exporting %d predictions to Supabase...", len(predictions_df))
        success = save_predictions_to_supabase(
            predictions_df, config["supabase_table_ckplus"]
        )

        if success:
            logger.info("Phish CK+ prediction pipeline completed successfully")
            return True
        else:
            logger.error("Failed to export predictions to Supabase")
            return False

    except Exception as e:
        logger.error("Error in Phish CK+ prediction pipeline: %s", e)
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    success = run_phish_ckplus_predictions()
    exit(0 if success else 1)
