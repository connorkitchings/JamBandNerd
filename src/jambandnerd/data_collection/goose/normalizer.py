"""Normalization functions for Goose raw data."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pandas as pd

from jambandnerd.data_collection.utils import compute_source_hash, parse_date


def normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs to `goose_songs_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        api_song_id = item.get("id")
        if not api_song_id:
            continue
        record = {
            "api_song_id": api_song_id,
            "song_name": item.get("name"),
            "first_played": None,
            "last_played": None,
            "times_played": 0,
            "average_length_seconds": None,
            "source_hash": compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `goose_shows_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        if not show_id:
            continue
        record = {
            "show_id": str(show_id),
            "show_date": parse_date(item.get("showdate")),
            "venue_name": item.get("venuename"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "tour_name": item.get("tourname"),
            "source_hash": compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize venues to `goose_venues_raw` schema."""
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
            "created_at": item.get("created_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `goose_setlists_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        set_number = item.get("setnumber")
        song_position = item.get("position")
        song_name = item.get("songname")
        if not (
            show_id
            and set_number is not None
            and song_position is not None
            and song_name
        ):
            continue
        settype = item.get("settype") or ""
        is_encore = settype.lower() == "encore"
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
            "song_position": int(song_position),
            "song_name": song_name,
            "encore": is_encore,
            "notes": item.get("footnote"),
            "source_hash": compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)
