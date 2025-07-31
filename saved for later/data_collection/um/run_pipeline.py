"""
UM Setlist Creation Pipeline Orchestration Script
Runs the scraping, processing, and saving of UM show, song, and setlist data.
All configuration is managed via hardcoded paths and environment variables.
"""

import os
import time
import traceback
from datetime import datetime
from pathlib import Path

from .export_data import save_query_data, save_um_data
from .scrape_setlists import fetch_um_setlist_data
from .scrape_shows import create_show_data
from .scrape_songs import scrape_um_songs
from .scrape_venues import scrape_um_venues
from .utils import get_last_update_time, get_logger

# Define constants locally
DATETIME_FORMAT = "%m/%d/%Y %H:%M"
BAND_NAME = "UM"


def main() -> None:
    """
    Orchestrates the UM scraping pipeline: scrapes song, venue, and setlist data, saves the results,
    and logs progress and errors.

    Inputs: None (uses utility functions and imported modules).
    Outputs: None (side effects: saves data to disk, logs output).
    """
    # Ensure logs/UM/ is always relative to the project root, not src/
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    logs_dir = os.path.join(project_root, "logs", "UM")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "um_pipeline.log")
    logger = get_logger(
        __name__,
        log_file=log_file,
        add_console_handler=True,
    )
    data_dir = Path(project_root) / "data" / BAND_NAME / "collected"
    # Log previous last update (only once, using utility)
    last_update_str = get_last_update_time(data_dir)
    if last_update_str:
        try:
            dt_object = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
            formatted_prev_update = dt_object.strftime(DATETIME_FORMAT)
            logger.info("Previous Last update: %s", formatted_prev_update)
        except ValueError:
            logger.warning(
                "Could not parse previous update timestamp: %s. Logging as is.",
                last_update_str,
            )
            logger.info("Previous Last update: %s", last_update_str)
    else:
        logger.info("No previous update found.")
    start_time = time.time()
    try:
        # Scrape songs
        logger.info("Scraping latest song data...")
        song_data = scrape_um_songs()
        logger.info("Song scraping completed. Found %s songs.", len(song_data))

        # Scrape venues
        logger.info("Scraping latest venue data...")
        venue_data = scrape_um_venues()

        # Scrape setlists
        logger.info("Scraping full setlist data...")
        setlist_data = fetch_um_setlist_data()
        logger.info(
            "Fetched %s setlist songs for %s shows.",
            len(setlist_data),
            len(setlist_data["link"].unique()),
        )

        # Create and save showdata.csv
        create_show_data(setlist_data, data_dir)

        # Save all data
        save_um_data(song_data, venue_data, setlist_data, data_dir)
        save_query_data(data_dir)
        elapsed = time.time() - start_time
        logger.info("UM pipeline completed in %.2f seconds.", elapsed)
    # TODO: Narrow this exception handling to catch only expected errors
    except Exception as e:
        logger.error("UM pipeline failed: %s", e)
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
