"""Data collector for Goose from elgoose.net API."""
import requests
import logging
from typing import List, Dict, Any
from datetime import date

from ..base import BandCollector

logger = logging.getLogger(__name__)

class GooseCollector(BandCollector):
    """Collects Goose data from the elgoose.net API."""

    BASE_URL = "https://elgoose.net/api"
    ARTIST_NAME = "Goose"

    def collect_shows(self, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """Collects show data from the elgoose.net API."""
        logger.info("Collecting Goose shows...")
        response = requests.get(f"{self.BASE_URL}/v2/shows.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        records = data.get('data', [])
        # Filter to Goose-only (exclude side projects like Vasudo)
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [r for r in records if str(r.get('artist', '')).strip().lower() == artist_lower]
        logger.info(f"Collected {len(filtered)} Goose shows.")
        return filtered

    def collect_setlists(self, show_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Collects setlist data from the elgoose.net API."""
        logger.info("Collecting Goose setlists...")
        response = requests.get(f"{self.BASE_URL}/v1/setlists.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        records = data.get('data', [])
        # Filter to Goose-only setlist rows
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [r for r in records if str(r.get('artist', '')).strip().lower() == artist_lower]
        logger.info(f"Collected {len(filtered)} Goose setlist records.")
        return filtered

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects song data from the elgoose.net API."""
        logger.info("Collecting Goose songs...")
        response = requests.get(f"{self.BASE_URL}/v2/songs.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        records = data.get('data', [])
        logger.info(f"Collected {len(records)} Goose songs.")
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collects venues data from the elgoose.net API."""
        logger.info("Collecting Goose venues...")
        response = requests.get(f"{self.BASE_URL}/v2/venues.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        records = data.get('data', [])
        logger.info(f"Collected {len(records)} Goose venues.")
        return records
