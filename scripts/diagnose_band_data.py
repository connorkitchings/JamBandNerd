#!/usr/bin/env python3
"""Diagnose data consistency issues for a band.

This script checks for common data integrity issues including:
- ID column presence and consistency
- Missing setlists for recent shows
- Date column consistency
- Null value detection

Usage:
    uv run python scripts/diagnose_band_data.py --band goose
    uv run python scripts/diagnose_band_data.py --band phish --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import date, timedelta

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.config import BAND_ID_COLUMNS
from src.jambandnerd.db.connection import get_supabase_client


def _completed_show_bounds(
    *, today: date | None = None, days: int = 30
) -> tuple[str, str]:
    """Return the recent completed-show window, excluding today."""
    today = today or date.today()
    cutoff = today - timedelta(days=days)
    end_date = today - timedelta(days=1)
    return cutoff.isoformat(), end_date.isoformat()


def _batched(items: list[str], size: int = 50) -> list[list[str]]:
    """Split IDs into stable batches for Supabase `in_` queries."""
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def _fetch_setlist_ids_for_shows(
    client, setlists_table: str, id_col: str, show_ids: set[str]
) -> set[str]:
    """Fetch setlist IDs for the target shows only."""
    if not show_ids:
        return set()

    setlist_ids: set[str] = set()
    for chunk in _batched(sorted(show_ids)):
        resp = client.table(setlists_table).select(id_col).in_(id_col, chunk).execute()
        for item in resp.data or []:
            value = item.get(id_col)
            if value is not None:
                setlist_ids.add(str(value))
    return setlist_ids


def _summarize_missing_setlist_diagnostics(
    band: str, diagnostics: list[dict[str, object]]
) -> tuple[str | None, str | None]:
    """Convert classified missing-setlist diagnostics into issue/warning text."""
    if not diagnostics:
        return None, None

    if band != "wsp":
        return f"{len(diagnostics)} shows without setlist data", None

    counts = Counter(str(item.get("diagnosis", "unknown")) for item in diagnostics)
    issue_statuses = {
        "collector_missed_setlist",
        "ec_request_failed",
        "fallback_data_available",
        "missing_source_url",
        "unknown",
    }
    if set(counts).issubset({"upstream_missing_setlist"}):
        return None, (
            f"{len(diagnostics)} WSP shows are blocked by upstream setlist pages "
            "that have not published a setlist yet"
        )

    detail = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    if set(counts) & issue_statuses:
        return f"{len(diagnostics)} WSP shows without setlist data ({detail})", None

    return f"{len(diagnostics)} shows without setlist data", None


def diagnose_band(band: str, verbose: bool = False) -> dict[str, any]:
    """Run comprehensive diagnostics on band data.

    Args:
        band: Band slug (goose, phish, or wsp)
        verbose: Whether to print detailed output

    Returns:
        Dictionary containing diagnostic results and any issues found
    """
    client = get_supabase_client()
    id_col = BAND_ID_COLUMNS.get(band, "show_id")

    results = {
        "band": band,
        "id_column": id_col,
        "issues": [],
        "warnings": [],
        "stats": {},
    }

    # Print header
    print(f"\n{'=' * 60}")
    print(f"Diagnosing {band.upper()} Data")
    print(f"{'=' * 60}")
    print(f"Primary ID Column: {id_col}")

    shows_table = f"{band}_shows_raw"
    setlists_table = f"{band}_setlists_raw"

    # Check 1: Verify shows table
    try:
        cutoff, end_date = _completed_show_bounds()
        shows_resp = (
            client.table(shows_table)
            .select("*")
            .gte("show_date", cutoff)
            .lte("show_date", end_date)
            .execute()
        )
        shows_df = pd.DataFrame(shows_resp.data)

        print(f"\n📊 Completed shows in last 30 days: {len(shows_df)}")
        results["stats"]["recent_shows"] = len(shows_df)

        if shows_df.empty:
            print("ℹ️ No completed recent shows found.")
            return results

        # Check for ID column presence in shows
        if id_col not in shows_df.columns:
            results["issues"].append(f"ID column '{id_col}' missing from shows table")
            print(f"❌ Column '{id_col}' NOT FOUND in shows table!")
            print(f"Available columns: {', '.join(shows_df.columns)}")
            return results

        print(f"✅ ID column '{id_col}' found in shows table")

        # Check for show_date column
        date_col = "show_date"
        if date_col not in shows_df.columns:
            results["issues"].append(
                f"Date column '{date_col}' missing from shows table"
            )
            print(f"❌ Date column '{date_col}' NOT FOUND!")
            # Try alternate date columns
            alt_date_cols = [c for c in shows_df.columns if "date" in c.lower()]
            if alt_date_cols:
                print(f"   Found alternate date columns: {', '.join(alt_date_cols)}")
        else:
            print(f"✅ Date column '{date_col}' found")
            # Check for null dates
            null_dates = shows_df[date_col].isna().sum()
            if null_dates > 0:
                results["issues"].append(f"{null_dates} shows with null dates")
                print(f"⚠️  {null_dates} shows have null dates")

        # Check for null IDs
        null_ids = shows_df[id_col].isna().sum()
        if null_ids > 0:
            results["issues"].append(f"{null_ids} shows with null IDs")
            print(f"⚠️  {null_ids} shows have null IDs")

    except Exception as e:
        results["issues"].append(f"Error fetching shows: {e}")
        print(f"❌ Error fetching shows: {e}")
        return results

    # Check 2: Verify setlists table
    try:
        setlists_resp = client.table(setlists_table).select("*").limit(1000).execute()
        setlists_df = pd.DataFrame(setlists_resp.data)

        print(f"📋 Setlist records (sample): {len(setlists_df)}")
        results["stats"]["setlist_records_sample"] = len(setlists_df)

        if setlists_df.empty:
            results["issues"].append("No setlist data found")
            print("❌ No setlist data found!")
            return results

        # Check for ID column in setlists
        if id_col not in setlists_df.columns:
            results["issues"].append(
                f"ID column '{id_col}' missing from setlists table"
            )
            print(f"❌ Column '{id_col}' NOT FOUND in setlists table!")
            print(f"Available columns: {', '.join(setlists_df.columns)}")
            return results

        print(f"✅ ID column '{id_col}' found in setlists table")

        # Check for required setlist columns
        required_setlist_cols = ["song_name", "set_number"]
        pos_col = "position" if band == "phish" else "song_position"
        required_setlist_cols.append(pos_col)

        missing_cols = [
            c for c in required_setlist_cols if c not in setlists_df.columns
        ]
        if missing_cols:
            results["issues"].append(
                f"Missing required setlist columns: {', '.join(missing_cols)}"
            )
            print(f"⚠️  Missing columns: {', '.join(missing_cols)}")

    except Exception as e:
        results["issues"].append(f"Error fetching setlists: {e}")
        print(f"❌ Error fetching setlists: {e}")
        return results

    # Check 3: Find orphaned shows (shows without setlists)
    try:
        show_ids = set(shows_df[id_col].astype(str))
        setlist_ids = _fetch_setlist_ids_for_shows(
            client, setlists_table, id_col, show_ids
        )
        orphaned = show_ids - setlist_ids

        print(
            f"\n🔍 Orphaned completed shows (shows without setlists): {len(orphaned)}"
        )
        results["stats"]["orphaned_shows"] = len(orphaned)

        if orphaned:
            print("\nFirst 10 orphaned shows:")
            for show_id in list(orphaned)[:10]:
                show = shows_df[shows_df[id_col].astype(str) == show_id].iloc[0]
                show_date = show.get("show_date", "Unknown")
                venue = (
                    show.get("venue_name")
                    or show.get("venuename")
                    or show.get("venue")
                    or "Unknown venue"
                )
                print(f"  - {show_date} at {venue} (ID: {show_id})")

            if verbose and len(orphaned) > 10:
                print(f"\n  ... and {len(orphaned) - 10} more")

            diagnostics: list[dict[str, object]] = []
            if band == "wsp":
                try:
                    from src.jambandnerd.data_collection.wsp.orchestration import (
                        classify_missing_recent_setlists,
                    )

                    diagnostics = classify_missing_recent_setlists(
                        client,
                        shows_df[shows_df[id_col].astype(str).isin(orphaned)].to_dict(
                            "records"
                        ),
                    )
                    if diagnostics:
                        print("\nWSP missing-setlist diagnostics:")
                        for item in diagnostics[:10]:
                            print(
                                "  - "
                                f"{item.get('show_date')} (ID: {item.get('show_id')}): "
                                f"{item.get('diagnosis')} - {item.get('detail')}"
                            )
                except Exception as exc:
                    print(f"⚠️  Could not classify WSP missing setlists: {exc}")

            issue, warning = _summarize_missing_setlist_diagnostics(
                band,
                diagnostics or [{"diagnosis": "unknown"} for _ in orphaned],
            )
            if issue:
                results["issues"].append(issue)
            if warning:
                results["warnings"].append(warning)
        else:
            print("✅ All recent shows have setlist data")

    except Exception as e:
        results["issues"].append(f"Error checking for orphaned shows: {e}")
        print(f"❌ Error checking for orphaned shows: {e}")

    # Check 4: Data quality checks
    print("\n🔎 Data Quality Checks")

    # Check for duplicate show IDs
    duplicate_shows = shows_df[shows_df.duplicated(subset=[id_col], keep=False)]
    if not duplicate_shows.empty:
        results["issues"].append(f"{len(duplicate_shows)} duplicate show IDs found")
        print(f"⚠️  {len(duplicate_shows)} duplicate show IDs found")
        if verbose:
            print(f"   Duplicate IDs: {duplicate_shows[id_col].unique().tolist()[:5]}")
    else:
        print("✅ No duplicate show IDs")

    # Check for missing venue information
    venue_cols = ["venue_name", "venuename", "venue"]
    venue_col_found = next((c for c in venue_cols if c in shows_df.columns), None)
    if venue_col_found:
        missing_venues = shows_df[venue_col_found].isna().sum()
        if missing_venues > 0:
            results["issues"].append(f"{missing_venues} shows with missing venue data")
            print(f"⚠️  {missing_venues} shows missing venue information")
        else:
            print("✅ All shows have venue information")
    else:
        results["issues"].append("No venue column found in shows table")
        print("⚠️  No venue column found")

    # Final summary
    print(f"\n{'=' * 60}")
    if results["issues"]:
        print(f"❌ Found {len(results['issues'])} issue(s)")
        for i, issue in enumerate(results["issues"], 1):
            print(f"  {i}. {issue}")
        if results["warnings"]:
            print(f"⚠️  Additional warnings: {len(results['warnings'])}")
            for i, warning in enumerate(results["warnings"], 1):
                print(f"  {i}. {warning}")
    elif results["warnings"]:
        print(f"⚠️  Warnings only ({len(results['warnings'])})")
        for i, warning in enumerate(results["warnings"], 1):
            print(f"  {i}. {warning}")
    else:
        print("✅ No issues found - data looks good!")
    print(f"{'=' * 60}\n")

    return results


def main() -> None:
    """Main entry point for the diagnostic script."""
    parser = argparse.ArgumentParser(
        description="Diagnose data consistency issues for a band",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run basic diagnostics for Goose
  python scripts/diagnose_band_data.py --band goose

  # Run detailed diagnostics for Phish
  python scripts/diagnose_band_data.py --band phish --verbose

  # Check all bands
  for band in goose phish wsp billy um; do
    python scripts/diagnose_band_data.py --band $band
  done
        """,
    )
    parser.add_argument(
        "--band",
        required=True,
        choices=["goose", "eggy", "phish", "wsp", "billy", "um"],
        help="Band to diagnose",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including sample data",
    )

    args = parser.parse_args()

    try:
        results = diagnose_band(args.band, verbose=args.verbose)

        # Exit with error code if issues found
        if results["issues"]:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nDiagnostics interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        if args.verbose:
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
