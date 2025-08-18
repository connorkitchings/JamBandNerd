"""Runs the Goose data collection pipeline (Goose-first, raw tables).

This script fetches data from the elgoose.net API via the `GooseCollector`,
normalizes responses to the raw table schemas, and performs upserts into
`goose_songs_raw`, `goose_shows_raw`, and `goose_setlists_raw`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.goose.collector import GooseCollector  # noqa: E402
from src.jambandnerd.db.operations import upsert_dataframe  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402


def _compute_source_hash(record: Dict[str, Any]) -> str:
    """Compute a deterministic hash of a JSON-serializable record.

    Args:
        record: The record to hash.

    Returns:
        A hex-encoded SHA256 hash string.
    """
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[str]:
    """Parse a date-like string to ISO date (YYYY-MM-DD) or return None.

    Tries common formats without throwing.
    """
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_duration_seconds(value: Any) -> Optional[int]:
    """Parse duration to seconds from either int or mm:ss string forms."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
        if ":" in text:
            parts = text.split(":")
            try:
                mins = int(parts[-2])
                secs = int(parts[-1])
                return mins * 60 + secs
            except (ValueError, IndexError):
                return None
    return None


def _normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs to `goose_songs_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        # Handle the actual elgoose.net API response structure
        song_name = item.get("name")  # API uses "name" field
        api_song_id = item.get("id")  # API song ID
        if not song_name or not api_song_id:
            continue
        record = {
            "api_song_id": api_song_id,
            "song_name": song_name,
            "first_played": None,  # Not provided by elgoose.net API
            "last_played": None,   # Not provided by elgoose.net API
            "times_played": 0,     # Not provided by elgoose.net API
            "average_length_seconds": None,  # Not provided by elgoose.net API
            "source_hash": _compute_source_hash(item),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `goose_shows_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        # Handle the actual elgoose.net API response structure
        show_id = item.get("show_id")
        show_date = item.get("showdate")
        if not show_id or not show_date:
            continue
        record = {
            "show_id": str(show_id),
            "show_date": _parse_date(show_date),
            "venue_name": item.get("venuename"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "tour_name": item.get("tourname"),
            "source_hash": _compute_source_hash(item),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize venues to `goose_venues_raw` schema using venues endpoint payload.

    Schema fields observed: venue_id, venuename, city, state, country, zip, capacity, slug
    """
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        venue_id = item.get("venue_id")
        name = item.get("venuename")
        if venue_id is None or not name:
            continue
        record = {
            "venue_id": str(venue_id),
            "venue_name": name,
            "city": item.get("city"),
            "state": item.get("state"),
            "country": item.get("country"),
            "zip": item.get("zip"),
            "capacity": int(item.get("capacity") or 0),
            "slug": item.get("slug"),
            "source_hash": _compute_source_hash(item),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `goose_setlists_raw` schema.

    Only rows with resolvable `show_id`, `set_number`, `song_position`, and `song_name`
    are emitted to satisfy NOT NULL constraints.
    """
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        # Handle the actual elgoose.net API response structure
        show_id = item.get("show_id")
        set_number = item.get("setnumber")  # API uses "setnumber"
        song_position = item.get("position")
        song_name = item.get("songname")  # API uses "songname"
        
        if not (show_id and set_number is not None and song_position is not None and song_name):
            # Skip rows we cannot confidently normalize to required schema
            continue
            
        # Skip song_length_seconds - not needed
        
        # Determine if this is an encore based on settype
        settype = item.get("settype") or ""
        is_encore = settype.lower() == "encore"
        
        # Convert set_number - handle encore sets (e.g. "e" -> 99)
        if str(set_number).lower().startswith('e'):
            set_num = 99  # Use 99 for encore sets
        else:
            try:
                set_num = int(set_number)
            except (ValueError, TypeError):
                continue  # Skip invalid set numbers
        
        record = {
            "show_id": str(show_id),
            "set_number": set_num,
            "song_position": int(song_position),
            "song_name": song_name,
            "encore": is_encore,
            "notes": item.get("footnote"),  # API uses "footnote" for notes
            "source_hash": _compute_source_hash(item),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def run_goose_collection() -> None:
    """Collect all Goose data and store it in Supabase raw tables."""
    print("Starting Goose data collection...")
    collector = GooseCollector()
    get_supabase_client()  # environment validation / early failure if misconfigured

    # Collect and insert songs
    print("Collecting songs...")
    songs_raw = collector.collect_songs()
    songs_df = _normalize_songs(songs_raw)
    print(f"Prepared {len(songs_df)} songs for upsert.")
    if not songs_df.empty:
        upsert_dataframe(
            table_name="goose_songs_raw",
            df=songs_df,
            conflict_columns=["api_song_id"],
        )
        print("Inserted/updated songs in goose_songs_raw.")
    else:
        print("No songs normalized; skipping songs upsert.")

    # Collect and insert shows
    print("Collecting shows...")
    shows_raw = collector.collect_shows()
    shows_df = _normalize_shows(shows_raw)
    print(f"Prepared {len(shows_df)} shows for upsert.")
    if not shows_df.empty:
        upsert_dataframe(
            table_name="goose_shows_raw",
            df=shows_df,
            conflict_columns=["show_id"],
        )
        print("Inserted/updated shows in goose_shows_raw.")
    else:
        print("No shows normalized; skipping shows upsert.")

    # Collect and insert venues
    print("Collecting venues...")
    venues_raw = collector.collect_venues()
    venues_df = _normalize_venues(venues_raw)
    print(f"Prepared {len(venues_df)} venues for upsert.")
    if not venues_df.empty:
        try:
            upsert_dataframe(
                table_name="goose_venues_raw",
                df=venues_df,
                conflict_columns=["venue_id"],
            )
            print("Inserted/updated venues in goose_venues_raw.")
        except Exception as exc:
            # Allow pipeline to continue even if venues table is not ready yet
            print(f"Warning: could not upsert venues ({exc}). Skipping venues step.")
    else:
        print("No venues normalized; skipping venues upsert.")

    # Collect and insert setlists
    print("Collecting setlists...")
    setlists_raw = collector.collect_setlists()
    setlists_df = _normalize_setlists(setlists_raw)
    print(f"Prepared {len(setlists_df)} setlist entries for upsert.")
    if not setlists_df.empty:
        upsert_dataframe(
            table_name="goose_setlists_raw",
            df=setlists_df,
            conflict_columns=["show_id", "set_number", "song_position"],
        )
        print("Inserted/updated setlists in goose_setlists_raw.")
    else:
        print("No setlists normalized; skipping setlists upsert.")

    # Log collection run
    try:
        client = get_supabase_client()
        client.table("collection_runs").insert({"band": "goose"}).execute()
        print("Logged collection run.")
    except Exception as exc:
        print(f"Warning: could not log collection run ({exc}).")

    print("Goose data collection finished.")


def run_goose_venues_collection() -> None:
    """Collect venues via the venues endpoint and upsert into goose_venues_raw."""
    print("Starting Goose venues collection...")
    collector = GooseCollector()
    get_supabase_client()
    venues_raw = collector.collect_venues()
    venues_df = _normalize_venues(venues_raw)
    print(f"Prepared {len(venues_df)} venues for upsert.")
    if not venues_df.empty:
        try:
            upsert_dataframe(
                table_name="goose_venues_raw",
                df=venues_df,
                conflict_columns=["venue_id"],
            )
            print("Inserted/updated venues in goose_venues_raw.")
        except Exception as exc:
            print(f"Warning: could not upsert venues ({exc}). Skipping venues step.")
    else:
        print("No venues normalized; skipping venues upsert.")


if __name__ == "__main__":
    run_goose_collection()
