"""Run the Eggy data collection pipeline (raw tables).

This script fetches data from thecarton.net API via the `EggyCollector`,
normalizes responses to the Supabase raw schemas, and performs upserts into
`eggy_songs_raw`, `eggy_shows_raw`, `eggy_setlists_raw`, and `eggy_venues_raw`.
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure project root on path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import ensure_source_reachable, upsert_table  # noqa: E402
from src.jambandnerd.data_collection.browser import CloudflareBypass  # noqa: E402
from src.jambandnerd.data_collection.eggy.collector import EggyCollector  # noqa: E402
from src.jambandnerd.data_collection.eggy.normalizer import (  # noqa: E402
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)
from src.jambandnerd.data_collection.utils import CollectionTimer  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402


def run_eggy_collection(skip_validation: bool = False) -> None:
    """Collect all Eggy data and store it in Supabase raw tables."""
    timer = CollectionTimer()
    print("Starting Eggy data collection...")
    ensure_source_reachable("eggy")
    collector = EggyCollector()
    get_supabase_client()

    upsert_table(
        "eggy_songs_raw",
        collector.collect_songs,
        normalize_songs,
        ["api_song_id"],
        skip_validation=skip_validation,
    )
    upsert_table(
        "eggy_shows_raw",
        collector.collect_shows,
        normalize_shows,
        ["show_id"],
        skip_validation=skip_validation,
    )
    upsert_table(
        "eggy_venues_raw",
        collector.collect_venues,
        normalize_venues,
        ["venue_id"],
        skip_validation=skip_validation,
    )
    upsert_table(
        "eggy_setlists_raw",
        collector.collect_setlists,
        normalize_setlists,
        ["show_id", "set_number", "song_position"],
        required_columns=["set_number", "song_position"],
        skip_validation=skip_validation,
    )

    CloudflareBypass.cleanup()
    timer.log("eggy")
    print("Eggy collection complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Eggy data into Supabase raw tables."
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Supabase schema validation before upserts.",
    )
    args = parser.parse_args()

    run_eggy_collection(skip_validation=args.skip_validation)


if __name__ == "__main__":
    main()
