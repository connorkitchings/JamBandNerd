"""Run the Eggy data collection pipeline (raw tables).

This script fetches data from thecarton.net API via the `EggyCollector`,
normalizes responses to the Supabase raw schemas, and performs upserts into
`eggy_songs_raw`, `eggy_shows_raw`, `eggy_setlists_raw`, and `eggy_venues_raw`.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

# Ensure project root on path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import ensure_source_reachable  # noqa: E402
from src.jambandnerd.data_collection.browser import CloudflareBypass  # noqa: E402
from src.jambandnerd.data_collection.eggy.collector import EggyCollector  # noqa: E402
from src.jambandnerd.data_collection.eggy.normalizer import (  # noqa: E402
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.db.operations import validate_and_upsert_dataframe  # noqa: E402


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
        except Exception as exc:
            print(f"Error upserting to {table_name}: {exc}")

    upsert_table(
        "eggy_songs_raw", collector.collect_songs, normalize_songs, ["api_song_id"]
    )
    upsert_table(
        "eggy_shows_raw", collector.collect_shows, normalize_shows, ["show_id"]
    )
    upsert_table(
        "eggy_venues_raw", collector.collect_venues, normalize_venues, ["venue_id"]
    )
    upsert_table(
        "eggy_setlists_raw",
        collector.collect_setlists,
        normalize_setlists,
        ["show_id", "set_number", "song_position"],
        required_columns=["set_number", "song_position"],
    )

    CloudflareBypass.cleanup()


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
