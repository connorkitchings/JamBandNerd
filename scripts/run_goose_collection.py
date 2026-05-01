"""Runs the Goose data collection pipeline (Goose-first, raw tables).

This script fetches data from the elgoose.net API via the `GooseCollector`,
normalizes responses to the raw table schemas, and performs upserts into
`goose_songs_raw`, `goose_shows_raw`, and `goose_setlists_raw`.
"""

from __future__ import annotations

import argparse
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import ensure_source_reachable, upsert_table  # noqa: E402
from src.jambandnerd.data_collection.goose.collector import GooseCollector  # noqa: E402
from src.jambandnerd.data_collection.goose.normalizer import (  # noqa: E402
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)
from src.jambandnerd.data_collection.utils import CollectionTimer  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402


def run_goose_collection(skip_validation: bool = False) -> None:
    """Collect all Goose data and store it in Supabase raw tables."""
    timer = CollectionTimer()
    print("Starting Goose data collection...")
    ensure_source_reachable("goose")
    collector = GooseCollector()
    get_supabase_client()

    upsert_table(
        "goose_songs_raw",
        collector.collect_songs,
        normalize_songs,
        ["api_song_id"],
        skip_validation=skip_validation,
    )
    upsert_table(
        "goose_shows_raw",
        collector.collect_shows,
        normalize_shows,
        ["show_id"],
        skip_validation=skip_validation,
    )
    upsert_table(
        "goose_venues_raw",
        collector.collect_venues,
        normalize_venues,
        ["venue_id"],
        skip_validation=skip_validation,
    )
    upsert_table(
        "goose_setlists_raw",
        collector.collect_setlists,
        normalize_setlists,
        ["show_id", "set_number", "song_position"],
        required_columns=["set_number", "song_position"],
        skip_validation=skip_validation,
    )

    # Log collection run
    timer.log("goose")

    print("Goose data collection finished.")


def main() -> None:
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


if __name__ == "__main__":
    main()
