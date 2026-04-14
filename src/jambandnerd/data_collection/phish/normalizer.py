"""Normalization functions for Phish raw data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

import pandas as pd

from jambandnerd.data_collection.utils import compute_source_hash

logger = logging.getLogger(__name__)


def _to_bool(value: Any) -> bool:
    """Coerce a loosely-typed value to bool."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    s = str(value).strip().lower()
    if s in {"true", "t", "yes", "y"}:
        return True
    if s in {"false", "f", "no", "n", ""}:
        return False
    if s.isdigit():
        try:
            return int(s) > 0
        except Exception:
            return False
    return bool(s)


def normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs to `phish_songs_raw` schema."""
    now = datetime.now(timezone.utc).isoformat()
    normalized = [
        {
            "api_song_id": item.get("songid"),
            "song_name": item.get("song"),
            "slug": item.get("slug"),
            "abbreviation": item.get("abbr"),
            "artist": item.get("artist"),
            "debut_date": item.get("debut"),
            "last_played_date": item.get("last_played"),
            "times_played": item.get("times_played"),
            "gap": item.get("gap"),
            "last_permalink": item.get("last_permalink"),
            "debut_permalink": item.get("debut_permalink"),
            "source_hash": compute_source_hash(item),
            "created_at": now,
        }
        for item in raw
        if item.get("songid")
    ]
    df = pd.DataFrame(normalized)
    df.drop_duplicates(subset=["api_song_id"], keep="first", inplace=True)
    return df


def normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `phish_shows_raw` schema."""
    now = datetime.now(timezone.utc).isoformat()
    raw_list = list(raw)
    normalized = [
        {
            "show_id": item.get("showid"),
            "show_year": item.get("showyear"),
            "show_month": item.get("showmonth"),
            "show_day": item.get("showday"),
            "show_date": item.get("showdate"),
            "permalink": item.get("permalink"),
            "exclude_from_stats": item.get("exclude_from_stats"),
            "api_venue_id": item.get("venueid"),
            "setlist_notes": item.get("setlist_notes"),
            "venue_name": item.get("venue"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "api_artist_id": item.get("artistid"),
            "artist_name": item.get("artist_name"),
            "api_tour_id": item.get("tourid"),
            "tour_name": item.get("tour_name"),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "source_hash": compute_source_hash(item),
            "created_at": now,
        }
        for item in raw_list
        if item.get("showid")
    ]
    df = pd.DataFrame(normalized)
    if not df.empty:
        df["api_artist_id"] = pd.to_numeric(
            df["api_artist_id"], errors="coerce"
        ).astype("Int64")
        df["api_tour_id"] = pd.to_numeric(df["api_tour_id"], errors="coerce").astype(
            "Int64"
        )
    return df


def normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize venues to `phish_venues_raw` schema."""
    now = datetime.now(timezone.utc).isoformat()
    venues = {}
    for item in raw:
        venue_id = item.get("venueid")
        if venue_id and venue_id not in venues:
            venues[venue_id] = {
                "api_venue_id": venue_id,
                "venue_name": item.get("venue"),
                "venue_city": item.get("city"),
                "venue_state": item.get("state"),
                "venue_country": item.get("country"),
                "source_hash": compute_source_hash(item),
                "created_at": now,
            }
    df = pd.DataFrame(list(venues.values()))
    df.drop_duplicates(subset=["api_venue_id"], keep="first", inplace=True)
    return df


def normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `phish_setlists_raw` schema."""
    now = datetime.now(timezone.utc).isoformat()
    normalized_rows: List[Dict[str, Any]] = []
    for item in raw:
        if not item.get("uniqueid"):
            continue
        row = {
            "api_unique_id": item.get("uniqueid"),
            "show_id": item.get("showid"),
            "show_date": item.get("showdate"),
            "permalink": item.get("permalink"),
            "api_song_id": item.get("songid"),
            "song_name": item.get("song"),
            "set_number": item.get("set"),
            "position": item.get("position"),
            "transition": item.get("trans_mark"),
            "is_reprise": _to_bool(item.get("isreprise")),
            "is_jam": _to_bool(item.get("isjam")),
            "is_jam_chart": _to_bool(item.get("isjamchart")),
            "track_time": item.get("tracktime"),
            "gap": item.get("gap"),
            "is_original": _to_bool(item.get("is_original")),
            "footnote": item.get("footnote"),
            "source_hash": compute_source_hash(item),
            "created_at": now,
        }
        normalized_rows.append(row)

    df = pd.DataFrame(normalized_rows)
    if not df.empty:
        for col in ["set_number", "song_position", "position", "gap", "track_time"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        initial_rows = len(df)
        df.drop_duplicates(subset=["api_unique_id"], keep="first", inplace=True)
        if len(df) < initial_rows:
            logger.info("Dropped %d duplicate setlist entries.", initial_rows - len(df))
    return df
