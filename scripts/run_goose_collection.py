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


def _get_db_show_count(client) -> int:
    """Get the current show count from the database."""
    try:
        response = (
            client.table("goose_shows_raw")
            .select("*", count="exact")
            .limit(0)
            .execute()
        )
        return response.count or 0
    except Exception as exc:
        print(f"Warning: Could not fetch DB show count ({exc})")
        return -1


def run_goose_collection(
    skip_validation: bool = False,
    skip_if_unchanged: bool = True,
    force: bool = False,
) -> None:
    """Collect all Goose data and store it in Supabase raw tables.

    Args:
        skip_validation: Bypass schema validation before upserts.
        skip_if_unchanged: Skip collection if upstream show count matches DB.
        force: Force collection even if counts match.
    """
    timer = CollectionTimer()
    print("Starting Goose data collection...")
    ensure_source_reachable("goose")
    collector = GooseCollector()
    client = get_supabase_client()

    # Check if we can skip collection based on show count
    if skip_if_unchanged and not force:
        print("Checking for new shows...")
        db_count = _get_db_show_count(client)

        if db_count >= 0:
            # Peek at upstream show count without full fetch
            upstream_shows = collector.collect_shows()
            upstream_count = len(upstream_shows)

            if upstream_count == db_count:
                print(
                    f"✓ Goose show count unchanged ({db_count} shows). Skipping collection."
                )
                timer.log("goose")
                return
            else:
                print(
                    f"✗ Show count changed: DB={db_count}, Upstream={upstream_count}. Running collection..."
                )
        else:
            print("Could not determine DB show count. Proceeding with collection...")
    elif force:
        print("Force flag set. Proceeding with collection...")

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
    parser.add_argument(
        "--no-skip-unchanged",
        action="store_true",
        help="Disable show count comparison (always run collection).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force collection even if show counts match.",
    )
    args = parser.parse_args()
    run_goose_collection(
        skip_validation=args.skip_validation,
        skip_if_unchanged=not args.no_skip_unchanged,
        force=args.force,
    )


if __name__ == "__main__":
    main()
