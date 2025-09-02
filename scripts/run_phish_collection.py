"""Runs the Phish data collection pipeline.

This script fetches data from the phish.net API via the `PhishCollector`,
normalizes responses to the raw table schemas, and performs upserts into
`phish_songs_raw`, `phish_shows_raw`, `phish_venues_raw`, and `phish_setlists_raw`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.phish.collector import PhishCollector
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import get_table_schema, upsert_dataframe
from src.jambandnerd.db.validation import (
    coerce_df_types,
    validate_dataframe_against_table,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _compute_source_hash(record: Dict[str, Any]) -> str:
    """Compute a deterministic hash of a JSON-serializable record."""
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
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
            "source_hash": _compute_source_hash(item),
            "created_at": now,  # Added this line
        }
        for item in raw
        if item.get("songid")
    ]
    df = pd.DataFrame(normalized)
    df.drop_duplicates(subset=["api_song_id"], keep="first", inplace=True)
    return df


def _normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows to `phish_shows_raw` schema."""
    normalized = [
        {
            "api_show_id": item.get("showid"),
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
            "source_hash": _compute_source_hash(item),
        }
        for item in raw
        if item.get("showid")
    ]
    df = pd.DataFrame(normalized)
    if not df.empty:
        df["api_artist_id"] = pd.to_numeric(
            df["api_artist_id"], errors="coerce"
        ).astype("Int64")
        df["api_tour_id"] = pd.to_numeric(
            df["api_tour_id"], errors="coerce"
        ).astype("Int64")
    return df


