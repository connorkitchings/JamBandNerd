from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


def _compute_source_hash(record: Dict[str, Any]) -> str:
    """Compute a deterministic hash of a JSON-serializable record."""
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
    """Normalize songs to `wsp_songs_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        api_song_id = item.get("id")
        if not api_song_id:
            continue
        record = {
            "api_song_id": api_song_id,
            "song_name": item.get("name"),
            "first_played": None,  # Not in API
            "last_played": None,  # Not in API
            "times_played": 0,  # Not in API
            "average_length_seconds": None,  # Not in API
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
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
            "source_hash": _compute_source_hash(item),
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
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"),  # Not in API, will be None
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `wsp_setlists_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        # Support both API format (setnumber) and EC format (set_number)
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
        record = {
            "show_id": str(show_id),
            "set_number": set_num,
            "song_position": song_position_int,
            "song_name": song_name,
            # Database doesn't have 'encore' column (derived from set_number)
            "is_segue": item.get("is_segue", False),
            "song_notes": item.get("footnote") or item.get("song_notes"),
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"),  # Not in API, will be None
            "updated_at": item.get("updated_at"),  # Not in API, will be None
        }
        normalized.append(record)
    return pd.DataFrame(normalized)
