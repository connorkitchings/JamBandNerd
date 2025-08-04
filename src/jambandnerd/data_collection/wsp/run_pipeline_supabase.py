"""WSP Setlist Creation Pipeline for Supabase

This module is a wrapper around the main WSP pipeline that ensures the caching logic
is used properly when running in CI or other contexts. It prevents unnecessary scraping
of all shows and songs when they haven't changed.
"""

import argparse
import logging
import time

import pandas as pd

# Import the main pipeline's caching utilities
from jambandnerd.data_collection.wsp.cache_utils import (
    get_date_filter_cutoff,
    should_scrape_shows,
    should_scrape_songs,
    update_shows_cache,
    update_songs_cache,
)
from jambandnerd.data_collection.wsp.data_transformer import (
    transform_setlists_for_supabase,
    transform_shows_for_supabase,
    transform_songs_for_supabase,
)
from jambandnerd.data_collection.wsp.export_data_supabase import save_wsp_data_to_supabase
from jambandnerd.data_collection.wsp.scrape_setlists import load_setlist_data
from jambandnerd.data_collection.wsp.scrape_shows import scrape_wsp_shows
from jambandnerd.data_collection.wsp.scrape_songs import scrape_wsp_songs
from jambandnerd.data_collection.wsp.utils import get_logger
from jambandnerd.db.db_utils import get_table_as_dataframe

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = get_logger(__name__, add_console_handler=True)


def run_wsp_pipeline(test_mode: bool = False, update: bool = True, force_scrape_all: bool = False):
    """Runs the full WSP data collection pipeline and uploads to Supabase.

    Uses caching logic to avoid unnecessary scraping of shows and songs.

    Args:
        test_mode: If True, runs in test mode with limited data
        update: If True, only scrapes recent shows (last 3 months)
        force_scrape_all: If True, forces scraping of all shows and songs

    Returns:
    """
    logger.info("Starting optimized WSP data ingestion pipeline for Supabase...")
    start_time = time.time()

    try:
        # Intelligent show scraping with caching
        if should_scrape_shows(force_scrape=force_scrape_all, max_age_days=7) or test_mode:
            logger.info("Scraping WSP show data (cache expired or missing)...")
            shows_df = scrape_wsp_shows(start_year=2023) if test_mode else scrape_wsp_shows()
            logger.info("Scraped %d shows.", len(shows_df))
            update_shows_cache(len(shows_df))
        else:
            logger.info("Skipping show scraping (using cached data)")
            # Load existing show data from Supabase
            shows_df = get_table_as_dataframe("wsp_shows")
            logger.info("Loaded %d shows from Supabase cache.", len(shows_df))

        # Intelligent song scraping with caching
        if should_scrape_songs(force_scrape=force_scrape_all, max_age_days=7) or test_mode:
            logger.info("Scraping WSP song catalog (cache expired or missing)...")
            songs_df = scrape_wsp_songs()
            logger.info("Scraped %d songs.", len(songs_df))
            update_songs_cache(len(songs_df))
        else:
            logger.info("Skipping song scraping (using cached data)")
            # Load existing song data from Supabase
            songs_df = get_table_as_dataframe("wsp_songs")
            logger.info("Loaded %d songs from Supabase cache.", len(songs_df))

        # Apply date-based filtering for setlist scraping
        if update and not test_mode:
            cutoff_date = get_date_filter_cutoff(months_back=3)
            # Filter shows to only recent ones for setlist checking
            if 'date' in shows_df.columns:
                shows_df['date_parsed'] = pd.to_datetime(shows_df['date'], errors='coerce')
                recent_shows = shows_df[shows_df['date_parsed'] >= cutoff_date]
                logger.info("Filtered to %d recent shows (last 3 months) for setlist checking.", len(recent_shows))
            else:
                logger.warning("No date column found in show data, using all shows")
                recent_shows = shows_df
        else:
            # For test mode or non-update mode
            if test_mode:
                # In test mode, just use a few shows
                recent_shows = shows_df.head(3)
            else:
                recent_shows = shows_df

        # Scrape setlists
        logger.info("Scraping WSP setlists for %d shows...", len(recent_shows))
        setlists_df = load_setlist_data(shows=recent_shows, update=update, scrape=True)

        # Transform data for Supabase
        logger.info("Transforming data for Supabase...")
        songs_supabase = transform_songs_for_supabase(songs_df) if should_scrape_songs(force_scrape=force_scrape_all, max_age_days=7) or test_mode else pd.DataFrame()
        shows_supabase = transform_shows_for_supabase(shows_df) if should_scrape_shows(force_scrape=force_scrape_all, max_age_days=7) or test_mode else pd.DataFrame()
        setlists_supabase = transform_setlists_for_supabase(setlists_df)

        # Save to Supabase
        logger.info("Saving WSP data to Supabase...")
        save_wsp_data_to_supabase(songs_supabase, shows_supabase, setlists_supabase)

        elapsed = time.time() - start_time
        logger.info("WSP pipeline completed in %.2f seconds.", elapsed)
        return True
    except Exception as e:
        logger.exception("WSP pipeline failed: %s", e)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the WSP data collection pipeline and upload to Supabase.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode, scraping only a small subset of data.",
    )
    args = parser.parse_args()

    run_wsp_pipeline(test_mode=args.test)
