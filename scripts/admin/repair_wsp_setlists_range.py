#!/usr/bin/env python3
"""Delete WSP setlist rows for a date range without deleting show identities.

Usage:
  uv run python scripts/admin/repair_wsp_setlists_range.py --date-from 2020-01-01 --date-to 2026-12-31 --dry-run
  uv run python scripts/admin/repair_wsp_setlists_range.py --date-from 2020-01-01 --date-to 2026-12-31
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import List

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from scripts.common import batched_values
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402

PAGE_SIZE = 1000
DELETE_BATCH_SIZE = 100


def _validate_date(raw: str) -> str:
    datetime.strptime(raw, "%Y-%m-%d")
    return raw


def _fetch_show_ids(client, date_from: str, date_to: str) -> List[int]:
    response = (
        client.table("wsp_shows_raw")
        .select("show_id")
        .gte("show_date", date_from)
        .lte("show_date", date_to)
        .order("show_date")
        .execute()
    )
    return [
        int(row["show_id"])
        for row in (response.data or [])
        if row.get("show_id") is not None
    ]


def _count_setlist_rows(client, show_ids: List[int]) -> int:
    total = 0
    for batch in batched_values(show_ids, DELETE_BATCH_SIZE):
        offset = 0
        while True:
            response = (
                client.table("wsp_setlists_raw")
                .select("show_id")
                .in_("show_id", batch)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            rows = response.data or []
            total += len(rows)
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
    return total


def _delete_setlist_rows(client, show_ids: List[int]) -> int:
    deleted = 0
    for batch in batched_values(show_ids, DELETE_BATCH_SIZE):
        response = (
            client.table("wsp_setlists_raw").delete().in_("show_id", batch).execute()
        )
        deleted += len(response.data or [])
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", required=True, type=_validate_date)
    parser.add_argument("--date-to", required=True, type=_validate_date)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report affected WSP rows without deleting anything.",
    )
    args = parser.parse_args()

    if args.date_from > args.date_to:
        raise SystemExit("--date-from must be <= --date-to")

    client = get_supabase_client()
    show_ids = _fetch_show_ids(client, args.date_from, args.date_to)

    if not show_ids:
        print(
            f"No WSP shows found between {args.date_from} and {args.date_to}. Nothing to do."
        )
        return

    setlist_row_count = _count_setlist_rows(client, show_ids)
    print(
        f"WSP repair window {args.date_from}..{args.date_to}: {len(show_ids)} show(s), "
        f"{setlist_row_count} setlist row(s)."
    )
    print("Show rows in wsp_shows_raw will be preserved.")

    if args.dry_run:
        print("[DRY RUN] No changes made.")
        return

    deleted = _delete_setlist_rows(client, show_ids)
    print(
        f"Deleted {deleted} wsp_setlists_raw row(s) for {len(show_ids)} show(s) in the requested range."
    )
    print("Next step:")
    print(
        f"  uv run python scripts/run_wsp_collection.py --year_start {args.date_from[:4]} --year_end {args.date_to[:4]}"
    )


if __name__ == "__main__":
    main()
