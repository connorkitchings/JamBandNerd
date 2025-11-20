"""
WSP data collector implementation using the BaseDataCollector pattern.

This version removes local caching: shows and songs are always scraped from
everydaycompanion.com. Setlist scraping remains incremental via per-link
existence checks in loaders, and update-mode filters recent shows (last 90 days).
"""

from datetime import datetime, timedelta

import pandas as pd
from jambandnerd.data_collection.wsp.loaders import (
    load_setlist_data,
    scrape_wsp_shows,
    scrape_wsp_songs,
)

from jambandnerd.data_collection.base import ScrapingBasedDataCollector


class WSPDataCollector(ScrapingBasedDataCollector):
    """
    WSP-specific data collector that scrapes data from everydaycompanion.com,
    with integrated caching, transformation, and export logic.
    """

    def __init__(self, update_mode: bool = True, force_scrape_all: bool = False):
        super().__init__("wsp", "https://everydaycompanion.com")
        self.update_mode = update_mode
        self.force_scrape_all = force_scrape_all

    def load_data(self) -> dict[str, pd.DataFrame]:
        """
        Load WSP data with incremental update logic (no local caching for shows/songs).

        Returns:
            A dictionary containing 'wsp_songs', 'wsp_shows', and 'wsp_setlists' DataFrames.
        """
        self.logger.info(
            "Starting WSP data collection (update=%s, force_scrape=%s)...",
            self.update_mode,
            self.force_scrape_all,
        )

        # Always scrape show data from source (no local caching)
        self.logger.info("Scraping WSP show data from source...")
        shows_df = scrape_wsp_shows(self.logger)
        self.logger.info("Scraped %d shows.", len(shows_df))

        # Always scrape song catalog from source (no local caching)
        self.logger.info("Scraping WSP song catalog from source...")
        songs_df = scrape_wsp_songs(self.logger)
        self.logger.info("Scraped %d songs.", len(songs_df))

        # Intelligent setlist scraping with date-based filtering for updates
        if self.update_mode and not self.force_scrape_all:
            # For update mode, only scrape setlists for recent shows (last 3 months)
            cutoff_date = datetime.now() - timedelta(days=90)
            cutoff_str = cutoff_date.strftime("%m/%d/%Y")

            # Filter shows to recent ones only
            shows_df["date_parsed"] = pd.to_datetime(
                shows_df["date"], format="%m/%d/%Y", errors="coerce"
            )
            recent_shows = shows_df[shows_df["date_parsed"] >= cutoff_date].copy()

            # Clean up temporary column from shows_df before export
            shows_df = shows_df.drop(columns=["date_parsed"])

            self.logger.info(
                "Update mode: Scraping setlists for %d recent shows (since %s) out of %d total shows",
                len(recent_shows),
                cutoff_str,
                len(shows_df),
            )

            if len(recent_shows) > 0:
                setlists_df = load_setlist_data(
                    shows=recent_shows, logger=self.logger, update=self.update_mode, scrape=True
                )
            else:
                self.logger.info("No recent shows found, skipping setlist scraping")
                setlists_df = pd.DataFrame()
        else:
            # Full scrape mode - scrape all shows
            self.logger.info(
                "Full scrape mode: Scraping setlists for all %d shows...", len(shows_df)
            )
            setlists_df = load_setlist_data(
                shows=shows_df, logger=self.logger, update=self.update_mode, scrape=True
            )

        # No cache metadata to update (local caching removed)

        return {
            "wsp_songs": songs_df,
            "wsp_shows": shows_df,
            "wsp_setlists": setlists_df,
        }

    def get_table_configs(self) -> dict[str, dict[str, str | list[str]]]:
        """
        Get WSP-specific table export configurations.

        Returns:
            Dictionary mapping table names to export configurations
        """
        return {
            "wsp_songs": {
                "conflict_column": "code",
                "date_columns": ["first_played", "last_played"],  # No date columns in songs
            },
            "wsp_shows": {
                "conflict_column": "link",
                "date_columns": ["date"],  # Convert date to MM/DD/YYYY
            },
            "wsp_setlists": {
                "conflict_column": "link,song_index_show",  # Composite key
                "date_columns": [],  # No date columns in setlists
            },
        }


def main():
    """Main entry point for WSP data collection pipeline."""
    collector = WSPDataCollector()
    success = collector.run_pipeline()
    return success


if __name__ == "__main__":
    main()
