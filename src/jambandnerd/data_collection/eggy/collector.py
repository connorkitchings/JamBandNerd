"""Data collector for Eggy via thecarton.net API."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
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
        filtered = [
            record
            for record in records
            if self._is_target_artist(record, artist_name=self.ARTIST_NAME)
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

    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse a timestamp value from the API into a datetime object."""
        if not value:
            return None
        try:
            if isinstance(value, str):
                # Handle ISO format with or without timezone
                value = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value)
            if isinstance(value, (int, float)):
                # Assume Unix timestamp
                return datetime.fromtimestamp(value)
        except (ValueError, TypeError) as e:
            logger.debug("Could not parse timestamp %s: %s", value, e)
        return None

    def _filter_by_timestamp(
        self,
        records: List[Dict[str, Any]],
        since: datetime,
        timestamp_field: str = "updated_at",
    ) -> List[Dict[str, Any]]:
        """Filter records to only those updated since the given timestamp."""
        filtered = []
        for record in records:
            record_ts = self._parse_timestamp(record.get(timestamp_field))
            if record_ts and record_ts >= since:
                filtered.append(record)
        return filtered

    def collect_shows_incremental(
        self,
        since: datetime,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Collect shows updated since the given timestamp (incremental mode).

        Args:
            since: Only return shows with updated_at >= this timestamp.
            start_date: Optional date filter (client-side after timestamp filter).
            end_date: Optional date filter (client-side after timestamp filter).

        Returns:
            List of show records updated since the given timestamp.
        """
        records = self._fetch_from_endpoint("v2/shows.json")
        filtered = self._filter_artist(records)

        # Apply timestamp filter
        filtered = self._filter_by_timestamp(
            filtered, since, timestamp_field="updated_at"
        )

        # Apply optional date range filter (client-side)
        if start_date or end_date:
            date_filtered = []
            for record in filtered:
                show_date_str = record.get("showdate") or record.get("show_date")
                if not show_date_str:
                    continue
                try:
                    show_date = datetime.strptime(str(show_date_str), "%Y-%m-%d").date()
                    if start_date and show_date < start_date:
                        continue
                    if end_date and show_date > end_date:
                        continue
                    date_filtered.append(record)
                except ValueError:
                    # Include records with unparseable dates
                    date_filtered.append(record)
            filtered = date_filtered

        logger.info(
            "✅ Eggy: Collected %s shows (incremental since %s).",
            len(filtered),
            since.isoformat(),
        )
        return filtered

    def collect_setlists_incremental(
        self,
        since: datetime,
        show_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Collect setlists updated since the given timestamp (incremental mode).

        Args:
            since: Only return setlists with updated_at >= this timestamp.
            show_ids: Optional list of show IDs to filter by.

        Returns:
            List of setlist records updated since the given timestamp.
        """
        records = self._fetch_from_endpoint("v1/setlists.json")
        filtered = self._filter_artist(records)

        # Apply timestamp filter
        filtered = self._filter_by_timestamp(
            filtered, since, timestamp_field="updated_at"
        )

        # Apply optional show ID filter
        if show_ids:
            id_set = {str(show_id) for show_id in show_ids}
            filtered = [row for row in filtered if str(row.get("show_id")) in id_set]

        logger.info(
            "✅ Eggy: Collected %s setlist rows (incremental since %s).",
            len(filtered),
            since.isoformat(),
        )
        return filtered

    def collect_songs_incremental(self, since: datetime) -> List[Dict[str, Any]]:
        """Collect songs updated since the given timestamp (incremental mode).

        Args:
            since: Only return songs with updated_at >= this timestamp.

        Returns:
            List of song records updated since the given timestamp.
        """
        records = self._fetch_from_endpoint("v2/songs.json")
        records = self._filter_artist(records)

        # Apply timestamp filter
        records = self._filter_by_timestamp(
            records, since, timestamp_field="updated_at"
        )

        logger.info(
            "✅ Eggy: Collected %s songs (incremental since %s).",
            len(records),
            since.isoformat(),
        )
        return records
