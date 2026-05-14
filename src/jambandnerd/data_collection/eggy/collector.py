"""Data collector for Eggy via thecarton.net API."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Dict, List, Optional

import requests

from ..base import BandCollector
from ..browser import CloudflareBypass
from ..config import get_collector_config

logger = logging.getLogger(__name__)


class EggyCollector(BandCollector):
    """Collect Eggy data from thecarton.net API.

    thecarton.net is behind Cloudflare bot protection.  Standard requests
    return 403 with a JS challenge.  This collector overrides
    ``_fetch_from_endpoint`` to fall back to Playwright when that happens.
    """

    ARTIST_NAME = "Eggy"

    def __init__(self) -> None:
        config = get_collector_config("eggy")
        super().__init__(config)
        logger.info(
            "Initialized EggyCollector with rate limit %s/%ss",
            config.rate_limit_calls,
            config.rate_limit_window,
        )

    def _fetch_from_endpoint(
        self,
        endpoint: str,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            return super()._fetch_from_endpoint(
                endpoint, use_cache=use_cache, cache_ttl=cache_ttl, **kwargs
            )
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 403:
                logger.warning("403 from %s — falling back to Playwright", url)
                return self._fetch_via_playwright(url)
            raise

    def _fetch_via_playwright(self, url: str) -> List[Dict[str, Any]]:
        try:
            response = CloudflareBypass.make_request(url)
            response.raise_for_status()
        except Exception:
            logger.error("Playwright fallback also failed for %s", url)
            return []

        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError):
            logger.error("Playwright returned non-JSON for %s", url)
            return []

        if isinstance(data, dict) and "data" in data:
            return data["data"] or []
        if isinstance(data, list):
            return data
        logger.warning("Unexpected response shape from %s", url)
        return []

    def _filter_artist(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Limit API payloads to the target artist when an artist field exists."""
        if not records:
            return []
        if all(
            "artist" not in record or record.get("artist") is None for record in records
        ):
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
