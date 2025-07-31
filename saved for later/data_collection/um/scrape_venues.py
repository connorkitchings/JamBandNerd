"""
Module for scraping UM venue data from allthings.umphreys.com.
"""

from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .utils import get_logger

BAND_NAME = "UM"
BASE_URL = "https://allthings.umphreys.com"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_COLLECTED_DIR = PROJECT_ROOT / "data" / BAND_NAME / "collected"
LOG_FILE_PATH = PROJECT_ROOT / "logs" / BAND_NAME / "um_pipeline.log"
VENUE_TABLE_IDX = 0

logger = get_logger(__name__, log_file=LOG_FILE_PATH, add_console_handler=False)


def scrape_um_venues(base_url: str = BASE_URL) -> pd.DataFrame:
    """
    Scrape and return UM venue data from allthings.umphreys.com.

    Args:
        base_url (str): Base URL for the UM website (default is BASE_URL).

    Returns:
        pd.DataFrame: DataFrame containing venue data with columns such as 'id', 'Last Played', etc.
    """
    venues_url = f"{base_url}/venues/"
    response = requests.get(venues_url, timeout=60)  # Added timeout
    response.raise_for_status()
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")
    if not tables or len(tables) <= VENUE_TABLE_IDX:
        logger.error(
            "Expected venue table at index %s not found in UM venue page.",
            VENUE_TABLE_IDX,
        )
        return pd.DataFrame()
    tables_str = str(tables)
    tables_io = StringIO(tables_str)
    tables = pd.read_html(tables_io)
    venue_data = tables[VENUE_TABLE_IDX].copy().reset_index(names="id")
    venue_data["id"] = venue_data["id"].astype(str)
    venue_data["Last Played"] = pd.to_datetime(venue_data["Last Played"]).dt.date
    logger.info("Scraped %s venues from %s", len(venue_data), venues_url)
    return venue_data
