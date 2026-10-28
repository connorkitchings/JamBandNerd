"""Delete duplicate rows from billy_shows_raw left by source-UUID drift.

Two groups are removed (deleting a show also deletes its billy_setlists_raw rows):
  ghost: a 0-song show whose same-date sibling has >= 3 songs (rule-based; the
         16 expected in prod were ids 96, 97, 99, 1194, 1195, 1276, 1364, 1568,
         1684, 1686, 3260, 24445, 24447, 27105, 29223, 29233).
  pair:  operator-chosen rows from a hard-coded allowlist of known duplicate
         pairs, supplied with ``--delete-show-id <id>`` (repeatable). Ids outside
         the allowlist, or both ids of one pair, are refused. There is no generic
         same-date rule: real festival sets and sit-ins must never be deleted.
Ghosts referenced by ``setlist_accuracy.show_id`` (band billy) are skipped and
reported; allowlisted pair rows referenced there are deleted along with their
accuracy rows (backed up under ``accuracy``). Dry run by default; with ``--apply`` a JSON backup of every
deleted show and its setlist rows is written first.

Usage:
  uv run python scripts/admin/dedupe_billy_shows.py
  uv run python scripts/admin/dedupe_billy_shows.py --delete-show-id 1202 --delete-show-id 29184
  uv run python scripts/admin/dedupe_billy_shows.py --apply --delete-show-id 1202
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from src.jambandnerd.config import SETLIST_ACCURACY_TABLE  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402

SHOWS_TABLE = "billy_shows_raw"
SETLISTS_TABLE = "billy_setlists_raw"
BAND = "billy"
GHOST_MIN_SIBLING_SONGS = 3
PAGE_SIZE = 1000


# Known duplicate pairs: show_date -> the two show_ids; the operator picks one.
DUPLICATE_PAIR_ALLOWLIST: dict[str, frozenset[str]] = {
    "2019-02-24": frozenset({"1201", "1202"}),
    "2026-09-28": frozenset({"31152", "29184"}),
}


def validate_delete_ids(delete_ids: list[str]) -> set[str]:
    """Return the validated ids; raise ValueError for any outside the allowlist
    or when both ids of one allowlisted pair are given."""
    ids = {str(i) for i in delete_ids}
    allowed = set().union(*DUPLICATE_PAIR_ALLOWLIST.values())
    unknown = sorted(ids - allowed)
    if unknown:
        raise ValueError(f"show ids not in the duplicate-pair allowlist: {unknown}")
    for show_date, pair in DUPLICATE_PAIR_ALLOWLIST.items():
        if pair <= ids:
            raise ValueError(
                f"refusing to delete both rows of the {show_date} pair {sorted(pair)}"
            )
    return ids


def select_duplicate_shows(
    show_rows: list[dict[str, Any]],
    setlist_rows: list[dict[str, Any]],
    referenced_show_ids: set[str],
    delete_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Pick shows to delete.

    Returns ``{"ghost": [...], "pair": [...], "skipped": [(show_id, group)],
    "accuracy_show_ids": [str, ...]}``. Referenced ghosts are skipped; referenced
    pair rows are selected and listed in ``accuracy_show_ids`` so their
    ``setlist_accuracy`` rows get deleted too. Pure apart from raising ValueError
    on invalid ``delete_ids``.
    """
    requested = validate_delete_ids(delete_ids or [])
    songs: dict[str, set[str]] = defaultdict(set)
    for row in setlist_rows:
        songs[str(row["show_id"])].add(str(row["song_name"]))
    ids_by_date: dict[Any, list[str]] = defaultdict(list)
    original_id: dict[str, Any] = {}
    for row in show_rows:
        key = str(row["show_id"])
        original_id[key] = row["show_id"]
        ids_by_date[row["show_date"]].append(key)

    ghost: set[str] = set()
    for ids in ids_by_date.values():
        for show_id in ids:
            if not songs[show_id] and any(
                len(songs[other]) >= GHOST_MIN_SIBLING_SONGS
                for other in ids
                if other != show_id
            ):
                ghost.add(show_id)

    pair = {i for i in requested if i in original_id} - ghost

    result: dict[str, Any] = {
        "ghost": [],
        "pair": [],
        "skipped": [],
        "accuracy_show_ids": [],
    }
    for group, candidates in (("ghost", ghost), ("pair", pair)):
        for show_id in sorted(candidates, key=lambda i: (len(i), i)):
            referenced = show_id in referenced_show_ids
            if referenced and group == "ghost":
                result["skipped"].append((original_id[show_id], group))
                continue
            result[group].append(original_id[show_id])
            if referenced:
                # Operator-chosen pair rows are deleted together with their
                # setlist_accuracy rows (backed up first).
                result["accuracy_show_ids"].append(show_id)
    return result


