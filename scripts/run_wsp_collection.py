"""Runs the Widespread Panic data collection pipeline.

This script fetches data from everydaycompanion.com via the `WSPCollector`,
normalizes the responses to the raw table schemas, and performs upserts into
the `wsp_songs_raw`, `wsp_shows_raw`, and `wsp_setlists_raw` tables.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.wsp.orchestration import process_wsp_data
from src.jambandnerd.data_collection.wsp.status import CollectionStatus

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def default_wsp_year_window(*, today: datetime | None = None) -> tuple[int, int]:
    """Return the default (year_start, year_end) show collection window.

    Spans the prior year through next year so newly-published future tours are
    picked up immediately (no Jan-1 blind spot). The collector treats an
    unpublished tour page (404) as a soft skip, so scanning next year is safe
    even before everydaycompanion.com has posted it.
    """
    current_year = (today or datetime.now()).year
    return current_year - 1, current_year + 1


def run_wsp_collection(
    skip_existing_setlists: bool = True,
    year_start: int | None = None,
    year_end: int | None = None,
    full_backfill: bool = False,
) -> CollectionStatus:
    """Runs the Widespread Panic data collection pipeline."""
    if not full_backfill and year_start is None and year_end is None:
        year_start, year_end = default_wsp_year_window()
        logging.info(
            f"Defaulting to show collection for years: {year_start}-{year_end}"
        )

    try:
        status = process_wsp_data(
            skip_existing_setlists=skip_existing_setlists,
            year_start=year_start,
            year_end=year_end,
            full_backfill=full_backfill,
        )
        _write_github_outputs(status)
        if status.workflow_state() == "degraded":
            logging.warning("⚠️ WSP collection completed in degraded mode")
        else:
            logging.info("✅ WSP collection completed successfully")
        return status
    except RuntimeError as e:
        logging.error(f"❌ WSP collection failed: {e}")
        _write_failure_github_outputs(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Unexpected error during WSP collection: {e}")
        logging.exception("Full traceback:")
        _write_failure_github_outputs(str(e))
        sys.exit(1)


def _write_github_outputs(status: CollectionStatus) -> None:
    """Write structured outputs for GitHub Actions consumers when available."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return

    with open(github_output, "a", encoding="utf-8") as handle:
        for key, value in status.as_github_outputs().items():
            handle.write(f"{key}={value}\n")


def _write_failure_github_outputs(reason: str) -> None:
    """Write explicit failure outputs when the runner exits non-zero."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return

    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write("workflow_state=failed\n")
        handle.write("outcome_code=failed_internal\n")
        handle.write("should_retry_collection=true\n")
        handle.write("recent_data_usable=false\n")
        handle.write("prediction_action=skipped\n")
        handle.write(f"failure_reason={reason}\n")


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
