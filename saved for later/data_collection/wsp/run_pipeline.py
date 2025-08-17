#!/usr/bin/env python3
"""
Unified WSP data collection pipeline runner.

This script serves as the single entry point for WSP data collection,
utilizing the refactored WSPDataCollector with integrated caching,
transformation, and export logic.
"""

import argparse
import sys

from .data_collector import WSPDataCollector


def main(update: bool = True, force_scrape_all: bool = False) -> bool:
    """
    Main WSP pipeline orchestrator.

    Args:
        update (bool): If True, run in update mode (incremental scraping).
                      If False, run full scrape.
        force_scrape_all (bool): If True, forces scraping of all shows and songs.

    Returns:
        bool: True if pipeline succeeded, False otherwise.
    """
    try:
        collector = WSPDataCollector(
            update_mode=update,
            force_scrape_all=force_scrape_all
        )
        success = collector.run_pipeline()

        if not success:
            print("WSP pipeline failed", file=sys.stderr)
            return False

        print("WSP pipeline completed successfully")
        return True

    except Exception as e:
        print(f"WSP pipeline failed with error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the WSP data collection pipeline."
    )
    parser.add_argument(
        "--full-scrape",
        action="store_true",
        help="Run full scrape instead of update mode.",
    )
    parser.add_argument(
        "--force-scrape-all",
        action="store_true",
        help="Force scraping of all shows and songs, ignoring cache.",
    )

    args = parser.parse_args()

    success = main(
        update=not args.full_scrape,
        force_scrape_all=args.force_scrape_all
    )

    sys.exit(0 if success else 1)
