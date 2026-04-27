from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from jambandnerd.data_collection.utils import compute_source_hash
from jambandnerd.data_collection.wsp.song_canonicalizer import canonicalize_song_name

logger = logging.getLogger(__name__)


def _parse_date(value: Optional[str]) -> Optional[str]:
    """Parse a date-like string to ISO date (YYYY-MM-DD) or return None."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


def normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs to `wsp_songs_raw` schema.

    Handles two formats:
    1. EC Collector: {code, song_name, first_played, last_played, times_played, aka}
    2. API format: {id, name, ...}
    """
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        song_code = item.get("code") or item.get("id")
        song_name = item.get("song_name") or item.get("name")
        if not song_code and not song_name:
            continue
        record = {
            "song_code": song_code,
            "song_name": song_name,
            "aka": item.get("aka"),
            "first_played": item.get("first_played"),
            "last_played": item.get("last_played"),
            "times_played": item.get("times_played", 0),
            "source_hash": compute_source_hash(item),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `wsp_shows_raw` schema.

    Supports two formats:
    1. TourWrangler API: {show_id, showdate, name, city, state, ...}
    2. EC Collector: {show_date, venue_name, city, state, source_url}
    """
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        if show_id in (None, ""):
            continue

        # Support both API format (showdate, name) and EC format (show_date, venue_name)
        show_date_raw = item.get("show_date") or item.get("showdate")
        venue_name = item.get("venue_name") or item.get("name")
        city = item.get("city")
        state = item.get("state")

        record = {
            "show_id": str(show_id),
            "show_date": (
                _parse_date(show_date_raw)
                if show_date_raw and not show_date_raw.count("-") == 2
                else show_date_raw
            ),
            "venue_name": venue_name,
            "city": city,
            "state": state,
            "show_notes": item.get("show_notes"),
            "source_url": item.get("source_url"),
            "source_hash": compute_source_hash(item),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize venues to `wsp_venues_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        venue_id = item.get("venue_id")
        if not venue_id:
            continue
        record = {
            "venue_id": str(venue_id),
            "venue_name": item.get("venuename"),
            "city": item.get("city"),
            "state": item.get("state"),
            "country": item.get("country"),
            "zip": item.get("zip"),
            "capacity": int(item.get("capacity") or 0),
            "slug": item.get("slug"),
            "source_hash": compute_source_hash(item),
            "created_at": item.get("created_at"),  # Not in API, will be None
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_setlists(
    raw: Iterable[Dict[str, Any]],
    canonical_lookup: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Normalize setlists to `wsp_setlists_raw` schema.

    Args:
        raw: Iterable of raw setlist dicts from any WSP source.
        canonical_lookup: Optional lowercase->canonical mapping from
            song_canonicalizer.build_canonical_lookup().
    """
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        set_number = (
            item.get("setnumber")
            if item.get("setnumber") is not None
            else item.get("set_number")
        )
        song_position = (
            item.get("position")
            if item.get("position") is not None
            else item.get("song_position")
        )
        song_name = item.get("songname") or item.get("song_name")

        if not (
            show_id
            and set_number is not None
            and song_position is not None
            and song_name
        ):
            continue
        try:
            song_position_int = int(song_position)
        except (ValueError, TypeError):
            continue
        if song_position_int <= 0:
            continue
        if str(set_number).lower().startswith("e"):
            set_num = 99
        else:
            try:
                set_num = int(set_number)
            except (ValueError, TypeError):
                continue

        canonical = canonicalize_song_name(song_name, canonical_lookup)
        if canonical != song_name:
            logger.debug("Canonicalized song name: %r -> %r", song_name, canonical)

        record = {
            "show_id": str(show_id),
            "set_number": set_num,
            "song_position": song_position_int,
            "song_name": canonical,
            "is_segue": item.get("is_segue", False),
            "song_notes": item.get("footnote") or item.get("song_notes"),
            "source": item.get("source", "everydaycompanion"),
            "source_hash": compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)
