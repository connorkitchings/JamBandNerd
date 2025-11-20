"""Runs the Widespread Panic data collection pipeline.

This script fetches data from everydaycompanion.com via the `WSPCollector`,
normalizes the responses to the raw table schemas, and performs upserts into
the `wsp_songs_raw`, `wsp_shows_raw`, and `wsp_setlists_raw` tables.
"""

import logging
import os
import sys
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.wsp.orchestration import process_wsp_data

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_wsp_collection(
    skip_existing_setlists: bool = True,
    year_start: int | None = None,
    year_end: int | None = None,
    full_backfill: bool = False,
) -> None:
    """Runs the Widespread Panic data collection pipeline."""
    if not full_backfill and year_start is None and year_end is None:
        current_year = datetime.now().year
        year_start = current_year - 1
        year_end = current_year
        logging.info(
            f"Defaulting to show collection for years: {year_start}-{year_end}"
        )

    process_wsp_data(
        skip_existing_setlists=skip_existing_setlists,
        year_start=year_start,
        year_end=year_end,
        full_backfill=full_backfill,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Widespread Panic data collection pipeline."
    )
    parser.add_argument(
        "--skip_existing_setlists",
        action="store_true",
        help="Skip shows that already have setlists.",
    )
    parser.add_argument(
        "--year_start", type=int, help="The first year to collect shows for."
    )
    parser.add_argument(
        "--year_end", type=int, help="The last year to collect shows for."
    )
    parser.add_argument(
        "--full_backfill",
        action="store_true",
        help="Perform a full backfill of all historical data, ignoring year filters.",
    )

    args = parser.parse_args()

    # Example of runs:
    # uv run python scripts/run_wsp_collection.py                    # Default: last year + this year
    # uv run python scripts/run_wsp_collection.py --year_start 2023 --year_end 2023  # Specific year
    # uv run python scripts/run_wsp_collection.py --full_backfill   # All historical data
    run_wsp_collection(
        skip_existing_setlists=args.skip_existing_setlists,
        year_start=args.year_start,
        year_end=args.year_end,
        full_backfill=args.full_backfill,
    )
