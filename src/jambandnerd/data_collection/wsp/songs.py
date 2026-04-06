"""Module for collecting WSP song data."""

import logging
from io import StringIO
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .parser_profile import DEFAULT_PROFILE
from .session import make_request

if TYPE_CHECKING:
    from .status import CollectionStatus

logger = logging.getLogger(__name__)


def collect_songs(
    session: requests.Session,
    base_url: str,
    status: Optional["CollectionStatus"] = None,
) -> List[Dict[str, Any]]:
    """Collects song data by scraping the song catalog page with rate limiting."""
    url = f"{base_url}/asp/songcode.asp"
    logger.info(f"Scraping songs from {url}")
    try:
        # Use enhanced request method with rate limiting
        response = make_request(session, url)
        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table")

        if len(tables) < DEFAULT_PROFILE.song_table_min_tables:
            logger.error("Could not find the song table on the page.")
            return []

        songs_df = pd.read_html(
            StringIO(str(tables[DEFAULT_PROFILE.song_table_index]))
        )[0]
        songs_df.columns = list(DEFAULT_PROFILE.song_table_columns)
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

    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 403:
            if status:
                status.record_403_error(url)
            logger.warning(
                f"403 Forbidden for {url}. Proceeding without song data. "
                f"(Total 403s: {status.http_403_errors if status else 'N/A'})"
            )
            return []
        else:
            if status:
                status.record_http_error(
                    url, e.response.status_code if e.response else 0
                )
            logger.error(f"Failed to scrape songs: {e}")
            return []
    except Exception as e:
        logger.error(f"Failed to scrape songs: {e}")
        return []
