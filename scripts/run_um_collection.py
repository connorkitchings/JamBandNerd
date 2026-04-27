"""Runs the Umphrey's McGee data collection pipeline.

This script coordinates the `UmCollector` to fetch songs, venues, shows,
and setlists from allthings.umphreys.com, normalizes the results, and upserts
them into the Supabase raw tables (`um_*_raw`).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from typing import Optional, Sequence

import pandas as pd

# Ensure project root is on sys.path when executed as a script
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.common import ensure_source_reachable  # type: ignore  # noqa: E402
from src.jambandnerd.data_collection.um.collector import UmCollector  # noqa: E402
from src.jambandnerd.data_collection.um.normalizer import (  # noqa: E402
    attach_source_hash,
    normalize_setlists,
)
from src.jambandnerd.data_collection.um.upcoming import (  # noqa: E402
    UpcomingShowsError,
    collect_upcoming_shows,
)
from src.jambandnerd.data_collection.utils import CollectionTimer  # noqa: E402
from src.jambandnerd.db.operations import (  # noqa: E402
    dedupe_dataframe_on_conflict,
    fetch_existing_values,
    validate_and_upsert_dataframe,
)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD."
        ) from exc


def _upsert(
    table_name: str,
    df: pd.DataFrame,
    conflict_columns: Sequence[str],
    *,
    skip_validation: bool,
    required_columns: Sequence[str] | None = None,
) -> None:
    """Normalize and upsert a DataFrame."""

    if df.empty:
        return
    deduped = dedupe_dataframe_on_conflict(
        df,
        conflict_columns=conflict_columns,
        table_name=table_name,
    )
    validate_and_upsert_dataframe(
        table_name=table_name,
        df=deduped,
        conflict_columns=list(conflict_columns),
        required_columns=required_columns,
        skip_validation=skip_validation,
    )


def _refresh_upcoming_shows(*, skip_validation: bool) -> None:
    """Refresh UM upcoming-show support data."""
    try:
        upcoming_records = collect_upcoming_shows()
    except UpcomingShowsError as exc:
        print(f"Warning: could not fetch upcoming UM shows ({exc}).")
        return

    if not upcoming_records:
        print("No upcoming UM shows found from Seated API.")
        return

    upcoming_df = pd.DataFrame(upcoming_records)
    upcoming_df = attach_source_hash(upcoming_df)
    _upsert(
        "um_upcoming_shows",
        upcoming_df,
        conflict_columns=["source_uuid"],
        skip_validation=skip_validation,
    )
    print(f"Upserted {len(upcoming_df)} upcoming shows into um_upcoming_shows.")


def _finish_collection(timer: CollectionTimer, *, skip_validation: bool) -> None:
    _refresh_upcoming_shows(skip_validation=skip_validation)
    timer.log("um")
    print("UM collection complete.")


def run_um_collection(
    *,
    skip_validation: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    full_backfill: bool = False,
) -> None:
    """Run the Umphrey's McGee data collection workflow."""
    timer = CollectionTimer()

    print("Starting Umphrey's McGee data collection...")
    ensure_source_reachable("um")
    collector = UmCollector()

    # Songs -----------------------------------------------------------------
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = pd.DataFrame(songs_data)
        songs_df = songs_df.drop_duplicates(subset=["song_id"]).reset_index(drop=True)
        songs_df = attach_source_hash(songs_df)
        _upsert(
            "um_songs_raw",
            songs_df,
            conflict_columns=["song_id"],
            skip_validation=skip_validation,
        )
        print(f"Upserted {len(songs_df)} songs into um_songs_raw.")
    else:
        print("No UM songs returned by API; skipping um_songs_raw upsert.")

    # Venues ----------------------------------------------------------------
    venues_data = collector.collect_venues()
    if venues_data:
        venues_df = pd.DataFrame(venues_data)
        venues_df = attach_source_hash(venues_df)
        _upsert(
            "um_venues_raw",
            venues_df,
            conflict_columns=["venue_id"],
            skip_validation=skip_validation,
        )
        print(f"Upserted {len(venues_df)} venues into um_venues_raw.")
    else:
        print("No UM venues returned by API; skipping um_venues_raw upsert.")

    # Shows -----------------------------------------------------------------
    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date)
    if not full_backfill:
        today = date.today()
        if start_dt is None:
            start_dt = max(
                today - timedelta(days=730), date(collector.EARLIEST_YEAR, 1, 1)
            )
        if end_dt is None or end_dt < today:
            end_dt = today + timedelta(days=90)

    shows_data = collector.collect_shows(start_date=start_dt, end_date=end_dt)
    if not shows_data:
        print("No UM shows returned by API; skipping show upsert.")
        _finish_collection(timer, skip_validation=skip_validation)
        return

    shows_df = pd.DataFrame(shows_data)
    shows_df = attach_source_hash(shows_df)
    _upsert(
        "um_shows_raw",
        shows_df,
        conflict_columns=["show_id"],
        skip_validation=skip_validation,
    )
    print(f"Upserted {len(shows_df)} shows into um_shows_raw.")

    if full_backfill:
        shows_to_process = shows_data
    else:
        # Determine which shows still require setlist collection
        candidate_ids = [str(s["show_id"]) for s in shows_data]
        existing_ids = fetch_existing_values(
            "um_setlists_raw",
            value_column="show_id",
            candidate_values=candidate_ids,
        )
        shows_to_process = [
            s for s in shows_data if str(s["show_id"]) not in existing_ids
        ]

    if not shows_to_process:
        print("All UM setlists already ingested; no additional collection required.")
        _finish_collection(timer, skip_validation=skip_validation)
        return

    print(f"Collecting setlists for {len(shows_to_process)} shows...")
    setlists_data = collector.collect_setlists(shows_to_process)
    if not setlists_data:
        print("No UM setlists collected.")
        _finish_collection(timer, skip_validation=skip_validation)
        return

    setlists_df = normalize_setlists(pd.DataFrame(setlists_data))
    _upsert(
        "um_setlists_raw",
        setlists_df,
        conflict_columns=["show_id", "show_position"],
        skip_validation=skip_validation,
    )
    print(f"Upserted {len(setlists_df)} setlist rows into um_setlists_raw.")

    _finish_collection(timer, skip_validation=skip_validation)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Umphrey's McGee API pipeline."
    )
    parser.add_argument(
        "--start-date",
        help="Earliest show date to collect (YYYY-MM-DD). Defaults to earliest known show.",
    )
    parser.add_argument(
        "--end-date",
        help="Latest show date to collect (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Supabase schema validation before upserting.",
    )
    parser.add_argument(
        "--full-backfill",
        action="store_true",
        help="Re-fetch setlists for all shows regardless of existing rows.",
    )
    return parser


def main() -> None:
    parser = _build_argument_parser()
    args = parser.parse_args()
    run_um_collection(
        skip_validation=args.skip_validation,
        start_date=args.start_date,
        end_date=args.end_date,
        full_backfill=args.full_backfill,
    )


if __name__ == "__main__":
    main()
