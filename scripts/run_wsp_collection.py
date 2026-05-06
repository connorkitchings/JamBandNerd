"""Runs the Widespread Panic data collection pipeline.

This script fetches data from everydaycompanion.com via the `WSPCollector`,
normalizes the responses to the raw table schemas, and performs upserts into
the `wsp_songs_raw`, `wsp_shows_raw`, and `wsp_setlists_raw` tables.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.config.bands import get_collection_policy
from src.jambandnerd.data_collection.wsp.orchestration import process_wsp_data
from src.jambandnerd.data_collection.wsp.status import CollectionStatus

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_wsp_collection(
    skip_existing_setlists: bool = True,
    year_start: int | None = None,
    year_end: int | None = None,
    full_backfill: bool = False,
) -> CollectionStatus:
    """Runs the Widespread Panic data collection pipeline."""
    start_date = None
    end_date = None

    if not full_backfill and year_start is None and year_end is None:
        # Use rolling_window_days from collection policy (default: 90 days)
        policy = get_collection_policy("wsp")
        window_days = policy.rolling_window_days or 730

        today = date.today()
        start_date = today - timedelta(days=window_days)
        end_date = today + timedelta(days=90)  # Include upcoming shows

        logging.info(
            f"Defaulting to show collection window: {start_date.isoformat()} to {end_date.isoformat()} "
            f"({window_days} days historical + 90 days upcoming)"
        )

    try:
        status = process_wsp_data(
            skip_existing_setlists=skip_existing_setlists,
            year_start=year_start,
            year_end=year_end,
            start_date=start_date,
            end_date=end_date,
            full_backfill=full_backfill,
        )
        _write_github_outputs(status)
        if status.workflow_state() == "degraded":
            logging.warning("⚠️ WSP collection completed in degraded mode")
        else:
            logging.info("✅ WSP collection completed successfully")
        return status
    except RuntimeError as e:
        logging.error(f"\u274c WSP collection failed: {e}")
        _write_failure_github_outputs(str(e))
        raise
    except Exception as e:
        logging.error(f"\u274c Unexpected error during WSP collection: {e}")
        logging.exception("Full traceback:")
        _write_failure_github_outputs(str(e))
        raise RuntimeError(str(e)) from e


from scripts.common import write_github_output


def _write_github_outputs(status: CollectionStatus) -> None:
    """Write structured outputs for GitHub Actions consumers when available."""
    for key, value in status.as_github_outputs().items():
        write_github_output(key, value)


def _write_failure_github_outputs(reason: str) -> None:
    """Write explicit failure outputs when the runner exits non-zero."""
    write_github_output("workflow_state", "failed")
    write_github_output("outcome_code", "failed_internal")
    write_github_output("should_retry_collection", "true")
    write_github_output("recent_data_usable", "false")
    write_github_output("prediction_action", "skipped")
    write_github_output("failure_reason", reason)


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
    # uv run python scripts/run_wsp_collection.py                    # Default: 90-day rolling window + upcoming
    # uv run python scripts/run_wsp_collection.py --year_start 2023 --year_end 2023  # Specific year
    # uv run python scripts/run_wsp_collection.py --full_backfill   # All historical data
    try:
        run_wsp_collection(
            skip_existing_setlists=args.skip_existing_setlists,
            year_start=args.year_start,
            year_end=args.year_end,
            full_backfill=args.full_backfill,
        )
    except RuntimeError:
        sys.exit(1)
