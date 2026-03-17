#!/usr/bin/env python3
from __future__ import annotations

"""
TourWrangler fallback test runner for specific WSP dates.

Steps:
1) For each target date, find wsp_shows_raw row(s) (show_id, city, state).
2) Backup existing wsp_setlists_raw rows for those show_ids to tw_test_backups/....json.
3) Delete those rows to simulate EC being empty.
4) Fetch setlists from TourWrangler and upsert into wsp_setlists_raw (source='tourwrangler' if column exists).
5) Compare current (TW) rows to the EC backup and print summary, also write both to files for review.

Usage:
  uv run python scripts/manual/wsp/tw_fallback_test.py --dates 2025-10-03 2025-10-04
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Ensure project root is importable like other scripts do
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Local imports
from src.jambandnerd.data_collection.wsp.tourwrangler import (
    fetch_setlist_from_tourwrangler,
)
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import get_table_schema, upsert_dataframe
from src.jambandnerd.db.validation import (
    coerce_df_types,
    validate_dataframe_against_table,
)


def compute_source_hash_row(rec: dict) -> str:
    payload = json.dumps(
        {k: (None if pd.isna(v) else v) for k, v in rec.items()},
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_name(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"\[\s*\d+\s*\]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def to_keyed(rows: List[Dict[str, Any]]):
    keyed = defaultdict(set)
    for r in rows:
        sid = str(r.get("show_id"))
        setnum = str(r.get("set_number"))
        pos = int(r.get("song_position") or 0)
        name = normalize_name(str(r.get("song_name", "")))
        keyed[sid].add((setnum, pos, name))
    return keyed


def run(dates: List[str]) -> None:
    client = get_supabase_client()

    # 1) Locate shows
    shows: List[Dict[str, Any]] = []
    for d in dates:
        resp = (
            client.table("wsp_shows_raw")
            .select("show_id, show_date, city, state")
            .eq("show_date", d)
            .execute()
        )
        shows.extend(resp.data or [])
    if not shows:
        print("No shows found for requested dates.")
        return
    show_ids = [str(s["show_id"]) for s in shows if s.get("show_id")]
    print(f"Found {len(shows)} shows:")
    for s in shows:
        print("  ", s)

    # 2) Backup existing EC rows
    backup_dir = Path("tw_test_backups")
    backup_dir.mkdir(exist_ok=True)
    backup_file = backup_dir / f"wsp_ec_backup_{'_'.join(dates)}.json"
    existing = (
        client.table("wsp_setlists_raw")
        .select("*")
        .in_("show_id", show_ids)
        .execute()
        .data
        or []
    )
    backup_file.write_text(json.dumps(existing, indent=2))
    print(f"Backed up {len(existing)} existing setlist rows to {backup_file}")

    # 3) Delete existing to simulate EC empty
    if existing:
        client.table("wsp_setlists_raw").delete().in_("show_id", show_ids).execute()
        print("Deleted prior setlist rows for test.")

    # 4) Fetch from TourWrangler
    schema = get_table_schema("wsp_setlists_raw")
    has_source = any(
        (str(col.get("column_name", "")).lower() == "source") for col in (schema or [])
    )

    tw_rows_all: List[Dict[str, Any]] = []
    for s in shows:
        sid = str(s["show_id"])
        sdate = pd.to_datetime(s["show_date"]).date()
        city = s.get("city")
        state = s.get("state")
        rows = fetch_setlist_from_tourwrangler(sdate, sid, city, state)
        print(f"TourWrangler rows for show_id={sid} date={sdate}: {len(rows)}")
        for r in rows:
            r.setdefault("song_notes", "")
            if has_source:
                r["source"] = "tourwrangler"
        tw_rows_all.extend(rows)

    if not tw_rows_all:
        print("No TourWrangler rows parsed; aborting without upsert.")
        return

    df = pd.DataFrame(tw_rows_all)
    df["source_hash"] = df.apply(
        lambda row: compute_source_hash_row(row.to_dict()), axis=1
    )

    if schema:
        df = coerce_df_types(df, schema)
        _ = validate_dataframe_against_table(
            df, "wsp_setlists_raw", schema
        )  # warnings are non-blocking

    upsert_dataframe(
        "wsp_setlists_raw",
        df,
        conflict_columns=["show_id", "set_number", "song_position"],
    )
    print(f"Upserted {len(df)} TourWrangler rows.")

    # 5) Compare current (TW) rows vs EC backup
    current = (
        client.table("wsp_setlists_raw")
        .select("*")
        .in_("show_id", show_ids)
        .execute()
        .data
        or []
    )
    cur_keys = to_keyed(current)
    ec_keys = to_keyed(existing)

    summary = {}

    def strip_pos(xs):
        return {(a, c) for (a, _b, c) in xs}

    for sid in show_ids:
        cur = cur_keys.get(sid, set())
        ec = ec_keys.get(sid, set())
        missing_in_tw = sorted(list(ec - cur))
        extra_in_tw = sorted(list(cur - ec))
        # order-only or membership diffs ignoring position
        order_or_membership = sorted(list(strip_pos(cur) ^ strip_pos(ec)))
        summary[sid] = {
            "ec_count": len(ec),
            "tw_count": len(cur),
            "missing_in_tw_count": len(missing_in_tw),
            "extra_in_tw_count": len(extra_in_tw),
            "order_or_membership_preview": order_or_membership[:10],
            "missing_in_tw_preview": missing_in_tw[:10],
            "extra_in_tw_preview": extra_in_tw[:10],
        }

    print("\n=== EC vs TW Summary (backup taken at start of this run) ===")
    print(json.dumps(summary, indent=2))

    # Additionally compare against any prior EC backup file if it exists
    prior_backup = backup_dir / "wsp_ec_backup_2025-10-03_04.json"
    if prior_backup.exists():
        try:
            prior_ec = json.loads(prior_backup.read_text())
            prior_ec_keys = to_keyed(prior_ec)
            prior_summary = {}
            for sid in show_ids:
                cur = cur_keys.get(sid, set())
                ecp = prior_ec_keys.get(sid, set())
                missing_in_tw = sorted(list(ecp - cur))
                extra_in_tw = sorted(list(cur - ecp))
                order_or_membership = sorted(list(strip_pos(cur) ^ strip_pos(ecp)))
                prior_summary[sid] = {
                    "prior_ec_count": len(ecp),
                    "tw_count": len(cur),
                    "missing_in_tw_count": len(missing_in_tw),
                    "extra_in_tw_count": len(extra_in_tw),
                    "order_or_membership_preview": order_or_membership[:10],
                    "missing_in_tw_preview": missing_in_tw[:10],
                    "extra_in_tw_preview": extra_in_tw[:10],
                }
            print("\n=== EC vs TW Summary (compared to prior EC backup file) ===")
            print(json.dumps(prior_summary, indent=2))
        except Exception as e:
            print(f"Could not compare with prior EC backup ({prior_backup}): {e}")

    # Write artifacts
    (backup_dir / f"wsp_tw_current_rows_{'_'.join(dates)}.json").write_text(
        json.dumps(current, indent=2)
    )
    print(
        f"Wrote TW rows to {(backup_dir / f'wsp_tw_current_rows_{"_".join(dates)}.json')}\nDone."
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Run TW fallback for specific dates and compare against EC backup"
    )
    ap.add_argument(
        "--dates", nargs="+", required=True, help="Dates in YYYY-MM-DD format"
    )
    args = ap.parse_args()
    run(args.dates)
