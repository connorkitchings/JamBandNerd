"""Data collector for Phish from phish.net API."""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import date

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)

class PhishCollector(BandCollector):
    """Collects Phish data from the phish.net API with enhanced error handling."""

    ARTIST_NAME = "Phish"

    def __init__(self):
        config = get_collector_config('phish')
        super().__init__(config)
        
        # Phish.net requires an API key
        self.api_key = os.getenv("PHISH_API_KEY")
        if not self.api_key:
            raise ValueError("PHISH_API_KEY environment variable not set.")
        
        logger.info(f"Initialized PhishCollector with API key and rate limit: {config.rate_limit_calls}/{config.rate_limit_window}s")

    def _fetch_phish_endpoint(self, endpoint: str) -> List[Dict[str, Any]]:
        """Phish-specific endpoint fetcher that adds API key to requests."""
        # Add .json suffix and API key parameter for phish.net
        full_endpoint = f"{endpoint}.json?apikey={self.api_key}"
        
        try:
            response_data = self._fetch_from_endpoint(full_endpoint)
            # Phish.net API wraps data in a 'data' field
            if isinstance(response_data, dict):
                return response_data.get('data', [])
            return response_data
        except Exception as e:
            logger.error(f"Failed to fetch from phish.net endpoint {endpoint}: {e}")
            raise

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects all song data."""
        records = self._fetch_phish_endpoint("songs")
        logger.info(f"Collected {len(records)} Phish songs.")
        return records

    def collect_shows(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Collects all show data."""
        records = self._fetch_phish_endpoint("shows/artist/phish")
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

    def collect_setlists(self, show_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collects setlist data for a specific list of show IDs."""
        if not show_ids:
            return []

        # Lazy import to avoid hard dependency during other operations
        try:
            from tqdm import tqdm  # type: ignore
        except Exception:
            tqdm = None  # Fallback if tqdm is not available

        all_setlists = []
        logger.info(f"Collecting setlists for {len(show_ids)} shows...")
        iterable = tqdm(show_ids, desc="Phish setlists", unit="show") if tqdm else show_ids
        for show_id in iterable:
            # The phish.net API uses a different endpoint to get a setlist by showid
            endpoint = f"setlists/showid/{show_id}"
            try:
                # This endpoint returns a list with one element which is a dict containing the setlist
                setlist_data = self._fetch_phish_endpoint(endpoint)
                if setlist_data:
                    all_setlists.extend(setlist_data)
                # Rate limiting is now handled by the base class
            except Exception as e:
                logger.error(f"Failed to fetch setlist for show_id {show_id}: {e}")
        
        logger.info(f"Collected {len(all_setlists)} total setlist records.")
        return all_setlists
