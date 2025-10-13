#!/usr/bin/env python3
from __future__ import annotations

"""
Compare EC setlists (from DB or backup) vs TourWrangler parse for a specific date and URL.

Usage:
  uv run python scripts/tw_compare_ec_tw.py --date 2025-10-03 \
    --url https://www.tourwrangler.com/artists/widespread-panic/shows/october-3-2025-radians-amphitheater-memphis-tennessee

This script does not write to the database; it only reads and prints a summary.
"""

import os
import sys
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Ensure project root on path (like other scripts)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.data_collection.wsp.tourwrangler import parse_show_page


def normalize_name(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"\[\s*\d+\s*\]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def to_keyed(rows: List[Dict[str, Any]]):
    keyed = defaultdict(list)
    for r in rows:
        sid = str(r.get("show_id"))
        setnum = str(r.get("set_number"))
        pos = int(r.get("song_position") or 0)
        name = normalize_name(str(r.get("song_name", "")))
        keyed[sid].append((setnum, pos, name))
    return keyed


def run(date_str: str, url: str) -> None:
    client = get_supabase_client()

    # Find show
    shows = client.table("wsp_shows_raw").select("show_id, show_date, city, state").eq("show_date", date_str).execute().data or []
    if not shows:
        print(f"No show found for {date_str}")
        return
    show = shows[0]
    sid = str(show["show_id"])
    print(f"Show: {show}")

    # EC rows (from DB). If not found, try local prior backup file
    ec_rows = client.table("wsp_setlists_raw").select("*").eq("show_id", sid).execute().data or []
    if not ec_rows:
        backup = Path("tw_test_backups/wsp_ec_backup_2025-10-03_04.json")
        if backup.exists():
            prior = json.loads(backup.read_text())
            ec_rows = [r for r in prior if str(r.get("show_id")) == sid]
            print(f"EC rows loaded from backup: {len(ec_rows)}")
        else:
            print("No EC rows found in DB or backup.")

    # TW parse from URL
    tw_rows = parse_show_page(url, sid)

    # Compare
    def summarize(rows: List[Dict[str, Any]]):
        return {
            "count": len(rows),
            "sample": rows[:5],
        }

    print("\nSummary:")
    print(json.dumps({
        "ec": summarize(ec_rows),
        "tw": summarize(tw_rows),
    }, indent=2, default=str))

    # Keyed compare ignoring order: membership by (set, name)
    ec_setnames = {(str(r.get("set_number")), normalize_name(r.get("song_name"))) for r in ec_rows}
    tw_setnames = {(str(r.get("set_number")), normalize_name(r.get("song_name"))) for r in tw_rows}
    missing_in_tw = sorted(list(ec_setnames - tw_setnames))[:20]
    extra_in_tw = sorted(list(tw_setnames - ec_setnames))[:20]

    print("\nDiff (Ignoring position):")
    print(json.dumps({
        "missing_in_tw": missing_in_tw,
        "extra_in_tw": extra_in_tw,
    }, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Compare EC vs TW for a specific date")
    ap.add_argument("--date", required=True)
    ap.add_argument("--url", required=True)
    args = ap.parse_args()
    run(args.date, args.url)
