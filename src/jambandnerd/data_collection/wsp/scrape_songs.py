"""
Scrape WSP song data from everydaycompanion.com. Standalone after refactor.
"""

from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .utils import get_logger

# Inlined constants
SONG_CODES_TABLE_IDX = 1
SONG_CODES_URL = "https://www.everydaycompanion.com/songlist/"

logger = get_logger(__name__, add_console_handler=True)


def scrape_wsp_songs(
    base_url: str = "http://www.everydaycompanion.com/",
) -> pd.DataFrame:
    """
    Scrape and return the WSP song catalog from everydaycompanion.com.

    Args:
        base_url (str): Base URL for Everyday Companion.
        Defaults to 'http://www.everydaycompanion.com/'.

    Returns:
        pd.DataFrame: DataFrame with columns
        ['song', 'code', 'times_played', 'aka', 'ftp', 'ltp'].
    """
    songcode_url = f"{base_url}asp/songcode.asp"
    try:
        response = requests.get(songcode_url, timeout=10)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all("table")
    except Exception as e:
        logger.exception("Error fetching song codes: %s", e)
        return pd.DataFrame()
    # Table index 4 contains the song catalog
    song_table_idx = 4
    if not tables or len(tables) <= song_table_idx:
        logger.error(
            "Expected song catalog table at index %s not found in song codes page.",
            song_table_idx,
        )
        return pd.DataFrame()
    # Parse the table with pandas
    song_table_html = str(tables[song_table_idx])
    try:
        # Wrap HTML string in StringIO to avoid FutureWarning
        song_codes = pd.read_html(StringIO(song_table_html))[0]
    except Exception as e:
        # NOTE: This exception is broad due to unpredictable HTML parsing errors
        logger.error("Failed to parse song catalog table: %s", e)
        return pd.DataFrame()
    # Rename columns
    song_codes.columns = [
        "code",
        "song",
        "first_played",
        "last_played",
        "times_played",
        "aka",
    ]
    # Drop any rows where 'code' or 'song' is missing
    song_codes = song_codes.dropna(subset=["code", "song"]).reset_index(drop=True)
    # Convert times_played to int, fill missing with 0
    song_codes["times_played"] = (
        pd.to_numeric(song_codes["times_played"], errors="coerce").fillna(0).astype(int)
    )

    # Clean and format date columns
    for col in ["first_played", "last_played"]:
        # Replace non-date strings like 'First' with NaT
        song_codes[col] = song_codes[col].replace("First", None)
        # Convert to datetime, coercing errors to NaT (Not a Time)
        song_codes[col] = pd.to_datetime(song_codes[col], errors="coerce")

    return song_codes
