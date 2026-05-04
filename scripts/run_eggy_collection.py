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
from src.jambandnerd.db.operations import fetch_last_collection_timestamp  # noqa: E402


def run_eggy_collection(
    skip_validation: bool = False,
    incremental: bool = True,
    full_refresh: bool = False,
) -> None:
    """Collect all Eggy data and store it in Supabase raw tables.

    Args:
        skip_validation: Bypass schema validation before upserts.
        incremental: Use timestamp-based incremental collection (default: True).
        full_refresh: Force full refresh even if incremental is enabled.
    """
    timer = CollectionTimer()
    print("Starting Eggy data collection...")
    ensure_source_reachable("eggy")
    collector = EggyCollector()
    client = get_supabase_client()

    # Determine collection mode
    use_incremental = incremental and not full_refresh
    since_timestamp = None

    if use_incremental:
        since_timestamp = fetch_last_collection_timestamp("eggy", client=client)
        if since_timestamp:
            print(f"Using incremental mode (since: {since_timestamp.isoformat()})")
        else:
            print("No previous collection found, falling back to full refresh")
            use_incremental = False

    if use_incremental and since_timestamp:
        # Incremental collection mode
        # Collect only records updated since last successful collection

        def collect_songs_incremental():
            return collector.collect_songs_incremental(since_timestamp)

        def collect_shows_incremental():
            return collector.collect_shows_incremental(since_timestamp)

        def collect_setlists_incremental():
            return collector.collect_setlists_incremental(since_timestamp)

        # Songs (incremental)
        upsert_table(
            "eggy_songs_raw",
            collect_songs_incremental,
            normalize_songs,
            ["api_song_id"],
            skip_validation=skip_validation,
        )

        # Shows (incremental)
        upsert_table(
            "eggy_shows_raw",
            collect_shows_incremental,
            normalize_shows,
            ["show_id"],
            skip_validation=skip_validation,
        )

        # Venues (always full - small dataset, no timestamp field)
        upsert_table(
            "eggy_venues_raw",
            collector.collect_venues,
            normalize_venues,
            ["venue_id"],
            skip_validation=skip_validation,
        )

        # Setlists (incremental)
        upsert_table(
            "eggy_setlists_raw",
            collect_setlists_incremental,
            normalize_setlists,
            ["show_id", "set_number", "song_position"],
            required_columns=["set_number", "song_position"],
            skip_validation=skip_validation,
        )
    else:
        # Full refresh mode (original behavior)
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
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Disable incremental collection (force full refresh).",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Force a full refresh of all data (same as --no-incremental).",
    )
    args = parser.parse_args()

    run_eggy_collection(
        skip_validation=args.skip_validation,
        incremental=not args.no_incremental,
        full_refresh=args.full_refresh,
    )


if __name__ == "__main__":
    main()
