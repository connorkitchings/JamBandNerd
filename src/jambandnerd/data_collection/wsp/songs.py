"""Module for collecting WSP song data."""

import logging
from io import StringIO
from typing import Any, Dict, List

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .session import make_request

logger = logging.getLogger(__name__)


def collect_songs(session: requests.Session, base_url: str) -> List[Dict[str, Any]]:
    """Collects song data by scraping the song catalog page with rate limiting."""
    url = f"{base_url}/asp/songcode.asp"
    logger.info(f"Scraping songs from {url}")
    try:
        # Use enhanced request method with rate limiting
        response = make_request(session, url)
        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table")

        if len(tables) < 5:
            logger.error("Could not find the song table on the page.")
            return []

        songs_df = pd.read_html(StringIO(str(tables[4])))[0]
        songs_df.columns = [
            "code",
            "song_name",
            "first_played",
            "last_played",
            "times_played",
            "aka",
        ]
        songs_df.dropna(subset=["code", "song_name"], inplace=True)

        # Clean and format data
        songs_df["times_played"] = (
            pd.to_numeric(songs_df["times_played"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        for col in ["first_played", "last_played"]:
            songs_df[col] = pd.to_datetime(
                songs_df[col], format="%m/%d/%y", errors="coerce"
            ).dt.date

        logger.info(f"✅ Widespread Panic: Scraped {len(songs_df)} songs.")
        # Explicit type conversion to satisfy type checker
        return [dict(row) for row in songs_df.to_dict("records")]  # type: ignore[misc]

    except Exception as e:
        logger.error(f"Failed to scrape songs: {e}")
        return []
