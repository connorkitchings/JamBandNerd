#!/usr/bin/env python3
"""Wipe all Goose data from Supabase for a clean re-ingestion.

Deletes from raw tables (truncate-style) and band-filtered derived tables.

Usage:
    uv run python scripts/wipe_band_data.py --band goose
"""

from __future__ import annotations

import argparse
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.registry import list_pipeline_models

RAW_TABLE_PRIMARY_KEYS = {
    "songs_raw": "api_song_id",
    "shows_raw": "show_id",
    "venues_raw": "venue_id",
    "setlists_raw": "show_id",
}
BAND_FILTERED_TABLES = [
    "prediction_songs",
    "accuracy_per_show",
    "historical_prediction_runs",
    "collection_runs",
    "next_show_prediction_runs",
    "next_show_prediction_songs",
    "completed_show_prediction_runs",
    "completed_show_accuracy",
]


def wipe_band(band: str, dry_run: bool = False) -> None:
    client = get_supabase_client()
    prefix = f"[{band.upper()}]"

    for raw_suffix, pk_col in RAW_TABLE_PRIMARY_KEYS.items():
        table = f"{band}_{raw_suffix}"
        action = "Would delete" if dry_run else "Deleting"
        print(f"{prefix} {action} all rows from {table}...")
        if not dry_run:
            resp = client.table(table).delete().gt(pk_col, -1).execute()
            count = len(resp.data)
            if count == 0:
                resp = client.table(table).delete().lt(pk_col, 0).execute()
                count = len(resp.data)
            print(f"{prefix}   Deleted {count} rows from {table}")

    for table in BAND_FILTERED_TABLES:
        action = "Would delete" if dry_run else "Deleting"
        print(f"{prefix} {action} band={band} from {table}...")
        if not dry_run:
            resp = client.table(table).delete().eq("band", band).execute()
            print(f"{prefix}   Deleted {len(resp.data)} rows from {table}")

    models = [d.slug for d in list_pipeline_models()]
    for model in models:
        action = "Would delete" if dry_run else "Deleting"
        print(f"{prefix} {action} band={band} model={model} from predictions...")
        if not dry_run:
            resp = (
                client.table("predictions")
                .delete()
                .eq("band", band)
                .eq("model_slug", model)
                .execute()
            )
            print(f"{prefix}   Deleted {len(resp.data)} rows from predictions")

    print(f"{prefix} {'Would complete' if dry_run else 'Complete'}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wipe all data for a band from Supabase."
    )
    parser.add_argument("--band", required=True, choices=get_repo_supported_bands())
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview what would be deleted"
    )
    args = parser.parse_args()
    wipe_band(args.band, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