def fetch_all(client: Any, table: str, columns: str, **eq: Any) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        query = client.table(table).select(columns)
        for col, val in eq.items():
            query = query.eq(col, val)
        page = query.range(start, start + PAGE_SIZE - 1).execute().data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def write_backup(backup_dir: Path, payload: dict[str, Any]) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"dedupe_billy_shows_{stamp}.json"
    payload = {**payload, "created_at": stamp}
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="Delete rows (default is a dry run)."
    )
    parser.add_argument("--backup-dir", type=Path, default=Path("./backups"))
    parser.add_argument(
        "--delete-show-id",
        action="append",
        default=[],
        help="Allowlisted duplicate-pair show_id to delete (repeatable).",
    )
    args = parser.parse_args()
    try:
        validate_delete_ids(args.delete_show_id)
    except ValueError as exc:
        parser.error(str(exc))

    client = get_supabase_client()
    show_rows = fetch_all(client, SHOWS_TABLE, "*")
    setlist_rows = fetch_all(client, SETLISTS_TABLE, "*")
    accuracy_rows = fetch_all(client, SETLIST_ACCURACY_TABLE, "*", band=BAND)
    referenced = {str(r["show_id"]) for r in accuracy_rows}
    selected = select_duplicate_shows(
        show_rows, setlist_rows, referenced, args.delete_show_id
    )
    to_delete = selected["ghost"] + selected["pair"]
    print(
        f"ghost: {len(selected['ghost'])} | pair: {len(selected['pair'])} | "
        f"skipped (referenced by {SETLIST_ACCURACY_TABLE}): "
        f"{len(selected['skipped'])}"
    )
    for show_id, group in selected["skipped"]:
        print(f"  SKIP show_id={show_id} ({group})")
    if not args.apply:
        print("Dry run; nothing deleted (pass --apply).")
        return
    if not to_delete:
        print("Nothing to delete.")
        return

    delete_set = set(to_delete)
    accuracy_ids = set(selected["accuracy_show_ids"])
    accuracy_to_delete = [r for r in accuracy_rows if str(r["show_id"]) in accuracy_ids]
    backup_path = write_backup(
        args.backup_dir,
        {
            "shows": [r for r in show_rows if r["show_id"] in delete_set],
            "setlists": [r for r in setlist_rows if r["show_id"] in delete_set],
            "accuracy": accuracy_to_delete,
        },
    )
    print(f"Backup written: {backup_path}")
    for sid in sorted(accuracy_ids):
        client.table(SETLIST_ACCURACY_TABLE).delete().eq("band", BAND).eq(
            "show_id", sid
        ).execute()
    for show_id in to_delete:
        # Explicit child delete first so we do not depend on FK cascade config.
        client.table(SETLISTS_TABLE).delete().eq("show_id", show_id).execute()
        client.table(SHOWS_TABLE).delete().eq("show_id", show_id).execute()
    print(f"Deleted {len(to_delete)} shows.")


if __name__ == "__main__":
    main()
