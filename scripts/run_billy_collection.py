"""Runs the Billy Strings data collection pipeline.

This script mirrors the goose/wsp collectors by normalizing scraped data and
persisting it into the Supabase raw tables. It focuses on shows and setlists,
with placeholders for songs/venues should bmfsdb.com expose richer endpoints
in the future.
"""

from __future__ import annotations

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import argparse
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from scripts.common import ensure_source_reachable
from src.jambandnerd.data_collection.billy.collector import BillyCollector
from src.jambandnerd.data_collection.billy.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
)
from src.jambandnerd.data_collection.utils import CollectionTimer
from src.jambandnerd.db.operations import (
    fetch_existing_values,
    fetch_rows_by_column_values,
    validate_and_upsert_dataframe,
)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date '{date_str}'. Use YYYY-MM-DD.")


def run_billy_collection(
    skip_validation: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip_existing_setlists: bool = True,
    full_backfill: bool = False,
    skip_setlists: bool = False,
) -> None:
    print("Starting Billy Strings data collection...")
    timer = CollectionTimer()
    ensure_source_reachable("billy")

    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date)

    env_start = os.getenv("BILLY_START_DATE")
    if start_dt is None and env_start:
        try:
            start_dt = datetime.strptime(env_start, "%Y-%m-%d").date()
            print(f"Using BILLY_START_DATE override: {start_dt.isoformat()}")
        except ValueError:
            print(f"Warning: invalid BILLY_START_DATE '{env_start}', ignoring.")

    if not full_backfill and start_dt is None:
        today = date.today()
        start_dt = today - timedelta(days=60)
        print(
            "Defaulting to show collection window starting "
            f"{start_dt.isoformat()} (use --full-backfill or BILLY_START_DATE for overrides)."
        )

    collector = BillyCollector()

    # Songs
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = normalize_songs(songs_data)
        validate_and_upsert_dataframe(
            "billy_songs_raw",
            songs_df,
            ["song_name"],
            skip_validation=skip_validation,
        )
        print(f"Upserted {len(songs_df)} songs into billy_songs_raw.")
    else:
        print("No Billy Strings songs scraped; skipping billy_songs_raw upsert.")

    # Shows
    shows_data = collector.collect_shows(start_date=start_dt, end_date=end_dt)
    if shows_data:
        shows_df = normalize_shows(shows_data)
        validate_and_upsert_dataframe(
            "billy_shows_raw",
            shows_df,
            ["source_uuid"],
            skip_validation=skip_validation,
        )
        print(f"Upserted {len(shows_df)} shows into billy_shows_raw.")
    else:
        print("No Billy Strings shows scraped; skipping show upsert.")

    shows_from_db: List[Dict[str, Any]] = []
    try:
        source_uuids = [
            show.get("source_uuid")
            for show in shows_data
            if show.get("source_uuid") is not None
        ]
        shows_from_db = fetch_rows_by_column_values(
            "billy_shows_raw",
            select_columns=["show_id", "source_uuid", "source_url", "show_date"],
            filter_column="source_uuid",
            values=source_uuids,
        )
    except Exception as exc:  # pragma: no cover - supabase connectivity
        print(f"Warning: could not fetch billy_shows_raw from database ({exc}).")

    show_lookup = {
        row.get("source_uuid"): row for row in shows_from_db if row.get("source_uuid")
    }
    shows_requiring_setlists: List[Dict[str, Any]] = []

    for show in shows_data:
        uuid = show.get("source_uuid")
        if uuid and uuid in show_lookup:
            shows_requiring_setlists.append(show_lookup[uuid])

    if skip_setlists:
        print("Skipping Billy Strings setlist collection step.")
        timer.log("billy")
        return

    if not shows_requiring_setlists:
        print(
            "No Billy Strings shows with database IDs available for setlist scraping."
        )
        timer.log("billy")
        return

    existing_setlist_show_ids: set[str] = set()
    if skip_existing_setlists:
        try:
            candidate_show_ids = [
                row.get("show_id")
                for row in shows_requiring_setlists
                if row.get("show_id") is not None
            ]
            existing_setlist_show_ids = fetch_existing_values(
                "billy_setlists_raw",
                value_column="show_id",
                candidate_values=candidate_show_ids,
            )
        except Exception as exc:  # pragma: no cover - supabase connectivity
            print(f"Warning: could not load existing Billy setlist show IDs ({exc}).")

    shows_to_process = [
        {
            "show_id": row.get("show_id"),
            "source_url": row.get("source_url"),
            "source_uuid": row.get("source_uuid"),
            "show_date": row.get("show_date"),
        }
        for row in shows_requiring_setlists
        if str(row.get("show_id")) not in existing_setlist_show_ids
    ]

    if not shows_to_process:
        print("All Billy Strings shows already have setlists; nothing to scrape.")
        timer.log("billy")
        return

    setlists_data = collector.collect_setlists(shows_to_process)
    setlists_df = normalize_setlists(setlists_data)
    if setlists_df.empty:
        print("No valid Billy Strings setlist rows after normalization.")
        timer.log("billy")
        return

    validate_and_upsert_dataframe(
        "billy_setlists_raw",
        setlists_df,
        ["show_id", "set_number", "song_position"],
        required_columns=["set_number", "song_position"],
        skip_validation=skip_validation,
    )
    print(f"Upserted {len(setlists_df)} rows into billy_setlists_raw.")

    timer.log("billy")


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Billy Strings data collection with optional schema validation"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Bypass schema validation before upserts",
    )
    parser.add_argument(
        "--start-date", help="Limit show scraping to dates on/after YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", help="Limit show scraping to dates on/before YYYY-MM-DD"
    )
    parser.add_argument(
        "--skip-setlists", action="store_true", help="Skip the setlist collection step"
    )
    parser.add_argument(
        "--full-backfill",
        action="store_true",
        help="Scrape the full show history (overrides the default rolling window)",
    )
    return parser


def main() -> None:
    parser = _build_cli()
    args = parser.parse_args()
    run_billy_collection(
        skip_validation=args.skip_validation,
        start_date=args.start_date,
        end_date=args.end_date,
        full_backfill=args.full_backfill,
        skip_setlists=args.skip_setlists,
    )


if __name__ == "__main__":
    main()
