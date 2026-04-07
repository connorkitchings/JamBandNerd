#!/usr/bin/env python3
"""Play Fantasy Goose automatically using Goose notebook predictions."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.integrations.fantasy_goose import (  # noqa: E402
    append_github_output,
    format_console_summary,
    run_fantasy_goose_sync,
)


def main() -> None:
    """Run the Fantasy Goose automation flow."""
    parser = argparse.ArgumentParser(
        description="Submit Goose notebook picks to Fantasy Goose."
    )
    parser.add_argument(
        "--date",
        help="Target show date in YYYY-MM-DD format. Defaults to today in ET.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the show and picks but do not submit the entry.",
    )
    args = parser.parse_args()

    load_dotenv()
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
    result = run_fantasy_goose_sync(target_date=target_date, dry_run=args.dry_run)
    append_github_output(result)

    summary = format_console_summary(result)
    print(summary)

    github_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if github_summary:
        with open(github_summary, "a", encoding="utf-8") as handle:
            handle.write("## Fantasy Goose\n\n")
            handle.write("```\n")
            handle.write(summary)
            handle.write("\n```\n")


if __name__ == "__main__":
    main()
