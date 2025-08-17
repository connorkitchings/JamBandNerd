"""
Goose data collector implementation using the BaseDataCollector pattern.
"""

import pandas as pd
from datetime import datetime, timedelta

from jambandnerd.data_collection.base import APIBasedDataCollector

from .loaders import load_setlist_data, load_show_data, load_song_data


class GooseDataCollector(APIBasedDataCollector):
    """
    Goose-specific data collector that fetches data from the elgoose.net API
    """

    def __init__(self, update_mode: bool = True, force_scrape_all: bool = False):
        super().__init__("goose")  # No API key needed for Goose
        self.update_mode = update_mode
        self.force_scrape_all = force_scrape_all

    def get_most_recent_show_date(self) -> str | None:
        """Gets the most recent show date from the goose_shows table."""
        try:
            response = self.supabase_client.table("goose_shows").select("show_date").order("show_date", desc=True).limit(1).execute()
            if response.data:
                return response.data[0]["show_date"]
        except Exception as e:
            self.logger.error("Could not get most recent show date from Supabase: %s", e)
        return None

    def load_data(self) -> dict[str, pd.DataFrame]:
        """
        Load Goose data from the elgoose.net API

        Returns:
            Dictionary containing songs, shows, venues, setlists, and transitions DataFrames
        """
        self.logger.info("Starting Goose data loading from API (update_mode=%s)...", self.update_mode)

        since_date = None
        if self.update_mode and not self.force_scrape_all:
            since_date_str = self.get_most_recent_show_date()
            if since_date_str:
                # Convert from MM/DD/YYYY to YYYY-MM-DD for the API
                since_date = datetime.strptime(since_date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
                self.logger.info("Fetching new data since %s", since_date)

        # Always load songs
        self.logger.info("Loading song data...")
        song_data = load_song_data(self.logger)
        self.logger.info("Loaded %d songs", len(song_data))

        # Load shows and venues data
        self.logger.info("Loading show and venue data...")
        show_data, venue_data, _ = load_show_data(self.logger, since=since_date)
        self.logger.info("Loaded %d new shows and %d new venues", len(show_data), len(venue_data))

        # Load setlists and transitions data
        if not show_data.empty:
            self.logger.info("Loading setlist and transition data for new shows...")
            setlist_data, transition_data = load_setlist_data(self.logger)
            # Filter setlists for new shows
            show_ids = show_data["show_id"].tolist()
            setlist_data = setlist_data[setlist_data["show_id"].isin(show_ids)]
            self.logger.info(
                "Loaded %d setlist entries and %d transitions",
                len(setlist_data),
                len(transition_data),
            )
        else:
            self.logger.info("No new shows found, skipping setlist and transition loading.")
            setlist_data, transition_data = pd.DataFrame(), pd.DataFrame()

        return {
            "goose_songs": song_data,
            "goose_shows": show_data,
            "goose_venues": venue_data,
            "goose_setlists": setlist_data,
            "goose_transitions": transition_data,
        }

    def get_table_configs(self) -> dict[str, dict[str, any]]:
        """
        Get Goose-specific table export configurations.

        Returns:
            Dictionary mapping table names to export configurations
        """
        return {
            "goose_songs": {
                "conflict_column": "song_id",
                "date_columns": ["debut_date"],  # Convert debut_date to MM/DD/YYYY
            },
            "goose_shows": {
                "conflict_column": "show_id",
                "date_columns": ["show_date"],  # Convert show_date to MM/DD/YYYY
            },
            "goose_venues": {
                "conflict_column": "venue_id",
                "date_columns": [],  # No date columns in venues
            },
            "goose_setlists": {
                "conflict_column": "uniqueid",
                "date_columns": [],  # No date columns in setlists
            },
            "goose_transitions": {
                "conflict_column": "transition_id",
                "date_columns": [],  # No date columns in transitions
            },
        }


def main():
    """Main entry point for Goose data collection pipeline."""
    collector = GooseDataCollector()
    success = collector.run_pipeline()
    return success


if __name__ == "__main__":
    main()
