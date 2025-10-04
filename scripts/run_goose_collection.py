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
from src.jambandnerd.db.operations import upsert_dataframe, get_table_schema  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.db.validation import validate_dataframe_against_table, coerce_df_types # noqa: E402
import argparse


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


def _normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs to `goose_songs_raw` schema."""
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


def _normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `goose_shows_raw` schema."""
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id")
        if not show_id:
            continue
        record = {
            "show_id": str(show_id),
            "show_date": _parse_date(item.get("showdate")),
            "venue_name": item.get("venuename"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "tour_name": item.get("tourname"),
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
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
            "source_hash": _compute_source_hash(item),
            "created_at": item.get("created_at"), # Not in API, will be None
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `goose_setlists_raw` schema."""
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


def run_goose_collection(skip_validation: bool = False) -> None:
    """Collect all Goose data and store it in Supabase raw tables."""
    print("Starting Goose data collection...")
    collector = GooseCollector()
    get_supabase_client()

    # Upsert logic for each table type
    def upsert_table(table_name: str, collector_func, normalizer_func, conflict_cols: List[str]):
        print(f"Collecting {table_name}...")
        raw_data = collector_func()
        df = normalizer_func(raw_data)
        print(f"Prepared {len(df)} records for {table_name}.")
        if df.empty:
            print(f"No data for {table_name}; skipping upsert.")
            return

        schema = get_table_schema(table_name)
        if schema and not skip_validation:
            # First, coerce types to match the database schema.
            coerced_df = coerce_df_types(df, schema)
            # Then, validate the coerced DataFrame.
            report = validate_dataframe_against_table(coerced_df, table_name, schema)
            if not report.is_valid:
                print(f"⚠️  Validation warnings for {table_name}:")
                if report.missing_columns:
                    print(f"    Missing columns: {report.missing_columns}")
                if report.type_mismatches:
                    print(f"    Type mismatches: {len(report.type_mismatches)} columns")
                if report.nullable_violations:
                    print(f"    Nullable violations: {report.nullable_violations}")
                # Proceed anyway with coerced data - validation is now warning-only
            # Use the coerced DataFrame for the upsert
            df_to_upsert = coerced_df
        else:
            df_to_upsert = df
        
        try:
            upsert_dataframe(table_name=table_name, df=df_to_upsert, conflict_columns=conflict_cols)
            print(f"Upserted data into {table_name}.")
        except Exception as e:
            print(f"Error upserting to {table_name}: {e}")

    upsert_table("goose_songs_raw", collector.collect_songs, _normalize_songs, ["api_song_id"])
    upsert_table("goose_shows_raw", collector.collect_shows, _normalize_shows, ["show_id"])
    upsert_table("goose_venues_raw", collector.collect_venues, _normalize_venues, ["venue_id"])
    upsert_table("goose_setlists_raw", collector.collect_setlists, _normalize_setlists, ["show_id", "set_number", "song_position"])

    # Log collection run
    try:
        client = get_supabase_client()
        client.table("collection_runs").insert({"band": "goose"}).execute()
        print("Logged collection run.")
    except Exception as exc:
        print(f"Warning: could not log collection run ({exc}).")

    print("Goose data collection finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Goose data collection with optional schema validation")
    parser.add_argument("--skip-validation", action="store_true", help="Bypass schema validation before upserts")
    args = parser.parse_args()
    run_goose_collection(skip_validation=args.skip_validation)
