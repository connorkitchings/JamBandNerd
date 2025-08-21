"""Data collector for Goose from elgoose.net API."""
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import date

from ..base import BandCollector

logger = logging.getLogger(__name__)

class GooseCollector(BandCollector):
    """Collects Goose data from the elgoose.net API."""

    BASE_URL = "https://elgoose.net/api"
    ARTIST_NAME = "Goose"

    def _fetch_from_endpoint(self, endpoint: str) -> List[Dict[str, Any]]:
        """Private helper to fetch data from a given API endpoint."""
        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"Fetching data from {url}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('error'):
                raise RuntimeError(f"API Error at {endpoint}: {data.get('error_message', 'Unknown error')}")
            return data.get('data', [])
        except requests.RequestException as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise

    def collect_shows(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Collects show data, filtering to Goose-only artists."""
        records = self._fetch_from_endpoint("v2/shows.json")
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [r for r in records if str(r.get('artist', '')).strip().lower() == artist_lower]
        logger.info(f"Collected {len(filtered)} Goose shows.")
        return filtered

    def collect_setlists(self, show_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collects setlist data, filtering to Goose-only artists."""
        records = self._fetch_from_endpoint("v1/setlists.json")
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [r for r in records if str(r.get('artist', '')).strip().lower() == artist_lower]
        logger.info(f"Collected {len(filtered)} Goose setlist records.")
        return filtered

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects all song data."""
        records = self._fetch_from_endpoint("v2/songs.json")
        logger.info(f"Collected {len(records)} Goose songs.")
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collects all venue data."""
        records = self._fetch_from_endpoint("v2/venues.json")
        logger.info(f"Collected {len(records)} Goose venues.")
        return records