def _normalize_venues(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize venues to `phish_venues_raw` schema."""
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
                "source_hash": _compute_source_hash(item),
            }
    df = pd.DataFrame(list(venues.values()))
    df.drop_duplicates(subset=["api_venue_id"], keep="first", inplace=True)
    return df


def _normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `phish_setlists_raw` schema."""
    def _to_bool(value: Any) -> bool:
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
        # Numeric strings like "0", "1", "2" → True if > 0
        if s.isdigit():
            try:
                return int(s) > 0
            except Exception:
                return False
        return bool(s)

    now = datetime.now(timezone.utc).isoformat()
    normalized_rows: List[Dict[str, Any]] = []
    for item in raw:
        if not item.get("uniqueid"):
            continue
        row = {
            "api_unique_id": item.get("uniqueid"),
            "api_show_id": item.get("showid"),
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
            "source_hash": _compute_source_hash(item),
            "created_at": now, # Added this line
        }
        normalized_rows.append(row)

    df = pd.DataFrame(normalized_rows)
    if not df.empty:
        # Enforce numeric types where appropriate
        for col in ["set_number", "position", "gap", "track_time"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        # Deduplicate based on unique setlist entry
        initial_rows = len(df)
        df.drop_duplicates(subset=["api_unique_id"], keep="first", inplace=True)
        if len(df) < initial_rows:
            logging.info(f"Dropped {initial_rows - len(df)} duplicate setlist entries.")
    return df


def _clear_table(table_name: str) -> None:
    """Delete all rows from a table (requires a filter per PostgREST)."""
    client = get_supabase_client()
    # Delete all rows by using a condition that is true for every row
    # Use non-nullable text column `source_hash` to avoid type casting issues
    client.table(table_name).delete().neq("source_hash", "").execute()


def run_phish_collection(
    skip_validation: bool = False,
    clear_setlists: bool = False,
    only_setlists: bool = False,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    full_backfill: bool = False,
) -> None:
    """Collect all Phish data and store it in Supabase raw tables."""
    logging.info("Starting Phish data collection...")
    collector = PhishCollector()
    get_supabase_client()

    # Set default year range if not doing a full backfill
    if not full_backfill and year_start is None and year_end is None:
        current_year = datetime.now().year
        year_start = current_year - 1
        year_end = current_year
        logging.info(f"Defaulting to setlist collection for years: {year_start}-{year_end}")

    def upsert_table(
        table_name: str, collector_func, normalizer_func, conflict_cols: List[str]
    ):
        logging.info(f"Collecting {table_name}...")
        raw_data = collector_func()
        df = normalizer_func(raw_data)
        logging.info(f"Prepared {len(df)} records for {table_name}.")
        if df.empty:
            logging.info(f"No data for {table_name}; skipping upsert.")
            return

        schema = get_table_schema(table_name)
        if schema and not skip_validation:
            df = coerce_df_types(df, schema)
            report = validate_dataframe_against_table(df, table_name, schema)
            if not report.is_valid:
                logging.warning(f"Validation failed for {table_name}: {report}")

        try:
            upsert_dataframe(
                table_name=table_name, df=df, conflict_columns=conflict_cols
            )
            logging.info(f"Upserted data into {table_name}.")
        except Exception as e:
            logging.error(f"Error upserting to {table_name}: {e}")

    if clear_setlists:
        logging.info("Clearing phish_setlists_raw table...")
        _clear_table("phish_setlists_raw")
        logging.info("phish_setlists_raw cleared.")

    if not only_setlists:
        # Collect and upsert songs, shows, venues
        upsert_table(
            "phish_songs_raw", collector.collect_songs, _normalize_songs, ["api_song_id"]
        )

    # Shows provide data for venues and drive setlist selection
    shows_data = collector.collect_shows()
    shows_df = _normalize_shows(shows_data)

    # Optional year-based filtering for setlists
    filtered_shows_df = shows_df.copy()
    if year_start is not None or year_end is not None:
        ys = year_start if year_start is not None else -10**9
        ye = year_end if year_end is not None else 10**9
        if not filtered_shows_df.empty and "show_year" in filtered_shows_df.columns:
            filtered_shows_df["show_year"] = pd.to_numeric(
                filtered_shows_df["show_year"], errors="coerce"
            ).astype("Int64")
            before = len(filtered_shows_df)
            filtered_shows_df = filtered_shows_df[
                (filtered_shows_df["show_year"].astype("Int64") >= ys)
                & (filtered_shows_df["show_year"].astype("Int64") <= ye)
            ]
            logging.info(
                f"Filtered shows by year [{ys}, {ye}]: {len(filtered_shows_df)}/{before} remaining"
            )

    if not only_setlists and not shows_df.empty:
        upsert_dataframe(
            "phish_shows_raw", shows_df, conflict_columns=["api_show_id"]
        )
        logging.info(f"Upserted {len(shows_df)} shows into phish_shows_raw.")
        if not only_setlists:
            venues_df = _normalize_venues(shows_data)
            if not venues_df.empty:
                upsert_dataframe(
                    "phish_venues_raw", venues_df, conflict_columns=["api_venue_id"]
                )
                logging.info(f"Upserted {len(venues_df)} venues into phish_venues_raw.")

    # Collect setlists for the (optionally filtered) shows
    show_ids = filtered_shows_df["api_show_id"].dropna().astype(str).tolist()
    upsert_table(
        "phish_setlists_raw",
        lambda: collector.collect_setlists(show_ids=show_ids),
        _normalize_setlists,
        ["api_unique_id"],
    )

    # Log collection run
    try:
        client = get_supabase_client()
        client.table("collection_runs").insert({"band": "phish"}).execute()
        logging.info("Logged collection run.")
    except Exception as exc:
        logging.warning(f"Could not log collection run ({exc}).")

    logging.info("Phish data collection finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Phish data collection with optional schema validation"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Bypass schema validation before upserts",
    )
    parser.add_argument(
        "--clear-setlists",
        action="store_true",
        help="Clear all rows in phish_setlists_raw before collection",
    )
    parser.add_argument(
        "--only-setlists",
        action="store_true",
        help="Only collect setlists; skip songs/shows/venues upserts",
    )
    parser.add_argument("--year-start", type=int, help="Start year for setlists filter")
    parser.add_argument("--year-end", type=int, help="End year for setlists filter")
    parser.add_argument(
        "--full-backfill",
        action="store_true",
        help="Perform a full backfill of all setlists, ignoring year filters.",
    )
    args = parser.parse_args()
    run_phish_collection(
        skip_validation=args.skip_validation,
        clear_setlists=args.clear_setlists,
        only_setlists=args.only_setlists,
        year_start=args.year_start,
        year_end=args.year_end,
        full_backfill=args.full_backfill,
    )
