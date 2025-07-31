"""
Goose Setlist Creation Pipeline Orchestration Script.
Runs the scraping, processing, and saving of Goose show, song, and setlist data.
All configuration is managed via config.py and environment variables.
"""

import json
import os
import time
import traceback

from .loaders import load_goose_data
from .utils import get_logger


def main() -> None:
    """
    Orchestrate the Goose data collection pipeline: load data from API into memory for prediction models to use.
    """
    # Ensure logs/Goose/ is always relative to the project root, not src/
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    logs_dir = os.path.join(project_root, "logs", "Goose")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "goose_pipeline.log")
    logger = get_logger(__name__, log_file=log_file)
    data_dir = os.path.join(project_root, "data", "goose", "collected")
    # Log previous last update
    last_updated_path = os.path.join(data_dir, "last_updated.json")
    prev_update = None
    if os.path.exists(last_updated_path):
        try:
            with open(last_updated_path, encoding="utf-8") as f:
                prev_update = json.load(f).get("last_updated")
        # Intentionally broad Exception catch to ensure pipeline continues
        # if last_updated.json is corrupt or missing
        except Exception as e:
            logger.warning("Could not read last_updated.json: %s", e)
    if prev_update:
        logger.info("Previous Last update: %s", prev_update)
    else:
        logger.info("No previous update found.")
    start_time = time.time()
    try:
        # Load all data from API (in-memory only)
        song_data, show_data, venue_data, setlist_data, transition_data, next_show_info = load_goose_data()
        
        # Data is now loaded in-memory and ready for prediction models
        # No raw data export - only predictions should be saved to Supabase
        elapsed = time.time() - start_time
        logger.info("Goose data collection completed in %.2f seconds.", elapsed)
        logger.info("Data loaded in-memory and ready for prediction models.")
    # Intentionally broad Exception catch for pipeline robustness; logs all errors for debuggin
    except Exception as e:
        logger.error("Goose pipeline failed: %s\n%s", e, traceback.format_exc())


if __name__ == "__main__":
    main()
