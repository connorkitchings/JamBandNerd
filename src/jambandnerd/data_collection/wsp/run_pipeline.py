"""
WSP Setlist Creation Pipeline Orchestration Script

Runs the scraping, processing, and saving of Widespread Panic (WSP) show, song, and setlist data.
All configuration is managed via config.py and environment variables.
"""

import argparse
import os
import time

import pandas as pd

from .cache_utils import (
    get_date_filter_cutoff,
    should_scrape_shows,
    should_scrape_songs,
    update_shows_cache,
    update_songs_cache,
)
from .export_data_supabase import save_wsp_data_to_supabase
from .scrape_setlists import load_setlist_data
from .scrape_shows import scrape_wsp_shows
from .scrape_songs import scrape_wsp_songs
from .utils import get_logger

# --- Constants ---
BAND_NAME = "WSP"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def main(update: bool = True, force_scrape_all: bool = False):
    """Run the WSP data collection and ingestion pipeline for Supabase.

    Args:
        update (bool): If True, runs in update mode, scraping only recent data.
                         Defaults to True.
        force_scrape_all (bool): If True, forces scraping of shows and songs
                                regardless of cache. Defaults to False.
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
    logger.info("Starting optimized WSP data ingestion pipeline for Supabase...")
    start_time = time.time()
    try:
        # Intelligent show scraping with caching
        if should_scrape_shows(force_scrape=force_scrape_all, max_age_days=7):
            logger.info("Scraping WSP show data (cache expired or missing)...")
            show_data = scrape_wsp_shows()
            logger.info("Scraped %d shows.", len(show_data))
            update_shows_cache(len(show_data))
        else:
            logger.info("Skipping show scraping (using cached data - shows don't change frequently)")
            # Load existing show data from Supabase for setlist processing
            from jambandnerd.db.db_utils import get_table_as_dataframe
            show_data = get_table_as_dataframe("wsp_shows")
            logger.info("Loaded %d shows from Supabase cache.", len(show_data))

        # Intelligent song scraping with caching
        if should_scrape_songs(force_scrape=force_scrape_all, max_age_days=7):
            logger.info("Scraping WSP song catalog (cache expired or missing)...")
            song_data = scrape_wsp_songs()
            logger.info("Scraped %d songs.", len(song_data))
            update_songs_cache(len(song_data))
        else:
            logger.info("Skipping song scraping (using cached data - songs don't change frequently)")
            # Load existing song data from Supabase for reference
            from jambandnerd.db.db_utils import get_table_as_dataframe
            song_data = get_table_as_dataframe("wsp_songs")
            logger.info("Loaded %d songs from Supabase cache.", len(song_data))

        # Apply date-based filtering for setlist scraping (last 3 months)
        if update:
            cutoff_date = get_date_filter_cutoff(months_back=3)
            # Filter shows to only recent ones for setlist checking
            if 'date' in show_data.columns:
                show_data['date_parsed'] = pd.to_datetime(show_data['date'], errors='coerce')
                recent_shows = show_data[show_data['date_parsed'] >= cutoff_date]
                logger.info("Filtered to %d recent shows (last 3 months) for setlist checking.", len(recent_shows))
            else:
                logger.warning("No date column found in show data, using all shows")
                recent_shows = show_data
        else:
            recent_shows = show_data

        logger.info("Scraping WSP setlists for %d shows...", len(recent_shows))
        setlist_data = load_setlist_data(shows=recent_shows, update=update, scrape=True)
        if not setlist_data.empty:
            logger.info("Scraped setlist data for %d shows.", setlist_data["link"].nunique())
        else:
            logger.info("No new setlist data to save.")

        logger.info("Saving WSP data to Supabase...")
        # Only save data that was actually scraped (not loaded from cache)
        songs_to_save = song_data if should_scrape_songs(force_scrape=force_scrape_all, max_age_days=7) else pd.DataFrame()
        shows_to_save = show_data if should_scrape_shows(force_scrape=force_scrape_all, max_age_days=7) else pd.DataFrame()
        save_wsp_data_to_supabase(songs_to_save, shows_to_save, setlist_data)
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
    parser.add_argument(
        "--force-scrape-all",
        action="store_true",
        help="Force scraping of shows and songs regardless of cache age.",
    )
    args = parser.parse_args()
    scrape_flag = not args.dry_run
    main(update=args.update, force_scrape_all=args.force_scrape_all)
