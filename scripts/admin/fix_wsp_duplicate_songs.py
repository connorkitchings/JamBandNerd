"""Detect and fix WSP setlist shows where the stats section caused duplicate songs.

Root cause: the HTML table parser fallback (used when the text parser returns empty)
does not stop when the page's per-song stats section begins.  The stats section
header row ("StatsSongLTPDateL3TP" etc.) is filtered by _validate_song_name with
`continue`, so parsing continues and the songs listed in the stats section are
appended as positions N+1 ... N+K within the same set.

This script:
  1. Scans wsp_setlists_raw for sets where the same song name appears more than once
     (which is the fingerprint of this bug — legitimate in-set repeats are
     extremely rare for WSP).
  2. For each flagged show, reports the problem and — unless --dry-run is passed —
     deletes all setlist rows for that show so the next collection re-scrapes it.
     (The show row in wsp_shows_raw is NOT deleted; the collector will find the
     existing show and re-populate its setlist rows from the fixed code.)

Usage:
  uv run python scripts/admin/fix_wsp_duplicate_songs.py --dry-run
  uv run python scripts/admin/fix_wsp_duplicate_songs.py
  uv run python scripts/admin/fix_wsp_duplicate_songs.py --date 2025-07-26
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, List

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402


def _fetch_all_wsp_setlists(client) -> List[Dict]:
    """Page through wsp_setlists_raw and return every row."""
    rows: List[Dict] = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("wsp_setlists_raw")
            .select("id,show_id,set_number,song_position,song_name")
            .order("show_id")
            .order("set_number")
            .order("song_position")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def _fetch_show_dates(client, show_ids: List[int]) -> Dict[int, str]:
    """Return {show_id: show_date} for the given show ids."""
    resp = (
        client.table("wsp_shows_raw")
        .select("show_id,show_date")
        .in_("show_id", show_ids)
        .execute()
    )
    return {r["show_id"]: r["show_date"] for r in (resp.data or [])}


def _find_duplicate_shows(rows: List[Dict]) -> Dict[int, List[Dict]]:
    """
    Return {show_id: [duplicate_rows]} for shows that have the same song name
    appearing more than once within the same set.
    """
    # Group by (show_id, set_number) -> list of song rows
    sets: Dict[tuple, List[Dict]] = defaultdict(list)
    for row in rows:
        key = (row["show_id"], row["set_number"])
        sets[key].append(row)

    affected: Dict[int, List[Dict]] = defaultdict(list)
    for (show_id, set_number), set_rows in sets.items():
        names = [
            r["song_name"] for r in sorted(set_rows, key=lambda r: r["song_position"])
        ]
        seen: Dict[str, int] = {}
        for i, name in enumerate(names):
            if name in seen:
                # This name appeared earlier — all rows after first occurrence are duplicates
                duplicates = [
                    r
                    for r in set_rows
                    if r["song_name"] == name and r["song_position"] > seen[name]
                ]
                affected[show_id].extend(duplicates)
            else:
                seen[name] = set_rows[i]["song_position"]

    return affected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report affected shows without deleting anything.",
    )
    parser.add_argument(
        "--date",
        help="Limit scan to a specific show date (YYYY-MM-DD). Useful for targeted fixes.",
    )
    args = parser.parse_args()

    client = get_supabase_client()

    print("Fetching all WSP setlist rows...")
    all_rows = _fetch_all_wsp_setlists(client)
    print(f"  {len(all_rows)} rows fetched.")

    # If --date is given, filter to that show only
    if args.date:
        date_resp = (
            client.table("wsp_shows_raw")
            .select("show_id")
            .eq("show_date", args.date)
            .execute()
        )
        target_ids = {r["show_id"] for r in (date_resp.data or [])}
        if not target_ids:
            print(f"No WSP show found for date {args.date}.")
            return
        all_rows = [r for r in all_rows if r["show_id"] in target_ids]
        print(f"  Filtered to {len(all_rows)} rows for date {args.date}.")

    affected = _find_duplicate_shows(all_rows)

    if not affected:
        print("No shows with duplicate songs found. Database looks clean.")
        return

    show_dates = _fetch_show_dates(client, list(affected.keys()))

    print(f"\nFound {len(affected)} show(s) with duplicate songs:\n")
    for show_id, dup_rows in sorted(
        affected.items(), key=lambda kv: show_dates.get(kv[0], "")
    ):
        date_str = show_dates.get(show_id, "unknown date")
        by_set: Dict[str, List[Dict]] = defaultdict(list)
        for r in dup_rows:
            by_set[r["set_number"]].append(r)
        print(f"  Show {show_id} ({date_str}):")
        for set_num, set_dups in sorted(by_set.items()):
            songs = ", ".join(
                f"pos {r['song_position']}: {r['song_name']}"
                for r in sorted(set_dups, key=lambda r: r["song_position"])
            )
            print(f"    Set {set_num} — {len(set_dups)} duplicate row(s): {songs}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return

    print(
        "\nDeleting ALL setlist rows for affected shows so they will be re-scraped..."
    )
    affected_show_ids = list(affected.keys())
    delete_resp = (
        client.table("wsp_setlists_raw")
        .delete()
        .in_("show_id", affected_show_ids)
        .execute()
    )
    deleted = len(delete_resp.data or [])
    print(f"  Deleted {deleted} row(s) across {len(affected_show_ids)} show(s).")
    print("\nNext steps:")
    print("  Run WSP collection to re-scrape the cleaned shows:")
    print("  uv run python scripts/run_wsp_collection.py")
    print("  (The fixed collector code will now stop at the stats section.)")


if __name__ == "__main__":
    main()
