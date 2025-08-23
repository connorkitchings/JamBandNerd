"""Data collector for Phish from phish.net API."""
import os
import time
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import date

from ..base import BandCollector

logger = logging.getLogger(__name__)

class PhishCollector(BandCollector):
    """Collects Phish data from the phish.net API, mirroring the Goose collector's structure."""

    BASE_URL = "https://api.phish.net/v5"

    def __init__(self):
        self.api_key = os.getenv("PHISH_API_KEY")
        if not self.api_key:
            raise ValueError("PHISH_API_KEY environment variable not set.")

    def _fetch_from_endpoint(self, endpoint: str) -> List[Dict[str, Any]]:
        """Private helper to fetch data with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}.json?apikey={self.api_key}"
        logger.info(f"Fetching data from {url}...")
        retries = 5
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=120)
                response.raise_for_status()
                return response.json().get('data', [])
            except (requests.exceptions.ChunkedEncodingError, requests.exceptions.RequestException) as e:
                logger.warning(
                    "API request failed on attempt %d/%d for endpoint '%s': %s",
                    attempt + 1,
                    retries,
                    endpoint,
                    e,
                )
                if attempt < retries - 1:
                    time.sleep(3 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("API request failed after %d retries.", retries)
                    raise
        return []

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects all song data."""
        records = self._fetch_from_endpoint("songs")
        logger.info(f"Collected {len(records)} Phish songs.")
        return records

    def collect_shows(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Collects all show data."""
        records = self._fetch_from_endpoint("shows/artist/phish")
        logger.info(f"Collected {len(records)} Phish shows.")
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collects all show data and extracts unique venues from it."""
        shows_data = self.collect_shows()
        if not shows_data:
            logger.warning("Cannot collect venues without show data.")
            return []

        venues = {}
        for show in shows_data:
            venue_id = show.get("venueid")
            if venue_id and venue_id not in venues:
                venues[venue_id] = {
                    "api_venue_id": venue_id,
                    "venue_name": show.get("venue"),
                    "venue_city": show.get("city"),
                    "venue_state": show.get("state"),
                    "venue_country": show.get("country"),
                }

        venue_list = list(venues.values())
        logger.info(f"Extracted {len(venue_list)} unique Phish venues.")
        return venue_list

    def collect_setlists(self, show_ids: List[str]) -> List[Dict[str, Any]]:
        """Collects setlist data for a specific list of show IDs."""
        if not show_ids:
            return []

        all_setlists = []
        logger.info(f"Collecting setlists for {len(show_ids)} shows...")
        for show_id in show_ids:
            # The phish.net API uses a different endpoint to get a setlist by showid
            endpoint = f"setlists/showid/{show_id}"
            try:
                # This endpoint returns a list with one element which is a dict containing the setlist
                setlist_data = self._fetch_from_endpoint(endpoint)
                if setlist_data:
                    all_setlists.extend(setlist_data)
                time.sleep(0.5)  # Respectful delay between API calls
            except Exception as e:
                logger.error(f"Failed to fetch setlist for show_id {show_id}: {e}")
        
        logger.info(f"Collected {len(all_setlists)} total setlist records.")
        return all_setlists