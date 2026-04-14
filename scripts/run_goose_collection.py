"""Runs the Goose data collection pipeline (Goose-first, raw tables).

This script fetches data from the elgoose.net API via the `GooseCollector`,
normalizes responses to the raw table schemas, and performs upserts into
`goose_songs_raw`, `goose_shows_raw`, and `goose_setlists_raw`.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import ensure_source_reachable  # noqa: E402
from src.jambandnerd.data_collection.goose.collector import GooseCollector  # noqa: E402
from src.jambandnerd.data_collection.goose.normalizer import (  # noqa: E402
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.db.operations import validate_and_upsert_dataframe  # noqa: E402


def run_goose_collection(skip_validation: bool = False) -> None:
    """Collect all Goose data and store it in Supabase raw tables."""
    print("Starting Goose data collection...")
    ensure_source_reachable("goose")
    collector = GooseCollector()
    get_supabase_client()

    # Upsert logic for each table type
    def upsert_table(
        table_name: str,
        collector_func,
        normalizer_func,
        conflict_cols: List[str],
        required_columns: List[str] | None = None,
    ):
        print(f"Collecting {table_name}...")
        try:
            raw_data = collector_func()
        except Exception as e:
            print(f"Error collecting {table_name}: {e}")
            return
        df = normalizer_func(raw_data)
        print(f"Prepared {len(df)} records for {table_name}.")
        if df.empty:
            print(f"No data for {table_name}; skipping upsert.")
            return

        try:
            validate_and_upsert_dataframe(
                table_name=table_name,
                df=df,
                conflict_columns=conflict_cols,
                required_columns=required_columns,
                skip_validation=skip_validation,
            )
            print(f"Upserted data into {table_name}.")
        except Exception as e:
            print(f"Error upserting to {table_name}: {e}")

    upsert_table(
        "goose_songs_raw", collector.collect_songs, normalize_songs, ["api_song_id"]
    )
    upsert_table(
        "goose_shows_raw", collector.collect_shows, normalize_shows, ["show_id"]
    )
    upsert_table(
        "goose_venues_raw", collector.collect_venues, normalize_venues, ["venue_id"]
    )
    upsert_table(
        "goose_setlists_raw",
        collector.collect_setlists,
        normalize_setlists,
        ["show_id", "set_number", "song_position"],
        required_columns=["set_number", "song_position"],
    )

    # Log collection run
    try:
        client = get_supabase_client()
        client.table("collection_runs").insert({"band": "goose"}).execute()
        print("Logged collection run.")
    except Exception as exc:
        print(f"Warning: could not log collection run ({exc}).")

    print("Goose data collection finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Goose data collection with optional schema validation"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Bypass schema validation before upserts",
    )
    args = parser.parse_args()
    run_goose_collection(skip_validation=args.skip_validation)
