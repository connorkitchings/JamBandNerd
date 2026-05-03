"""Normalization functions for Eggy raw data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

import pandas as pd

from jambandnerd.data_collection.utils import compute_source_hash, parse_date


def normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs into `eggy_songs_raw` schema."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        api_song_id = item.get("id") or item.get("song_id")
        if not api_song_id:
            continue
        record = {
            "api_song_id": str(api_song_id),
            "song_name": item.get("name") or item.get("song_name"),
            "first_played": item.get("first_played"),
            "last_played": item.get("last_played"),
            "times_played": item.get("times_played") or item.get("play_count") or 0,
            "average_length_seconds": item.get("average_length_seconds"),
            "source_hash": compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows into `eggy_shows_raw` schema."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id") or item.get("id")
        if not show_id:
            continue
        record = {
            "show_id": str(show_id),
            "show_date": parse_date(item.get("showdate") or item.get("show_date")),
            "venue_name": item.get("venuename") or item.get("venue_name"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "tour_name": item.get("tourname") or item.get("tour_name"),
            "source_hash": compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize venues into `eggy_venues_raw` schema."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        venue_id = item.get("venue_id") or item.get("id")
        if not venue_id:
            continue
        record = {
            "venue_id": str(venue_id),
            "venue_name": item.get("venuename") or item.get("name"),
            "city": item.get("city"),
            "state": item.get("state"),
            "country": item.get("country"),
            "zip": item.get("zip"),
            "capacity": int(item.get("capacity") or 0),
            "slug": item.get("slug"),
            "source_hash": compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlist rows into `eggy_setlists_raw` schema."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id") or item.get("id")
        set_number = item.get("setnumber") or item.get("set_number")
        song_position = item.get("position") or item.get("song_position")
        song_name = item.get("songname") or item.get("song_name")
        if not (
            show_id
            and set_number is not None
            and song_position is not None
            and song_name
        ):
            continue

        settype = item.get("settype") or item.get("set_type") or ""
        is_encore = str(settype).strip().lower() == "encore"
        set_value = set_number
        if isinstance(set_value, str) and set_value.lower().startswith("e"):
            set_value = 99
        else:
            try:
                set_value = int(set_value)
            except (ValueError, TypeError):
                continue

        record = {
            "show_id": str(show_id),
            "set_number": set_value,
            "song_position": int(song_position),
            "song_name": song_name,
            "encore": bool(is_encore),
            "notes": item.get("footnote") or item.get("notes"),
            "source_hash": compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)
