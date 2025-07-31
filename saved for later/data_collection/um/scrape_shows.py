"""
Module for scraping and processing Umphrey's McGee show data.
"""

import os
from pathlib import Path

import pandas as pd

from .utils import get_logger

# --- Constants ---
BAND_NAME = "UM"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_COLLECTED_DIR = PROJECT_ROOT / "data" / BAND_NAME / "collected"
LOG_FILE_PATH = PROJECT_ROOT / "logs" / BAND_NAME / "um_pipeline.log"
SHOW_DATA_FILENAME = "showdata.csv"

logger = get_logger(__name__, log_file=LOG_FILE_PATH, add_console_handler=False)


def create_show_data(
    setlist_data: pd.DataFrame, data_dir: str | Path = None
) -> pd.DataFrame:
    """
    Create a DataFrame for showdata.csv: one row per show with unique show ID/link,
    date, venue, city, state, country, and sequential show_number.

    Args:
        setlist_data (pd.DataFrame): DataFrame containing setlist data with show-level columns.
        data_dir (str | Path, optional): Directory to save showdata.csv. Defaults to DATA_DIR.

    Returns:
        pd.DataFrame: DataFrame of unique shows with sequential show_number.
    """
    data_dir = Path(data_dir) if data_dir is not None else Path(DATA_COLLECTED_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    if setlist_data.empty:
        logger.warning("No setlist data provided to create_show_data.")
        return pd.DataFrame()
    # Extract unique shows based on link (show_id), date, venue, city, state, country
    show_cols = ["link", "date", "venue", "city", "state", "country"]
    shows = setlist_data[show_cols].drop_duplicates().copy()
    # Parse date for sorting
    shows["parsed_date"] = pd.to_datetime(shows["date"], errors="coerce")
    shows = shows.sort_values("parsed_date").reset_index(drop=True)
    shows["show_number"] = shows.index + 1
    shows = shows.drop(columns=["parsed_date"])
    # Save to CSV
    showdata_path = data_dir / SHOW_DATA_FILENAME
    shows.to_csv(showdata_path, index=False)
    relative_showdata_path = os.path.relpath(showdata_path)
    logger.info("Saved UM shows data to %s", relative_showdata_path)
    return shows
