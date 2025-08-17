"""
Phish data collection pipeline using the new BaseDataCollector architecture.
"""

import argparse
import sys

from .data_collector import PhishDataCollector


def main(update: bool = True, force_scrape_all: bool = False) -> bool:
    """
    Main entry point for the Phish data collection pipeline.
    Uses the new PhishDataCollector class for consistent architecture.
    Returns True if successful, False if any error occurs.
    """
    try:
        collector = PhishDataCollector(
            update_mode=update,
            force_scrape_all=force_scrape_all
        )
        return collector.run_pipeline()
    except Exception as e:
        print(f"Error in Phish data collection pipeline: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Phish data collection pipeline."
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
