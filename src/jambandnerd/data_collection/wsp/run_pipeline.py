"""
WSP Setlist Creation Pipeline Orchestration Script

Runs the scraping, processing, and saving of Widespread Panic (WSP) show, song, and setlist data.
All configuration is managed via config.py and environment variables.
"""

import argparse
import os
import time

from .export_data_supabase import save_wsp_data_to_supabase
from .scrape_setlists import load_setlist_data
from .scrape_shows import scrape_wsp_shows
from .scrape_songs import scrape_wsp_songs
from .utils import get_logger

# --- Constants ---
BAND_NAME = "WSP"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def main(update: bool = True):
    """Run the WSP data collection and ingestion pipeline for Supabase.

    Args:
        update (bool): If True, runs in update mode, scraping only recent data.
                         Defaults to True.
    """
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    logs_dir = os.path.join(project_root, "logs", "WSP")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "wsp_pipeline.log")
    logger = get_logger(
        __name__,
        log_file=log_file,
        add_console_handler=True,
    )
    logger.info("Starting WSP data ingestion pipeline for Supabase...")
    start_time = time.time()
    try:
        logger.info("Scraping WSP show data...")
        show_data = scrape_wsp_shows()
        logger.info("Scraped %d shows.", len(show_data))

        logger.info("Scraping WSP song catalog...")
        song_data = scrape_wsp_songs()
        logger.info("Scraped %d songs.", len(song_data))

        logger.info("Scraping WSP setlists...")
        setlist_data = load_setlist_data(shows=show_data, update=update, scrape=True)
        if not setlist_data.empty:
            logger.info("Scraped setlist data for %d shows.", setlist_data["link"].nunique())
        else:
            logger.info("No new setlist data to save.")

        logger.info("Saving all WSP data to Supabase...")
        save_wsp_data_to_supabase(song_data, show_data, setlist_data)
        elapsed = time.time() - start_time
        logger.info("WSP scraping pipeline completed in %.2f seconds.", elapsed)
    except Exception as e:
        logger.exception("WSP pipeline failed: %s", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the WSP data collection pipeline.")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Run in update mode, scraping only recent data.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip actual web scraping; just show links that would be scraped.",
    )
    args = parser.parse_args()
    scrape_flag = not args.dry_run
    main(update=args.update)
