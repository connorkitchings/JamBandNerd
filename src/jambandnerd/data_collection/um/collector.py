"""Umphrey's McGee data collector using official JSON API."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

from requests import RequestException

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)


class UmCollector(BandCollector):
    """Collector for Umphrey's McGee data from allthings.umphreys.com."""

    ARTIST_ID = 1  # Umphrey's McGee artist ID
    ARTIST_NAME = "Umphrey's McGee"
    BASE_URL = "https://allthings.umphreys.com"
    EARLIEST_YEAR = 1998

    def __init__(self) -> None:
        config = get_collector_config("um")
        super().__init__(config)
        logger.info(
            "Initialized UmCollector with API base: %s",
            self.config.base_url,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def collect_songs(self) -> List[Dict[str, Any]]:
        """Fetch the UM song catalog from the official JSON API."""
        url = f"{self.config.base_url.rstrip('/')}/v2/songs.json"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
        except RequestException as exc:
            logger.error("Failed to fetch UM songs from %s: %s", url, exc)
            return []
        except ValueError as exc:
            logger.error("Failed to parse UM songs JSON from %s: %s", url, exc)
            return []

        if data.get("error"):
            logger.error("UM songs API error: %s", data.get("error_message"))
            return []

        records: List[Dict[str, Any]] = []
        for song in data.get("data", []):
            song_id = song.get("id")
            song_name = str(song.get("name") or "").strip()
            if song_id is None or not song_name:
                continue
            records.append(
                {
                    "song_id": song_id,
                    "song_name": song_name,
                    "song_slug": song.get("slug"),
                    "original_artist": song.get("original_artist"),
                    "is_original": _coerce_api_bool(song.get("isoriginal")),
                    "api_created_at": song.get("created_at"),
                    "api_updated_at": song.get("updated_at"),
                }
            )

        logger.info(
            "✅ %s: Collected %s songs via API.", self.ARTIST_NAME, len(records)
        )
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Fetch UM venue data from the official JSON API."""
        url = f"{self.config.base_url.rstrip('/')}/v2/venues.json"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
        except RequestException as exc:
            logger.error("Failed to fetch UM venues from %s: %s", url, exc)
            return []
        except ValueError as exc:
            logger.error("Failed to parse UM venues JSON from %s: %s", url, exc)
            return []

        if data.get("error"):
            logger.error("UM venues API error: %s", data.get("error_message"))
            return []

        records: List[Dict[str, Any]] = []
        for venue in data.get("data", []):
            venue_id = venue.get("venue_id")
            venue_name = str(venue.get("venuename") or "").strip()
            if venue_id is None or not venue_name:
                continue
            records.append(
                {
                    "venue_id": venue_id,
                    "venue_name": venue_name,
                    "venue_city": venue.get("city"),
                    "venue_state": venue.get("state"),
                    "venue_country": venue.get("country"),
                    "venue_zip": venue.get("zip"),
                    "capacity": venue.get("capacity"),
                    "venue_slug": venue.get("slug"),
                }
            )

        logger.info(
            "✅ %s: Collected %s venues via API.", self.ARTIST_NAME, len(records)
        )
        return records

    def collect_shows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch show metadata for a date range via API."""

        if end_date and start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        start = start_date or date(self.EARLIEST_YEAR, 1, 1)
        end = end_date or date.today()

        records: List[Dict[str, Any]] = []
        years = range(start.year, end.year + 1)

        for year in years:
            url = f"{self.config.base_url.rstrip('/')}/v2/shows/show_year/{year}.json"
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    continue

                for show in data.get("data", []):
                    if not self._is_target_artist(show, artist_id=self.ARTIST_ID):
                        continue

                    show_date_str = show.get("showdate")
                    if not show_date_str:
                        continue
                    try:
                        show_date = datetime.strptime(show_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        continue

                    if show_date < start or show_date > end:
                        continue

                    records.append(
                        {
                            "show_id": show.get("show_id"),
                            "source_url": urljoin(
                                self.BASE_URL, show.get("permalink", "")
                            ),
                            "show_date": show_date.isoformat(),
                            "venue_name": show.get("venuename"),
                            "venue_city": show.get("city"),
                            "venue_state": show.get("state"),
                            "venue_country": show.get("country"),
                            "show_notes": show.get("shownotes"),
                            "show_year": show_date.year,
                            "show_month": show_date.month,
                            "show_day": show_date.day,
                            "tour_name": show.get("tourname"),
                        }
                    )
            except Exception as exc:
                logger.error("Failed to fetch UM shows for %s: %s", year, exc)

        records.sort(key=lambda item: item["show_date"])
        logger.info(
            "✅ %s: Collected %s shows between %s and %s via API.",
            self.ARTIST_NAME,
            len(records),
            start,
            end,
        )
        return records

    def collect_setlists(
        self, shows_to_process: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch setlist rows for the provided shows via API."""

        shows_list = list(shows_to_process)
        if not shows_list:
            return []

        # Identify unique years to fetch in bulk
        years = set()
        for s in shows_list:
            sd = s.get("show_date")
            if sd:
                years.add(datetime.fromisoformat(sd).year)

        # Mapping for quick lookup
        show_ids_to_process = {str(s.get("show_id")) for s in shows_list}

        results: List[Dict[str, Any]] = []
        for year in sorted(years):
            url = f"{self.config.base_url.rstrip('/')}/v2/setlists/showyear/{year}.json"
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    continue

                # Group by show_id to calculate song_position
                show_data = {}
                for row in data.get("data", []):
                    if not self._is_target_artist(row, artist_id=self.ARTIST_ID):
                        continue

                    show_id = str(row.get("show_id"))
                    if show_id not in show_ids_to_process:
                        continue
                    if show_id not in show_data:
                        show_data[show_id] = []
                    show_data[show_id].append(row)

                for show_id, rows in show_data.items():
                    # Sort by API position just in case
                    rows.sort(key=lambda r: int(r.get("position") or 0))

                    current_set = None
                    song_pos = 0

                    for row in rows:
                        set_num = str(row.get("setnumber"))
                        if set_num != current_set:
                            current_set = set_num
                            song_pos = 1
                        else:
                            song_pos += 1

                        results.append(
                            {
                                "show_id": show_id,
                                "song_id": row.get("song_id"),
                                "song_name": row.get("songname"),
                                "set_label": row.get("settype"),
                                "set_sequence": set_num,
                                "song_position": song_pos,
                                "show_position": row.get("position"),
                                "transition": row.get("transition"),
                                "footnote_text": row.get("footnote"),
                            }
                        )
            except Exception as exc:
                logger.error("Failed to fetch UM setlists for %s: %s", year, exc)

        logger.info(
            "✅ %s: Collected %s setlist rows via API.", self.ARTIST_NAME, len(results)
        )
        return results

    # ------------------------------------------------------------------
    # Incremental Collection API (using api_updated_at timestamps)
    # ------------------------------------------------------------------
    def _parse_api_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse a timestamp value from the UM API into a datetime object."""
        if not value:
            return None
        try:
            if isinstance(value, str):
                # Handle ISO format with or without timezone
                value = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value)
        except (ValueError, TypeError) as e:
            logger.debug("Could not parse UM API timestamp %s: %s", value, e)
        return None

    def _filter_by_api_timestamp(
        self,
        records: List[Dict[str, Any]],
        since: datetime,
        timestamp_field: str = "updated_at",
    ) -> List[Dict[str, Any]]:
        """Filter records to only those updated since the given timestamp."""
        filtered = []
        for record in records:
            record_ts = self._parse_api_timestamp(record.get(timestamp_field))
            if record_ts and record_ts >= since:
                filtered.append(record)
        return filtered

    def collect_songs_incremental(self, since: datetime) -> List[Dict[str, Any]]:
        """Collect songs updated since the given timestamp (incremental mode).

        Args:
            since: Only return songs with updated_at >= this timestamp.

        Returns:
            List of song records updated since the given timestamp.
        """
        url = f"{self.config.base_url.rstrip('/')}/v2/songs.json"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
        except (RequestException, ValueError) as exc:
            logger.error("Failed to fetch UM songs for incremental update: %s", exc)
            return []

        if data.get("error"):
            logger.error("UM songs API error: %s", data.get("error_message"))
            return []

        # Filter by timestamp
        all_songs = data.get("data", [])
        filtered = self._filter_by_api_timestamp(
            all_songs, since, timestamp_field="updated_at"
        )

        records: List[Dict[str, Any]] = []
        for song in filtered:
            song_id = song.get("id")
            song_name = str(song.get("name") or "").strip()
            if song_id is None or not song_name:
                continue
            records.append(
                {
                    "song_id": song_id,
                    "song_name": song_name,
                    "song_slug": song.get("slug"),
                    "original_artist": song.get("original_artist"),
                    "is_original": _coerce_api_bool(song.get("isoriginal")),
                    "api_created_at": song.get("created_at"),
                    "api_updated_at": song.get("updated_at"),
                }
            )

        logger.info(
            "✅ %s: Collected %s songs via API (incremental since %s).",
            self.ARTIST_NAME,
            len(records),
            since.isoformat(),
        )
        return records

    def collect_shows_incremental(
        self,
        since: datetime,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch shows updated since the given timestamp (incremental mode).

        Args:
            since: Only return shows with updated_at >= this timestamp.
            start_date: Optional date filter (client-side after timestamp filter).
            end_date: Optional date filter (client-side after timestamp filter).

        Returns:
            List of show records updated since the given timestamp.
        """
        if end_date and start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        # For incremental, we still need to check recent years
        # UM doesn't have a "since" parameter, so we fetch years and filter
        start = start_date or date(self.EARLIEST_YEAR, 1, 1)
        end = end_date or date.today()

        records: List[Dict[str, Any]] = []
        years = range(start.year, end.year + 1)

        for year in years:
            url = f"{self.config.base_url.rstrip('/')}/v2/shows/show_year/{year}.json"
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    continue

                # Filter by timestamp first
                year_shows = data.get("data", [])
                timestamp_filtered = self._filter_by_api_timestamp(
                    year_shows, since, timestamp_field="updated_at"
                )

                for show in timestamp_filtered:
                    if not self._is_target_artist(show, artist_id=self.ARTIST_ID):
                        continue

                    show_date_str = show.get("showdate")
                    if not show_date_str:
                        continue
                    try:
                        show_date = datetime.strptime(show_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        continue

                    if show_date < start or show_date > end:
                        continue

                    records.append(
                        {
                            "show_id": show.get("show_id"),
                            "source_url": urljoin(
                                self.BASE_URL, show.get("permalink", "")
                            ),
                            "show_date": show_date.isoformat(),
                            "venue_name": show.get("venuename"),
                            "venue_city": show.get("city"),
                            "venue_state": show.get("state"),
                            "venue_country": show.get("country"),
                            "show_notes": show.get("shownotes"),
                            "show_year": show_date.year,
                            "show_month": show_date.month,
                            "show_day": show_date.day,
                            "tour_name": show.get("tourname"),
                            "api_updated_at": show.get("updated_at"),
                        }
                    )
            except Exception as exc:
                logger.error("Failed to fetch UM shows for %s: %s", year, exc)

        records.sort(key=lambda item: item["show_date"])
        logger.info(
            "✅ %s: Collected %s shows via API (incremental since %s).",
            self.ARTIST_NAME,
            len(records),
            since.isoformat(),
        )
        return records

    def collect_setlists_incremental(
        self,
        since: datetime,
        shows_to_process: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch setlists updated since the given timestamp (incremental mode).

        Args:
            since: Only return setlists with updated_at >= this timestamp.
            shows_to_process: Optional list of shows to filter by.

        Returns:
            List of setlist records updated since the given timestamp.
        """
        # Determine which years to fetch
        years = set()
        if shows_to_process:
            shows_list = list(shows_to_process)
            for s in shows_list:
                sd = s.get("show_date")
                if sd:
                    years.add(datetime.fromisoformat(sd).year)
        else:
            # If no shows specified, check recent years (last 2 years for incremental)
            current_year = datetime.now().year
            years = set(range(current_year - 1, current_year + 1))

        # Mapping for quick lookup
        show_ids_to_process = None
        if shows_to_process:
            show_ids_to_process = {str(s.get("show_id")) for s in shows_to_process}

        results: List[Dict[str, Any]] = []
        for year in sorted(years):
            url = f"{self.config.base_url.rstrip('/')}/v2/setlists/showyear/{year}.json"
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    continue

                # Group by show_id to calculate song_position
                show_data = {}
                for row in data.get("data", []):
                    # Check timestamp filter
                    row_ts = self._parse_api_timestamp(row.get("updated_at"))
                    if not row_ts or row_ts < since:
                        continue

                    if not self._is_target_artist(row, artist_id=self.ARTIST_ID):
                        continue

                    show_id = str(row.get("show_id"))
                    if show_ids_to_process and show_id not in show_ids_to_process:
                        continue
                    if show_id not in show_data:
                        show_data[show_id] = []
                    show_data[show_id].append(row)

                for show_id, rows in show_data.items():
                    # Sort by API position just in case
                    rows.sort(key=lambda r: int(r.get("position") or 0))

                    current_set = None
                    song_pos = 0

                    for row in rows:
                        set_num = str(row.get("setnumber"))
                        if set_num != current_set:
                            current_set = set_num
                            song_pos = 1
                        else:
                            song_pos += 1

                        results.append(
                            {
                                "show_id": show_id,
                                "song_id": row.get("song_id"),
                                "song_name": row.get("songname"),
                                "set_label": row.get("settype"),
                                "set_sequence": set_num,
                                "song_position": song_pos,
                                "show_position": row.get("position"),
                                "transition": row.get("transition"),
                                "footnote_text": row.get("footnote"),
                            }
                        )
            except Exception as exc:
                logger.error("Failed to fetch UM setlists for %s: %s", year, exc)

        logger.info(
            "✅ %s: Collected %s setlist rows via API (incremental since %s).",
            self.ARTIST_NAME,
            len(results),
            since.isoformat(),
        )
        return results


def _coerce_api_bool(value: Any) -> bool | None:
    """Normalize boolean-like values returned by the UM API."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", ""}:
            return False
    return bool(value)
