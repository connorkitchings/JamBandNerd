"""Runs the Phish data collection pipeline.

This script fetches data from the phish.net API via the `PhishCollector`,
normalizes responses to the raw table schemas, and performs upserts into
`phish_songs_raw`, `phish_shows_raw`, `phish_venues_raw`, and `phish_setlists_raw`.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List

import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import ensure_source_reachable
from src.jambandnerd.data_collection.phish.collector import PhishCollector
from src.jambandnerd.data_collection.phish.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)
from src.jambandnerd.data_collection.utils import CollectionTimer
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import (
    fetch_existing_values,
    upsert_dataframe,
    validate_and_upsert_dataframe,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _clear_table(table_name: str) -> None:
    """Delete all rows from a table (requires a filter per PostgREST)."""
    client = get_supabase_client()
    # Delete all rows by using a condition that is true for every row
    # Use non-nullable text column `source_hash` to avoid type casting issues
    client.table(table_name).delete().neq("source_hash", "").execute()


def run_phish_collection(
    skip_validation: bool = False,
    year_start: int | None = None,
    year_end: int | None = None,
    full_backfill: bool = False,
    only_setlists: bool = False,
    clear_setlists: bool = False,
) -> None:
    """Run the Phish data collection workflow."""
    timer = CollectionTimer()
    logging.info("Starting Phish data collection...")
    ensure_source_reachable("phish")
    collector = PhishCollector()
    get_supabase_client()

    # Set default year range if not doing a full backfill
    if not full_backfill and year_start is None and year_end is None:
        current_year = datetime.now().year
        year_start = current_year - 1
        year_end = current_year
        logging.info(
            f"Defaulting to setlist collection for years: {year_start}-{year_end}"
        )

    def upsert_table(
        table_name: str,
        collector_func,
        normalizer_func,
        conflict_cols: List[str],
        required_columns: List[str] | None = None,
    ):
        logging.info(f"Collecting {table_name}...")
        raw_data = collector_func()
        df = normalizer_func(raw_data)
        logging.info(f"Prepared {len(df)} records for {table_name}.")
        if df.empty:
            logging.info(f"No data for {table_name}; skipping upsert.")
            return

        if (
            required_columns
            and "song_position" in required_columns
            and "position" in df.columns
            and "song_position" not in df.columns
        ):
            df.rename(columns={"position": "song_position"}, inplace=True)

        # Final guard to ensure created_at exists
        if "created_at" not in df.columns:
            df["created_at"] = datetime.now(timezone.utc).isoformat()

        try:
            validate_and_upsert_dataframe(
                table_name=table_name,
                df=df,
                conflict_columns=conflict_cols,
                required_columns=required_columns,
                skip_validation=skip_validation,
            )
            logging.info(f"Upserted data into {table_name}.")
        except Exception as e:
            logging.error(f"Error upserting to {table_name}: {e}")
            return

    if clear_setlists:
        logging.info("Clearing phish_setlists_raw table...")
        _clear_table("phish_setlists_raw")
        logging.info("phish_setlists_raw cleared.")

    if not only_setlists:
        # Collect and upsert songs, shows, venues
        upsert_table(
            "phish_songs_raw",
            collector.collect_songs,
            normalize_songs,
            ["api_song_id"],
        )

    # Shows provide data for venues and drive setlist selection
    shows_data = collector.collect_shows()
    shows_df = normalize_shows(shows_data)

    # Optional year-based filtering for setlists
    filtered_shows_df = shows_df.copy()
    if year_start is not None or year_end is not None:
        ys = year_start if year_start is not None else -(10**9)
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
        upsert_dataframe("phish_shows_raw", shows_df, conflict_columns=["show_id"])
        logging.info(f"Upserted {len(shows_df)} shows into phish_shows_raw.")
        if not only_setlists:
            venues_df = normalize_venues(shows_data)
            if not venues_df.empty:
                upsert_dataframe(
                    "phish_venues_raw", venues_df, conflict_columns=["api_venue_id"]
                )
                logging.info(f"Upserted {len(venues_df)} venues into phish_venues_raw.")

    # Collect setlists for the (optionally filtered) shows
    show_ids = filtered_shows_df["show_id"].dropna().astype(str).tolist()

    # Incremental: skip shows that already have setlists in the DB
    if show_ids and not clear_setlists:
        try:
            existing_ids = fetch_existing_values(
                "phish_setlists_raw",
                value_column="show_id",
                candidate_values=show_ids,
            )
            before = len(show_ids)
            show_ids = [sid for sid in show_ids if sid not in existing_ids]
            if existing_ids:
                logging.info(
                    f"Skipping {len(existing_ids)} shows with existing setlists "
                    f"({len(show_ids)}/{before} remaining for collection)."
                )
        except Exception as exc:
            logging.warning(f"Could not check existing setlists; fetching all ({exc}).")

    if show_ids:
        upsert_table(
            "phish_setlists_raw",
            lambda: collector.collect_setlists(show_ids=show_ids),
            normalize_setlists,
            ["api_unique_id"],
            required_columns=["set_number", "position"],
        )
    else:
        logging.info("No new setlists to collect.")

    # Log collection run
    try:
        timer.log("phish")
        logging.info("Logged collection run.")
    except Exception as exc:
        logging.warning(f"Could not log collection run ({exc}).")

    logging.info("Phish data collection finished.")


def main() -> None:
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


if __name__ == "__main__":
    main()
