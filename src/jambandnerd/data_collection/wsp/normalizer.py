
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
            "last_played": None,   # Not in API
            "times_played": 0,     # Not in API
            "average_length_seconds": None, # Not in API
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `wsp_shows_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        if not show_id:
            continue
        record = {
            "show_id": str(show_id),
            "show_date": _parse_date(item.get("showdate")),
            "venue_name": item.get("name"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "tour_name": item.get("tourname"),
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        print(f"Record before appending: {record}")
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
            "created_at": item.get("created_at"), # Not in API, will be None
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `wsp_setlists_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        set_number = item.get("setnumber")
        song_position = item.get("position")
        song_name = item.get("songname")
        if not (show_id and set_number is not None and song_position is not None and song_name):
            continue
        settype = item.get("settype") or ""
        is_encore = settype.lower() == "encore"
        if str(set_number).lower().startswith('e'):
            set_num = 99
        else:
            try:
                set_num = int(set_number)
            except (ValueError, TypeError):
                continue
        record = {
            "show_id": str(show_id),
            "set_number": set_num,
            "song_position": int(song_position),
            "song_name": song_name,
            "encore": is_encore,
            "notes": item.get("footnote"),
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"), # Not in API, will be None
            "updated_at": item.get("updated_at"), # Not in API, will be None
        }
        normalized.append(record)
    return pd.DataFrame(normalized)
