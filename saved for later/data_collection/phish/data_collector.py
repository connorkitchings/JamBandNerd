"""
Phish data collector implementation using the BaseDataCollector pattern.
"""

import pandas as pd
from datetime import datetime, timedelta

from jambandnerd.data_collection.base import APIBasedDataCollector

from .api_utils import get_api_key
from .loaders import load_setlist_data, load_show_data, load_song_data


class PhishDataCollector(APIBasedDataCollector):
    """
    Phish-specific data collector that fetches data from the Phish.net API
    """

    def __init__(self, update_mode: bool = True, force_scrape_all: bool = False):
        super().__init__("phish")
        self.api_key = get_api_key(self.logger)
        self.update_mode = update_mode
        self.force_scrape_all = force_scrape_all

    def get_most_recent_show_date(self) -> str | None:
        """Gets the most recent show date from the phish_shows table."""
        try:
            response = self.supabase_client.table("phish_shows").select("showdate").order("showdate", desc=True).limit(1).execute()
            if response.data:
                return response.data[0]["showdate"]
        except Exception as e:
            self.logger.error("Could not get most recent show date from Supabase: %s", e)
        return None

    def load_data(self) -> dict[str, pd.DataFrame]:
        """
        Load Phish data from the Phish.net API.

        In update mode, it only fetches data since the last show in the database.
        """
        self.logger.info("Starting Phish data loading from API (update_mode=%s)...", self.update_mode)

        since_date = None
        if self.update_mode and not self.force_scrape_all:
            since_date_str = self.get_most_recent_show_date()
            if since_date_str:
                # Convert from MM/DD/YYYY to YYYY-MM-DD for the API
                since_date = datetime.strptime(since_date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
                self.logger.info("Fetching new data since %s", since_date)

        # Always load songs
        self.logger.info("Loading song data...")
        songs_df = load_song_data(self.api_key, self.logger)
        self.logger.info("Loaded %d songs", len(songs_df))

        # Load shows and venues data
        self.logger.info("Loading show and venue data...")
        shows_df, venues_df = load_show_data(self.api_key, self.logger, since=since_date)
        self.logger.info("Loaded %d new shows and %d new venues", len(shows_df), len(venues_df))

        # Load setlists and transitions data
        if not shows_df.empty:
            self.logger.info("Loading setlist and transition data for new shows...")
            show_ids = shows_df["showid"].tolist()
            setlists_df, transitions_df = load_setlist_data(self.api_key, self.logger, show_ids=show_ids)
            self.logger.info(
                "Loaded %d setlist entries and %d transitions",
                len(setlists_df),
                len(transitions_df),
            )
        else:
            self.logger.info("No new shows found, skipping setlist and transition loading.")
            setlists_df, transitions_df = pd.DataFrame(), pd.DataFrame()

        data_frames = {
            "phish_songs": songs_df,
            "phish_shows": shows_df,
            "phish_venues": venues_df,
            "phish_setlists": setlists_df,
            "phish_transitions": transitions_df,
        }

        # Aggressive cleaning
        for name, df in data_frames.items():
            for col in df.columns:
                df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else '')

        return data_frames

        return data_frames

    def get_table_configs(self) -> dict[str, dict[str, any]]:
        """
        Get Phish-specific table export configurations.

        Returns:
            Dictionary mapping table names to export configurations
        """
        return {
            "phish_songs": {
                "conflict_column": "song_id",
                "date_columns": ["debut_date"],  # Convert debut_date to MM/DD/YYYY
            },
            "phish_shows": {
                "conflict_column": "showid",
                "date_columns": ["showdate"],  # Convert showdate to MM/DD/YYYY
            },
            "phish_venues": {
                "conflict_column": "venueid",
                "date_columns": [],  # No date columns in venues
            },
            "phish_setlists": {
                "conflict_column": "uniqueid",
                "date_columns": [],  # No date columns in setlists
            },
            "phish_transitions": {
                "conflict_column": "transition",
                "date_columns": [],  # No date columns in transitions
            },
        }


def main():
    """Main entry point for Phish data collection pipeline."""
    collector = PhishDataCollector()
    success = collector.run_pipeline()
    return success


if __name__ == "__main__":
    main()
