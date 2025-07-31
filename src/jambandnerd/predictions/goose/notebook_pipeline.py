"""
Goose Notebook prediction pipeline.

This module orchestrates the Notebook model prediction process for Goose:
1. Load and transform data
2. Run Notebook model
3. Export predictions to Supabase
"""

import logging

from jambandnerd.models.notebook_model import run_notebook_model
from jambandnerd.models.prediction_exporter import save_predictions_to_supabase

from .data_transformer import get_band_config, prepare_data_for_notebook_model

logger = logging.getLogger(__name__)


def run_goose_notebook_predictions() -> bool:
    """
    Run the complete Goose Notebook prediction pipeline.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        logger.info("Starting Goose Notebook prediction pipeline...")

        # Step 1: Load and transform data
        logger.info("Loading and transforming Goose data...")
        (
            song_data,
            show_data,
            venue_data,
            setlist_data,
            transition_data,
        ) = prepare_data_for_notebook_model()

        # Step 2: Get band configuration
        config = get_band_config()

        # Step 3: Run Notebook model
        logger.info("Running Notebook model...")
        predictions_df = run_notebook_model(
            song_data=song_data,
            show_data=show_data,
            venue_data=venue_data,
            setlist_data=setlist_data,
            transition_data=transition_data,
            recent_shows_filter=config["recent_shows_filter"],
        )

        if predictions_df is None or predictions_df.empty:
            logger.error("Notebook model returned no predictions")
            return False

        # Step 4: Export predictions to Supabase
        logger.info("Exporting %d predictions to Supabase...", len(predictions_df))
        success = save_predictions_to_supabase(
            predictions_df, config["supabase_table_notebook"]
        )

        if success:
            logger.info("Goose Notebook prediction pipeline completed successfully")
            return True
        else:
            logger.error("Failed to export predictions to Supabase")
            return False

    except Exception as e:
        logger.error("Error in Goose Notebook prediction pipeline: %s", e)
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    success = run_goose_notebook_predictions()
    exit(0 if success else 1)
