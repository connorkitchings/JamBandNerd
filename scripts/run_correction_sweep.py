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

from scripts.generate_live_predictions import generate_live_predictions
from scripts.sync_retained_prediction_corpus import sync_retained_prediction_corpus
from scripts.validate_accuracy_tables import validate_accuracy
from scripts.validate_prediction_tables import _has_upcoming_show, validate_predictions
from src.jambandnerd.data_collection.correction_detector import (  # noqa: E402
    format_correction_report,
    run_correction_sweep,
)
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.models.registry import list_active_bands


def refresh_corrected_band(*, band: str, client, applied: int, dry_run: bool) -> dict:
    """Rebuild derived data after raw writes, retaining explicit recovery state."""
    outcome = {
        "status": "skipped",
        "corrections_applied": applied,
        "cache_invalidation_required": False,
        "stages": dict.fromkeys(
            (
                "retained_corpus",
                "live_predictions",
                "prediction_validation",
                "accuracy_validation",
            ),
            "not_run",
        ),
    }
    if dry_run:
        outcome["reason"] = "dry_run"
    elif not applied:
        outcome["reason"] = "no_corrections_applied"
    elif band not in list_active_bands():
        outcome["reason"] = "inactive_model"
    if "reason" in outcome:
        return outcome

    outcome["recovery_commands"] = [
        f"uv run python scripts/sync_retained_prediction_corpus.py --band {band} --window 50 --no-incremental --require-results",
        f"uv run python scripts/generate_live_predictions.py --band {band}",
        f"uv run python scripts/validate_prediction_tables.py --band {band}",
        f"uv run python scripts/validate_accuracy_tables.py --band {band} --replay-window 50 --require-exact-retained-window",
    ]
    stages = outcome["stages"]
    stage = "retained_corpus"
    try:
        stages[stage] = "running"
        rows = sync_retained_prediction_corpus(
            band=band, window=50, incremental=False, require_results=True
        )
        if rows <= 0:
            raise RuntimeError("Retained corpus refresh wrote no results")
        stages[stage] = "success"
        outcome["retained_rows_refreshed"] = rows

        stage = "live_predictions"
        stages[stage] = "running"
        if _has_upcoming_show(client, band=band):
            if not generate_live_predictions(band=band, require_output=True):
                raise RuntimeError("Live prediction generation did not complete")
            stages[stage] = "success"
        else:
            stages[stage] = "skipped_no_upcoming_show"

        stage = "prediction_validation"
        stages[stage] = "running"
        if validate_predictions(bands=[band], max_age_hours=48):
            raise RuntimeError("Prediction table validation failed")
        stages[stage] = "success"

        stage = "accuracy_validation"
        stages[stage] = "running"
        if validate_accuracy(
            bands=[band],
            max_age_hours=72,
            replay_window=50,
            require_exact_retained_window=True,
        ):
            raise RuntimeError("Accuracy table validation failed")
        stages[stage] = "success"
    except Exception as exc:
        stages[stage] = "failed"
        outcome["status"] = "failed"
        outcome["error"] = f"{stage}: {exc}"
        print(
            f"::error::Raw corrections were applied, but derived-data refresh failed: {outcome['error']}"
        )
        print(
            "Recover derived data with these existing commands, then revalidate the website band cache:"
        )
        for command in outcome["recovery_commands"]:
            print(command)
        return outcome

    outcome["status"] = "success"
    outcome["cache_invalidation_required"] = True
    return outcome


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect corrections but don't apply them (default)",
    )
    mode.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually apply detected corrections",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for the correction report (default: correction_sweep_report_{band}.json)",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["setlists"],
        choices=["shows", "setlists", "songs", "venues"],
        help="Tables to check for corrections",
    )

    args = parser.parse_args()

    if args.output is None:
        args.output = f"correction_sweep_report_{args.band}.json"

    dry_run = not args.no_dry_run

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

    applied = sum(result.corrections_applied for result in results.values())
    refresh = refresh_corrected_band(
        band=args.band, client=client, applied=applied, dry_run=dry_run
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
        "summary": {name: result.summary() for name, result in results.items()},
        "results": {name: result.to_dict() for name, result in results.items()},
        "post_correction_refresh": refresh,
    }

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDetailed report saved to: {output_path}")

    for result in results.values():
        for warning in result.warnings:
            print(f"::warning::{result.table_name}: {warning}")

    # Exit non-zero on any error (fetch failures, refused or failed applies)
    total_errors = sum(len(r.errors) for r in results.values())
    if refresh["status"] == "failed":
        total_errors += 1
    if total_errors > 0 or not results:
        for result in results.values():
            for error in result.errors:
                print(f"::error::{result.table_name}: {error}")
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
