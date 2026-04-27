"""One-time admin script to canonicalize WSP song names in wsp_setlists_raw.

Scans all setlist rows, applies the WSP song canonicalizer, and updates
any rows where the song name differs from the canonical form.

Usage:
  uv run python scripts/admin/fix_wsp_song_names.py --dry-run
  uv run python scripts/admin/fix_wsp_song_names.py
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.wsp.song_canonicalizer import (  # noqa: E402
    build_canonical_lookup,
    canonicalize_song_name,
)
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402


def _fetch_all_setlist_song_names(client) -> dict[str, list[int]]:
    """Return {song_name: [row_ids]} for all rows in wsp_setlists_raw."""
    names: dict[str, list[int]] = defaultdict(list)
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("wsp_setlists_raw")
            .select("id,song_name")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        for row in batch:
            name = row.get("song_name", "")
            if name:
                names[name].append(row["id"])
        if len(batch) < page_size:
            break
        offset += page_size
    return names


def _fetch_songs_raw(client) -> list[dict]:
    """Page through wsp_songs_raw and return all rows."""
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("wsp_songs_raw")
            .select("song_name,aka")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report affected rows without updating anything.",
    )
    args = parser.parse_args()

    client = get_supabase_client()

    print("Building canonical lookup from wsp_songs_raw...")
    songs_rows = _fetch_songs_raw(client)
    canonical_lookup = build_canonical_lookup(songs_rows)
    print(f"  {len(canonical_lookup)} canonical entries loaded.")

    print("Fetching all setlist song names...")
    song_name_groups = _fetch_all_setlist_song_names(client)
    total_rows = sum(len(ids) for ids in song_name_groups.values())
    print(f"  {total_rows} setlist rows across {len(song_name_groups)} distinct names.")

    changes: list[tuple[str, str, list[int]]] = []
    for raw_name, row_ids in sorted(song_name_groups.items()):
        canonical = canonicalize_song_name(raw_name, canonical_lookup)
        if canonical != raw_name:
            changes.append((raw_name, canonical, row_ids))

    if not changes:
        print("\nAll song names are already canonical. Nothing to fix.")
        return

    print(f"\nFound {len(changes)} non-canonical song name(s):\n")
    total_affected = 0
    for raw, canonical, ids in changes:
        print(f"  {raw!r} -> {canonical!r}  ({len(ids)} rows)")
        total_affected += len(ids)

    print(f"\nTotal: {total_affected} rows to update.")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return

    for raw, canonical, ids in changes:
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            client.table("wsp_setlists_raw").update({"song_name": canonical}).in_(
                "id", batch
            ).execute()

    print(f"\nUpdated {total_affected} rows to canonical song names.")


if __name__ == "__main__":
    main()
