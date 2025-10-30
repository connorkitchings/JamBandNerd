"""Data collector for Eggy via thecarton.net API."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)


class EggyCollector(BandCollector):
    """Collect Eggy data from thecarton.net API."""

    ARTIST_NAME = "Eggy"

    def __init__(self) -> None:
        config = get_collector_config("eggy")
        super().__init__(config)
        logger.info(
            "Initialized EggyCollector with rate limit %s/%ss",
            config.rate_limit_calls,
            config.rate_limit_window,
        )

    def _filter_artist(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Limit API payloads to the target artist when an artist field exists."""
        if not records:
            return []
        if all("artist" not in record or record.get("artist") is None for record in records):
            return records
        artist_lower = self.ARTIST_NAME.lower()
        filtered = [
            record
            for record in records
            if str(record.get("artist", "")).strip().lower() == artist_lower
        ]
        logger.debug("Filtered %s records down to %s", len(records), len(filtered))
        return filtered

    def collect_shows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Collect show metadata for Eggy."""
        # thecarton does not support date-range filters; apply client side if needed.
        records = self._fetch_from_endpoint("v2/shows.json")
        filtered = self._filter_artist(records)
        logger.info("✅ Eggy: Collected %s shows.", len(filtered))
        if start_date or end_date:
            logger.debug(
                "Date filtering requested (start=%s end=%s) but not applied upstream.",
                start_date,
                end_date,
            )
        return filtered

    def collect_setlists(
        self, show_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Collect setlists for Eggy shows."""
        records = self._fetch_from_endpoint("v1/setlists.json")
        filtered = self._filter_artist(records)
        if show_ids:
            id_set = {str(show_id) for show_id in show_ids}
            filtered = [row for row in filtered if str(row.get("show_id")) in id_set]
        logger.info("✅ Eggy: Collected %s setlist rows.", len(filtered))
        return filtered

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collect Eggy's song catalog."""
        records = self._fetch_from_endpoint("v2/songs.json")
        records = self._filter_artist(records)
        logger.info("✅ Eggy: Collected %s songs.", len(records))
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collect venue metadata referenced by Eggy shows."""
        records = self._fetch_from_endpoint("v2/venues.json")
        logger.info("✅ Eggy: Collected %s venues.", len(records))
        return records
