"""Data collector for Goose from elgoose.net API."""
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)

class GooseCollector(BandCollector):
    """Collects Goose data from the elgoose.net API with enhanced error handling."""

    ARTIST_NAME = "Goose"

    def __init__(self):
        config = get_collector_config('goose')
        super().__init__(config)
        logger.info(f"Initialized GooseCollector with rate limit: {config.rate_limit_calls}/{config.rate_limit_window}s")

    def collect_shows(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Collects show data, filtering to Goose-only artists."""
        records = self._fetch_from_endpoint("v2/shows.json")
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [r for r in records if str(r.get('artist', '')).strip().lower() == artist_lower]
        logger.info(f"✅ {self.ARTIST_NAME}: Collected {len(filtered)} shows.")
        return filtered

    def collect_setlists(self, show_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collects setlist data, filtering to Goose-only artists."""
        records = self._fetch_from_endpoint("v1/setlists.json")
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [r for r in records if str(r.get('artist', '')).strip().lower() == artist_lower]
        logger.info(f"✅ {self.ARTIST_NAME}: Collected {len(filtered)} setlist records.")
        return filtered

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects all song data."""
        records = self._fetch_from_endpoint("v2/songs.json")
        logger.info(f"✅ {self.ARTIST_NAME}: Collected {len(records)} songs.")
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collects all venue data."""
        records = self._fetch_from_endpoint("v2/venues.json")
        logger.info(f"✅ {self.ARTIST_NAME}: Collected {len(records)} venues.")
        return records
