#!/usr/bin/env python3
"""Run a correction sweep for a specific band.

This script is the entry point for the weekly correction sweep workflow.
It detects and optionally applies corrections to existing data records.

Usage:
    # Dry run (detect only, don't apply)
    uv run python scripts/run_correction_sweep.py --band goose --dry-run

    # Apply corrections
    uv run python scripts/run_correction_sweep.py --band goose --no-dry-run

    # Custom window
    uv run python scripts/run_correction_sweep.py --band goose --window-days 365
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root on path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.correction_detector import (
    format_correction_report,
    run_correction_sweep,
)
from src.jambandnerd.db.connection import get_supabase_client


def main():
    parser = argparse.ArgumentParser(
        description="Run a correction sweep to detect and fix data discrepancies."
    )
    parser.add_argument(
        "--band",
        required=True,
        choices=["goose", "phish", "eggy", "billy", "wsp", "um"],
        help="Band to run correction sweep for",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=730,
        help="Number of days to look back for corrections (default: 730)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Detect corrections but don't apply them (default: True)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually apply detected corrections",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="correction_sweep_report.json",
        help="Output file for the correction report",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["setlists"],
        choices=["shows", "setlists", "songs", "venues"],
        help="Tables to check for corrections",
    )

    args = parser.parse_args()

    # Determine if this is a dry run
    dry_run = args.dry_run and not args.no_dry_run

    print(f"Starting correction sweep for {args.band}")
    print(f"  Window: {args.window_days} days")
    print(f"  Tables: {', '.join(args.tables)}")
    print(
        f"  Mode: {'DRY RUN (detect only)' if dry_run else 'LIVE (apply corrections)'}"
    )
    print()

    # Initialize Supabase client
    client = get_supabase_client()

    # Run the correction sweep
    results = run_correction_sweep(
        band=args.band,
        window_days=args.window_days,
        dry_run=dry_run,
        tables=args.tables,
        client=client,
    )

    # Generate and print report
    report = format_correction_report(results)
    print(report)

    # Save detailed results to JSON
    output_data = {
        "band": args.band,
        "timestamp": datetime.now().isoformat(),
        "window_days": args.window_days,
        "dry_run": dry_run,
        "tables": args.tables,
        "results": {name: result.to_dict() for name, result in results.items()},
    }

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDetailed report saved to: {output_path}")

    # Exit with error code if there were errors
    total_errors = sum(len(r.errors) for r in results.values())
    if total_errors > 0:
        print(f"\n⚠️  Completed with {total_errors} errors")
        sys.exit(1)

    total_corrections = sum(r.corrections_found for r in results.values())
    if total_corrections > 0:
        print(f"\n✓ Found {total_corrections} corrections")
        if not dry_run:
            applied = sum(r.corrections_applied for r in results.values())
            print(f"✓ Applied {applied} corrections")
    else:
        print("\n✓ No corrections needed")

    sys.exit(0)


if __name__ == "__main__":
    main()
