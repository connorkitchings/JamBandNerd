#!/usr/bin/env python3
"""
Efficiently determines the date of the most recently completed show for a given band.
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.db.connection import get_supabase_client


def get_last_completed_show_date(band: str) -> str | None:
    client = get_supabase_client()
    shows_tbl = f"{band}_shows_raw"
    sets_tbl = f"{band}_setlists_raw"
    id_col = "api_show_id" if band == "phish" else "show_id"
    date_col = "show_date"

    try:
        # 1. Get the most recent 100 shows from the database.
        recent_shows_resp = (
            client.table(shows_tbl)
            .select(f"{id_col}, {date_col}")
            .order(date_col, desc=True)
            .limit(100)
            .execute()
        )
        if not recent_shows_resp.data:
            print(f"Warning: No shows found for band '{band}'.", file=sys.stderr)
            return None

        recent_shows = pd.DataFrame(recent_shows_resp.data)
        recent_show_ids = recent_shows[id_col].astype(str).tolist()

        # 2. Find which of those recent shows have setlists.
        setlists_resp = (
            client.table(sets_tbl).select(id_col).in_(id_col, recent_show_ids).execute()
        )
        if not setlists_resp.data:
            print(
                f"Warning: No setlists found for the last 100 shows of band '{band}'.",
                file=sys.stderr,
            )
            return None

        completed_recent_show_ids = {
            str(row[id_col]) for row in setlists_resp.data if row.get(id_col)
        }

        if not completed_recent_show_ids:
            print(
                f"Warning: No completed shows found among the most recent 100 for band '{band}'.",
                file=sys.stderr,
            )
            return None

        # 3. From the original list of recent shows, filter to the ones that are completed.
        completed_shows = recent_shows[
            recent_shows[id_col].astype(str).isin(completed_recent_show_ids)
        ]

        # 4. The most recent date from this filtered list is our answer.
        last_date = pd.to_datetime(completed_shows[date_col]).max().date()
        return str(last_date)

    except Exception as e:
        print(
            f"An error occurred while fetching the last completed show date for '{band}': {e}",
            file=sys.stderr,
        )
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Get the date of the most recently completed show for a band."
    )
    parser.add_argument(
        "--band",
        required=True,
        choices=list(get_active_bands()),
        help="The band's slug.",
    )
    args = parser.parse_args()
    last_date = get_last_completed_show_date(args.band)
    if last_date:
        print(last_date)
