"""Delete duplicate rows from um_shows_raw created by the /setlists/ URL change.

Two groups are removed (deleting a show cascades to um_setlists_raw):
  ghost: a 0-song show whose same-date sibling has >= 3 songs.
  pair:  two shows sharing a normalised URL with identical song sets; the row
         whose URL contains ``/setlists/`` is kept.
Candidates referenced by ``setlist_accuracy.show_id`` are skipped and reported,
unless ``--delete-referenced-pairs`` is given: then referenced *pair* rows are
deleted along with their accuracy rows (rebuilt by a later forced re-score).
Referenced ghosts are always skipped.
``--delete-ids a,b`` deletes exactly those shows (and their accuracy rows) for
duplicates the rules above cannot pick; naming an id is the consent. Each id
must exist and have a same-date, same-venue sibling that is not also listed.
Dry run by default; with ``--apply`` a JSON backup of every deleted show, its
setlist rows and any deleted accuracy rows is written first.

Usage:
  uv run python scripts/admin/dedupe_um_shows.py
  uv run python scripts/admin/dedupe_um_shows.py --apply
  uv run python scripts/admin/dedupe_um_shows.py --apply --delete-referenced-pairs
  uv run python scripts/admin/dedupe_um_shows.py --delete-ids 1743900804,1773756239
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

from scripts.run_um_collection import normalize_um_show_url  # noqa: E402
from src.jambandnerd.config import SETLIST_ACCURACY_TABLE  # noqa: E402
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402

SHOWS_TABLE = "um_shows_raw"
SETLISTS_TABLE = "um_setlists_raw"
BAND = "um"
GHOST_MIN_SIBLING_SONGS = 3
PAGE_SIZE = 1000


def select_duplicate_shows(
    show_rows: list[dict[str, Any]],
    setlist_rows: list[dict[str, Any]],
    referenced_show_ids: set[str],
    delete_referenced_pairs: bool = False,
) -> dict[str, Any]:
    """Pick shows to delete.

    Returns ``{"ghost": [show_id, ...], "pair": [show_id, ...],
    "skipped": [(show_id, group), ...], "accuracy_show_ids": [str, ...]}``.
    With ``delete_referenced_pairs`` referenced pair rows are selected and listed
    in ``accuracy_show_ids`` (their accuracy rows must be deleted first);
    referenced ghosts are always skipped. Pure: no I/O.
    """
    songs: dict[Any, set[str]] = defaultdict(set)
    for row in setlist_rows:
        songs[row["show_id"]].add(str(row["song_name"]))
    shows = {row["show_id"]: row for row in show_rows}

    ghost: set[Any] = set()
    by_date: dict[Any, list[Any]] = defaultdict(list)
    for show_id, row in shows.items():
        by_date[row["show_date"]].append(show_id)
    for ids in by_date.values():
        for show_id in ids:
            if not songs[show_id] and any(
                len(songs[other]) >= GHOST_MIN_SIBLING_SONGS
                for other in ids
                if other != show_id
            ):
                ghost.add(show_id)

    pair: set[Any] = set()
    by_url: dict[str, list[Any]] = defaultdict(list)
    for show_id, row in shows.items():
        if row.get("source_url"):
            by_url[normalize_um_show_url(row["source_url"])].append(show_id)
    for ids in by_url.values():
        keepers = [i for i in ids if "/setlists/" in shows[i]["source_url"]]
        if len(ids) != 2 or len(keepers) != 1:
            continue
        loser = next(i for i in ids if i != keepers[0])
        if songs[loser] == songs[keepers[0]] and loser not in ghost:
            pair.add(loser)

    result: dict[str, Any] = {
        "ghost": [],
        "pair": [],
        "skipped": [],
        "accuracy_show_ids": [],
    }
    for group, candidates in (("ghost", ghost), ("pair", pair)):
        for show_id in sorted(candidates):
            referenced = str(show_id) in referenced_show_ids
            if referenced and not (group == "pair" and delete_referenced_pairs):
                result["skipped"].append((show_id, group))
                continue
            if referenced:
                result["accuracy_show_ids"].append(str(show_id))
            result[group].append(show_id)
    return result


def validate_delete_ids(
    show_rows: list[dict[str, Any]], delete_ids: list[str]
) -> list[str]:
    """Return ``delete_ids`` if each is safe to delete, else raise ``ValueError``.

    Safe means the show exists and a same-date, same-venue sibling survives, so
    the last row of a show is never removed. Pure: no I/O.
    """
    shows = {str(r["show_id"]): r for r in show_rows}
    listed = set(delete_ids)
    for sid in delete_ids:
        if sid not in shows:
            raise ValueError(f"show_id {sid} not found in {SHOWS_TABLE}")
        row = shows[sid]
        siblings = [
            other
            for other, r in shows.items()
            if other != sid
            and r["show_date"] == row["show_date"]
            and r.get("venue_name") == row.get("venue_name")
        ]
        if not siblings:
            raise ValueError(f"show_id {sid} has no same-date, same-venue sibling")
        if all(other in listed for other in siblings):
            raise ValueError(f"show_id {sid} and all its siblings are listed")
    return delete_ids


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
    path = backup_dir / f"dedupe_um_shows_{stamp}.json"
    payload = {**payload, "created_at": stamp}
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def delete_shows(
    client: Any,
    backup_dir: Path,
    to_delete: list[Any],
    show_rows: list[dict[str, Any]],
    setlist_rows: list[dict[str, Any]],
    accuracy_to_delete: list[dict[str, Any]],
    accuracy_ids: set[str],
) -> None:
    """Back up, then delete accuracy rows, setlist rows and shows (in that order)."""
    delete_set = set(to_delete)
    backup_path = write_backup(
        backup_dir,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="Delete rows (default is a dry run)."
    )
    parser.add_argument(
        "--delete-referenced-pairs",
        action="store_true",
        help=f"Also delete pair rows referenced by {SETLIST_ACCURACY_TABLE} "
        "(their accuracy rows are backed up and deleted first).",
    )
    parser.add_argument(
        "--delete-ids",
        type=lambda v: [i.strip() for i in v.split(",") if i.strip()],
        help="Comma-separated show_ids to delete (with their accuracy rows) "
        "instead of the automatic selection.",
    )
    parser.add_argument("--backup-dir", type=Path, default=Path("./backups"))
    args = parser.parse_args()

    client = get_supabase_client()
    show_rows = fetch_all(client, SHOWS_TABLE, "*")
    setlist_rows = fetch_all(client, SETLISTS_TABLE, "*")
    accuracy_rows = fetch_all(client, SETLIST_ACCURACY_TABLE, "*", band=BAND)
    referenced = {str(r["show_id"]) for r in accuracy_rows}
    if args.delete_ids:
        try:
            ids = validate_delete_ids(show_rows, args.delete_ids)
        except ValueError as exc:
            parser.error(str(exc))
        selected = {
            "ghost": [],
            "pair": [r["show_id"] for r in show_rows if str(r["show_id"]) in ids],
            "skipped": [],
            "accuracy_show_ids": [i for i in ids if i in referenced],
        }
    else:
        selected = select_duplicate_shows(
            show_rows, setlist_rows, referenced, args.delete_referenced_pairs
        )
    accuracy_ids = set(selected["accuracy_show_ids"])
    accuracy_to_delete = [r for r in accuracy_rows if str(r["show_id"]) in accuracy_ids]
    to_delete = selected["ghost"] + selected["pair"]
    print(
        f"ghost: {len(selected['ghost'])} | pair: {len(selected['pair'])} | "
        f"skipped (referenced by {SETLIST_ACCURACY_TABLE}): "
        f"{len(selected['skipped'])}"
    )
    for show_id, group in selected["skipped"]:
        print(f"  SKIP show_id={show_id} ({group})")
    for show_id in selected["pair"] if args.delete_ids else []:
        n_songs = sum(1 for r in setlist_rows if r["show_id"] == show_id)
        acc = [
            r.get("id") for r in accuracy_to_delete if str(r["show_id"]) == str(show_id)
        ]
        print(f"  DELETE show_id={show_id}: {n_songs} songs, accuracy ids={acc}")
    print(f"{SETLIST_ACCURACY_TABLE} rows to delete: {len(accuracy_to_delete)}")
    if not args.apply:
        print("Dry run; nothing deleted (pass --apply).")
        return
    if not to_delete:
        print("Nothing to delete.")
        return

    delete_shows(
        client,
        args.backup_dir,
        to_delete,
        show_rows,
        setlist_rows,
        accuracy_to_delete,
        accuracy_ids,
    )
    print(f"Deleted {len(to_delete)} shows.")


if __name__ == "__main__":
    main()
