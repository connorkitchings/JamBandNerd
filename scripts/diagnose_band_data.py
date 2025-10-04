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
import sys
import os
import pandas as pd
from datetime import date, timedelta

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.config import BAND_ID_COLUMNS


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
        "stats": {}
    }
    
    # Print header
    print(f"\n{'='*60}")
    print(f"Diagnosing {band.upper()} Data")
    print(f"{'='*60}")
    print(f"Primary ID Column: {id_col}")
    
    shows_table = f"{band}_shows_raw"
    setlists_table = f"{band}_setlists_raw"
    
    # Check 1: Verify shows table
    try:
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        shows_resp = client.table(shows_table).select("*").gte("show_date", cutoff).execute()
        shows_df = pd.DataFrame(shows_resp.data)
        
        print(f"\n📊 Shows in last 30 days: {len(shows_df)}")
        results["stats"]["recent_shows"] = len(shows_df)
        
        if shows_df.empty:
            results["issues"].append("No recent shows found")
            print("❌ No recent shows found!")
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
            results["issues"].append(f"Date column '{date_col}' missing from shows table")
            print(f"❌ Date column '{date_col}' NOT FOUND!")
            # Try alternate date columns
            alt_date_cols = [c for c in shows_df.columns if 'date' in c.lower()]
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
            results["issues"].append(f"ID column '{id_col}' missing from setlists table")
            print(f"❌ Column '{id_col}' NOT FOUND in setlists table!")
            print(f"Available columns: {', '.join(setlists_df.columns)}")
            return results
        
        print(f"✅ ID column '{id_col}' found in setlists table")
        
        # Check for required setlist columns
        required_setlist_cols = ["song_name", "set_number"]
        pos_col = "position" if band == "phish" else "song_position"
        required_setlist_cols.append(pos_col)
        
        missing_cols = [c for c in required_setlist_cols if c not in setlists_df.columns]
        if missing_cols:
            results["issues"].append(f"Missing required setlist columns: {', '.join(missing_cols)}")
            print(f"⚠️  Missing columns: {', '.join(missing_cols)}")
            
    except Exception as e:
        results["issues"].append(f"Error fetching setlists: {e}")
        print(f"❌ Error fetching setlists: {e}")
        return results
    
    # Check 3: Find orphaned shows (shows without setlists)
    try:
        # Get all setlist IDs for matching
        all_setlists_resp = client.table(setlists_table).select(id_col).execute()
        all_setlists_df = pd.DataFrame(all_setlists_resp.data)
        
        show_ids = set(shows_df[id_col].astype(str))
        setlist_ids = set(all_setlists_df[id_col].astype(str)) if not all_setlists_df.empty else set()
        orphaned = show_ids - setlist_ids
        
        print(f"\n🔍 Orphaned shows (shows without setlists): {len(orphaned)}")
        results["stats"]["orphaned_shows"] = len(orphaned)
        
        if orphaned:
            results["issues"].append(f"{len(orphaned)} shows without setlist data")
            print("\nFirst 10 orphaned shows:")
            for show_id in list(orphaned)[:10]:
                show = shows_df[shows_df[id_col].astype(str) == show_id].iloc[0]
                show_date = show.get('show_date', 'Unknown')
                venue = show.get('venue_name') or show.get('venuename') or show.get('venue') or 'Unknown venue'
                print(f"  - {show_date} at {venue} (ID: {show_id})")
                
            if verbose and len(orphaned) > 10:
                print(f"\n  ... and {len(orphaned) - 10} more")
        else:
            print("✅ All recent shows have setlist data")
            
    except Exception as e:
        results["issues"].append(f"Error checking for orphaned shows: {e}")
        print(f"❌ Error checking for orphaned shows: {e}")
    
    # Check 4: Data quality checks
    print(f"\n🔎 Data Quality Checks")
    
    # Check for duplicate show IDs
    duplicate_shows = shows_df[shows_df.duplicated(subset=[id_col], keep=False)]
    if not duplicate_shows.empty:
        results["issues"].append(f"{len(duplicate_shows)} duplicate show IDs found")
        print(f"⚠️  {len(duplicate_shows)} duplicate show IDs found")
        if verbose:
            print(f"   Duplicate IDs: {duplicate_shows[id_col].unique().tolist()[:5]}")
    else:
        print(f"✅ No duplicate show IDs")
    
    # Check for missing venue information
    venue_cols = ['venue_name', 'venuename', 'venue']
    venue_col_found = next((c for c in venue_cols if c in shows_df.columns), None)
    if venue_col_found:
        missing_venues = shows_df[venue_col_found].isna().sum()
        if missing_venues > 0:
            results["issues"].append(f"{missing_venues} shows with missing venue data")
            print(f"⚠️  {missing_venues} shows missing venue information")
        else:
            print(f"✅ All shows have venue information")
    else:
        results["issues"].append("No venue column found in shows table")
        print(f"⚠️  No venue column found")
    
    # Final summary
    print(f"\n{'='*60}")
    if results["issues"]:
        print(f"❌ Found {len(results['issues'])} issue(s)")
        for i, issue in enumerate(results["issues"], 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ No issues found - data looks good!")
    print(f"{'='*60}\n")
    
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
  for band in goose phish wsp; do
    python scripts/diagnose_band_data.py --band $band
  done
        """
    )
    parser.add_argument(
        "--band",
        required=True,
        choices=["goose", "phish", "wsp"],
        help="Band to diagnose"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output including sample data"
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
