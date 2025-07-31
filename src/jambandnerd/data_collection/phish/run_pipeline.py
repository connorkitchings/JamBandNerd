"""
Phish Setlist Creation Pipeline Orchestration Script
Runs the scraping, processing, and saving of Phish show, song, and setlist data.
All configuration is managed via hardcoded paths and environment variables.
"""

import json
import os
import time
from datetime import datetime

from .call_api import get_api_key
from .loaders import (
    load_setlist_data,
    load_show_data,
    load_song_data,
)
from .utils import get_logger


def main() -> bool:
    """
    Main entry point for the Phish data collection pipeline.
    Loads data from API into memory for prediction models to use.
    Returns True if successful, False if any error occurs.
    """
    # Ensure logs/Phish/ is always relative to the project root, not src/
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    logs_dir = os.path.join(project_root, "logs", "Phish")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "phish_pipeline.log")
    logger = get_logger(__name__, log_file=log_file, add_console_handler=True)
    api_key = get_api_key()  # Use utility to load from .env
    data_dir = os.path.join(project_root, "data", "phish", "collected")
    # Log previous last update
    last_updated_path = os.path.join(data_dir, "last_updated.json")
    prev_update = None
    if os.path.exists(last_updated_path):
        try:
            with open(last_updated_path, encoding="utf-8") as f:
                prev_update = json.load(f).get("last_updated")
        except Exception as e:
            logger.warning("Could not read last_updated.json: %s", e)
    if prev_update:
        try:
            # Parse the existing timestamp (assuming YYYY-MM-DD HH:MM:SS)
            dt_object = datetime.strptime(prev_update, "%Y-%m-%d %H:%M:%S")
            # Format to MM/DD/YYYY HH:MM
            formatted_prev_update = dt_object.strftime("%m/%d/%Y %H:%M")
            logger.info("Previous Last update: %s", formatted_prev_update)
        except ValueError:
            # If parsing fails, log the original string as a fallback
            logger.warning(
                "Could not parse previous update timestamp: %s. Logging as is.",
                prev_update,
            )
            logger.info("Previous Last update: %s", prev_update)
    else:
        logger.info("No previous update found.")
    start_time = time.time()
    try:
        logger.info("Loading Song Data")
        song_data = load_song_data(api_key)
        logger.info("Loading Show and Venue Data")
        show_data, venue_data = load_show_data(api_key)
        logger.info("Loading Setlist and Transition Data")
        setlist_data, transition_data = load_setlist_data(api_key)
        logger.info(
            "load_setlist_data returned. Setlist data rows: %s, Transition data rows: %s",
            len(setlist_data),
            len(transition_data),
        )
        # Data is now loaded in-memory and ready for prediction models
        # No need to save raw data to Supabase - only predictions should be saved
        elapsed = time.time() - start_time
        logger.info("Phish pipeline completed in %.2f seconds.", elapsed)
        logger.info("Phish pipeline completed successfully.")
        return True
    except Exception as e:
        # Broad exception catching is generally discouraged, but we want to ensure
        # the pipeline doesn't crash unexpectedly. Instead, log the error and return failure.
        logger.exception("CRITICAL ERROR in main: %s", e)
        return False


if __name__ == "__main__":
    import sys

    if not main():
        sys.exit(1)
