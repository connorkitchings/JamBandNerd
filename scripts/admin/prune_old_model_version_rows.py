"""Remove orphaned prediction/result rows written by superseded model versions.

For each band, deletes rows whose ``model_version`` differs from the band's
current version in setlist_prediction_songs, setlist_predictions,
setlist_accuracy and setlist_results. A band is only touched when a
current-version board exists in setlist_predictions. Dry run by default; with
``--apply`` a JSON backup of every row to be deleted is written first.

Usage:
  uv run python scripts/admin/prune_old_model_version_rows.py
  uv run python scripts/admin/prune_old_model_version_rows.py --band wsp --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from src.jambandnerd.config import (  # noqa: E402
    SETLIST_ACCURACY_TABLE,
    SETLIST_PREDICTION_SONGS_TABLE,
    SETLIST_PREDICTIONS_TABLE,
    SETLIST_RESULTS_TABLE,
)
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.models.registry import (  # noqa: E402
    get_band_model_version,
    list_active_bands,
)

# Child/derived tables first so deletes never trip on dependent rows.
TABLES = (
    SETLIST_PREDICTION_SONGS_TABLE,
    SETLIST_PREDICTIONS_TABLE,
    SETLIST_ACCURACY_TABLE,
    SETLIST_RESULTS_TABLE,
)
PAGE_SIZE = 1000


def has_current_board(client: Any, band: str, model_version: str) -> bool:
    rows = (
        client.table(SETLIST_PREDICTIONS_TABLE)
        .select("id")
        .eq("band", band)
        .eq("model_version", model_version)
        .limit(1)
        .execute()
        .data
    )
    return bool(rows)


def fetch_other_version_rows(
    client: Any, table: str, band: str, model_version: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        page = (
            client.table(table)
            .select("*")
            .eq("band", band)
            .neq("model_version", model_version)
            .range(start, start + PAGE_SIZE - 1)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def write_backup(
    backup_dir: Path, band: str, model_version: str, rows_by_table: dict[str, list]
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"prune_old_model_versions_{band}_{stamp}.json"
    payload = {
        "band": band,
        "current_model_version": model_version,
        "created_at": stamp,
        "rows": rows_by_table,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def prune_band(
    client: Any, band: str, model_version: str, *, apply: bool, backup_dir: Path
) -> dict[str, int] | None:
    """Return per-table delete counts, or None when the band was skipped."""
    if not has_current_board(client, band, model_version):
        print(
            f"[{band}] SKIP: no {model_version} board in {SETLIST_PREDICTIONS_TABLE}."
        )
        return None

    rows_by_table = {
        table: fetch_other_version_rows(client, table, band, model_version)
        for table in TABLES
    }
    counts = {table: len(rows) for table, rows in rows_by_table.items()}
    print(f"[{band}] current={model_version} rows to delete before: {counts}")
    if not apply:
        print(f"[{band}] Dry run; nothing deleted (pass --apply).")
        return counts

    if any(counts.values()):
        backup_path = write_backup(backup_dir, band, model_version, rows_by_table)
        print(f"[{band}] Backup written: {backup_path}")
    for table in TABLES:
        if counts[table]:
            (
                client.table(table)
                .delete()
                .eq("band", band)
                .neq("model_version", model_version)
                .execute()
            )
    remaining = {
        table: len(fetch_other_version_rows(client, table, band, model_version))
        for table in TABLES
    }
    print(f"[{band}] other-version rows after: {remaining}")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--band", choices=list_active_bands(), default=None)
    parser.add_argument(
        "--apply", action="store_true", help="Delete rows (default is a dry run)."
    )
    parser.add_argument("--backup-dir", type=Path, default=Path("./backups"))
    args = parser.parse_args()

    client = get_supabase_client()
    for band in [args.band] if args.band else list_active_bands():
        prune_band(
            client,
            band,
            get_band_model_version(band),
            apply=args.apply,
            backup_dir=args.backup_dir,
        )


if __name__ == "__main__":
    main()
