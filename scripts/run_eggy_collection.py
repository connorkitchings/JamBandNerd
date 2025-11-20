"""Run the Eggy data collection pipeline (raw tables).

This script fetches data from thecarton.net API via the `EggyCollector`,
normalizes responses to the Supabase raw schemas, and performs upserts into
`eggy_songs_raw`, `eggy_shows_raw`, `eggy_setlists_raw`, and `eggy_venues_raw`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

# Ensure project root on path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import (  # noqa: E402
    assert_required_columns,
    ensure_source_reachable,
)
from src.jambandnerd.data_collection.eggy.collector import EggyCollector  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.db.operations import (  # noqa: E402
    get_table_schema,
    upsert_dataframe,
)
from src.jambandnerd.db.validation import (  # noqa: E402
    coerce_df_types,
    validate_dataframe_against_table,
)


def _compute_source_hash(record: Dict[str, Any]) -> str:
    """Compute a deterministic hash of a JSON payload."""
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[str]:
    """Parse a date-like string to ISO format or return None."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


def _normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
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
            "source_hash": _compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows into `eggy_shows_raw` schema."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id") or item.get("id")
        if not show_id:
            continue
        record = {
            "show_id": str(show_id),
            "show_date": _parse_date(item.get("showdate") or item.get("show_date")),
            "venue_name": item.get("venuename") or item.get("venue_name"),
            "venue_city": item.get("city"),
            "venue_state": item.get("state"),
            "venue_country": item.get("country"),
            "tour_name": item.get("tourname") or item.get("tour_name"),
            "source_hash": _compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
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
            "source_hash": _compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def _normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlist rows into `eggy_setlists_raw` schema."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        show_id = item.get("show_id") or item.get("id")
        set_number = item.get("setnumber") or item.get("set_number")
        song_position = item.get("position") or item.get("song_position")
        song_name = item.get("songname") or item.get("song_name")
        if not (show_id and set_number is not None and song_position is not None and song_name):
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
            "source_hash": _compute_source_hash(item),
            "api_created_at": item.get("created_at"),
            "api_updated_at": item.get("updated_at"),
            "ingested_at": ingested_at,
        }
        normalized.append(record)
    return pd.DataFrame(normalized)


def run_eggy_collection(skip_validation: bool = False) -> None:
    """Collect Eggy data and store it in Supabase raw tables."""
    print("Starting Eggy data collection...")
    ensure_source_reachable("eggy")
    collector = EggyCollector()
    get_supabase_client()

    def upsert_table(
        table_name: str,
        collector_func,
        normalizer_func,
        conflict_cols: List[str],
        required_columns: Optional[List[str]] = None,
    ) -> None:
        print(f"Collecting {table_name}...")
        raw_data = collector_func()
        df = normalizer_func(raw_data)
        print(f"Prepared {len(df)} records for {table_name}.")
        if df.empty:
            print(f"No data for {table_name}; skipping upsert.")
            return

        if required_columns:
            assert_required_columns(table_name, df, required_columns)

        schema = get_table_schema(table_name)
        if schema and not skip_validation:
            coerced_df = coerce_df_types(df, schema)
            report = validate_dataframe_against_table(coerced_df, table_name, schema)
            if not report.is_valid:
                print(f"⚠️  Validation warnings for {table_name}:")
                if report.missing_columns:
                    print(f"    Missing columns: {report.missing_columns}")
                if report.type_mismatches:
                    print(f"    Type mismatches: {len(report.type_mismatches)} columns")
                if report.nullable_violations:
                    print(f"    Nullable violations: {report.nullable_violations}")
            df_to_upsert = coerced_df
        else:
            df_to_upsert = df

        try:
            upsert_dataframe(table_name=table_name, df=df_to_upsert, conflict_columns=conflict_cols)
            print(f"Upserted data into {table_name}.")
        except Exception as exc:
            print(f"Error upserting to {table_name}: {exc}")

    upsert_table("eggy_songs_raw", collector.collect_songs, _normalize_songs, ["api_song_id"])
    upsert_table("eggy_shows_raw", collector.collect_shows, _normalize_shows, ["show_id"])
    upsert_table("eggy_venues_raw", collector.collect_venues, _normalize_venues, ["venue_id"])
    upsert_table(
        "eggy_setlists_raw",
        collector.collect_setlists,
        _normalize_setlists,
        ["show_id", "set_number", "song_position"],
        required_columns=["set_number", "song_position"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Eggy data into Supabase raw tables.")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Supabase schema validation before upserts.",
    )
    args = parser.parse_args()

    run_eggy_collection(skip_validation=args.skip_validation)


if __name__ == "__main__":
    main()
