import argparse
import logging

from jambandnerd.data_collection.wsp.data_transformer import (
    transform_setlists_for_supabase,
    transform_shows_for_supabase,
    transform_songs_for_supabase,
)
from jambandnerd.data_collection.wsp.scrape_setlists import load_setlist_data
from jambandnerd.data_collection.wsp.scrape_shows import scrape_wsp_shows
from jambandnerd.data_collection.wsp.scrape_songs import scrape_wsp_songs
from jambandnerd.models.data_exporter import export_dataframe_to_supabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_wsp_pipeline(test_mode: bool = False):
    """Runs the full WSP data collection pipeline and uploads to Supabase.

    Args:
        test_mode: If True, scrapes only a small subset of data for testing.
    """
    # Scrape Data
    logging.info("Starting WSP data scraping...")
    songs_df = scrape_wsp_songs()
    shows_df = scrape_wsp_shows(start_year=2023) if test_mode else scrape_wsp_shows()
    setlists_df = load_setlist_data(shows_df.head(3)) if test_mode else load_setlist_data(shows_df)
    logging.info(
        "Scraped %d songs, %d shows, and %d setlist entries.",
        len(songs_df),
        len(shows_df),
        len(setlists_df),
    )

    # Transform Data
    logging.info("Transforming data for Supabase...")
    songs_supabase = transform_songs_for_supabase(songs_df)
    shows_supabase = transform_shows_for_supabase(shows_df)
    setlists_supabase = transform_setlists_for_supabase(setlists_df)

    # Upload to Supabase
    logging.info("Uploading data to Supabase...")
    export_dataframe_to_supabase(songs_supabase, "wsp_songs", "code", logging)
    export_dataframe_to_supabase(shows_supabase, "wsp_shows", "link", logging)
    export_dataframe_to_supabase(setlists_supabase, "wsp_setlists", "link,song_index_show", logging)

    logging.info("WSP Supabase pipeline completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the WSP data collection pipeline and upload to Supabase.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode, scraping only a small subset of data.",
    )
    args = parser.parse_args()

    run_wsp_pipeline(test_mode=args.test)
