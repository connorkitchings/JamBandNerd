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
from datetime import datetime
from typing import Any, Dict, Iterable, List

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
        }
        for item in raw
        if item.get("songid")
    ]
    return pd.DataFrame(normalized)


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
    return pd.DataFrame(list(venues.values()))


def _normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlists to `phish_setlists_raw` schema."""
    normalized = [
        {
            "api_unique_id": item.get("uniqueid"),
            "api_show_id": item.get("showid"),
            "show_date": item.get("showdate"),
            "permalink": item.get("permalink"),
            "api_song_id": item.get("songid"),
            "song_name": item.get("song"),
            "set_number": item.get("set"),
            "position": item.get("position"),
            "transition": item.get("trans_mark"),
            "is_reprise": item.get("isreprise"),
            "is_jam": item.get("isjam"),
            "is_jam_chart": item.get("isjamchart"),
            "track_time": item.get("tracktime"),
            "gap": item.get("gap"),
            "is_original": item.get("is_original"),
            "footnote": item.get("footnote"),
            "source_hash": _compute_source_hash(item),
        }
        for item in raw
        if item.get("uniqueid")
    ]
    return pd.DataFrame(normalized)


def run_phish_collection(skip_validation: bool = False) -> None:
    """Collect all Phish data and store it in Supabase raw tables."""
    logging.info("Starting Phish data collection...")
    collector = PhishCollector()
    get_supabase_client()

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
                logging.error(f"Validation failed for {table_name}: {report}")
                return

        try:
            upsert_dataframe(
                table_name=table_name, df=df, conflict_columns=conflict_cols
            )
            logging.info(f"Upserted data into {table_name}.")
        except Exception as e:
            logging.error(f"Error upserting to {table_name}: {e}")

    # Collect and upsert all data types
    upsert_table(
        "phish_songs_raw", collector.collect_songs, _normalize_songs, ["api_song_id"]
    )
    # Shows provides data for venues, so collect it once
    shows_data = collector.collect_shows()
    shows_df = _normalize_shows(shows_data)
    if not shows_df.empty:
        upsert_dataframe(
            "phish_shows_raw", shows_df, conflict_columns=["api_show_id"]
        )
        logging.info(f"Upserted {len(shows_df)} shows into phish_shows_raw.")
        # Now handle venues from the same data
        venues_df = _normalize_venues(shows_data)
        if not venues_df.empty:
            upsert_dataframe(
                "phish_venues_raw", venues_df, conflict_columns=["api_venue_id"]
            )
            logging.info(f"Upserted {len(venues_df)} venues into phish_venues_raw.")

        # Now, collect setlists for the shows we just processed
        show_ids = shows_df["api_show_id"].dropna().astype(str).tolist()
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
    args = parser.parse_args()
    run_phish_collection(skip_validation=args.skip_validation)
