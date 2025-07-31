"""
High-level API client for fetching all Phish data into memory.
"""
import os
from typing import Dict

import pandas as pd

from .call_api import get_api_key
from .loaders import load_song_data, load_show_data, load_setlist_data
from .utils import get_logger

# Set up logger
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
logs_dir = os.path.join(project_root, "logs", "Phish")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "phish_pipeline.log")
logger = get_logger(__name__, log_file=log_file, add_console_handler=True)


def load_all_phish_data_from_api() -> Dict[str, pd.DataFrame]:
    """
    Fetches all required Phish data from the Phish.net API and returns it as a
    dictionary of pandas DataFrames.

    This function orchestrates calls to the lower-level loaders and provides a
    single entry point for loading data into memory without saving to disk or DB.

    Returns:
        Dict[str, pd.DataFrame]: A dictionary where keys are table names
        (e.g., 'songs', 'shows') and values are the corresponding DataFrames.
    """
    logger.info("Starting Phish data load from API into memory...")
    try:
        api_key = get_api_key()

        logger.info("Loading song data...")
        songs_df = load_song_data(api_key)

        logger.info("Loading show and venue data...")
        shows_df, venues_df = load_show_data(api_key)

        logger.info("Loading setlist and transition data...")
        setlists_df, transitions_df = load_setlist_data(api_key)

        data_frames = {
            "phish_songs": songs_df,
            "phish_shows": shows_df,
            "phish_venues": venues_df,
            "phish_setlists": setlists_df,
            "phish_transitions": transitions_df,
        }

        logger.info("Successfully loaded all Phish data into memory.")
        for name, df in data_frames.items():
            logger.info(f"  - {name}: {len(df)} records")

        return data_frames

    except Exception as e:
        logger.exception("CRITICAL ERROR during in-memory Phish data load: %s", e)
        # In case of failure, return a dictionary with empty dataframes
        # to prevent downstream consumers from failing on a None object.
        return {
            "phish_songs": pd.DataFrame(),
            "phish_shows": pd.DataFrame(),
            "phish_venues": pd.DataFrame(),
            "phish_setlists": pd.DataFrame(),
            "phish_transitions": pd.DataFrame(),
        }
