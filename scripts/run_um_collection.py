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

from scripts.common import (  # type: ignore  # noqa: E402
    ensure_source_reachable,
    write_github_output,
)
from src.jambandnerd.config.bands import get_collection_policy  # noqa: E402
from src.jambandnerd.data_collection.um.collector import UmCollector  # noqa: E402
from src.jambandnerd.data_collection.um.normalizer import (  # noqa: E402
    normalize_setlists,
)
from src.jambandnerd.data_collection.um.upcoming import (  # noqa: E402
    UpcomingShowsError,
    collect_upcoming_shows,
)
from src.jambandnerd.data_collection.utils import (  # noqa: E402
    CollectionTimer,
    attach_source_hash_column,
)
from src.jambandnerd.db.operations import (  # noqa: E402
    dedupe_dataframe_on_conflict,
    fetch_existing_values,
    fetch_last_collection_timestamp,
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
    upcoming_df = attach_source_hash_column(upcoming_df)
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


def _emit_github_output(**kwargs: str) -> None:
    """Write key=value pairs to GITHUB_OUTPUT if available."""
    for key, value in kwargs.items():
        write_github_output(key, value)


def run_um_collection(
    *,
    skip_validation: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    full_backfill: bool = False,
    incremental: bool = True,
) -> None:
    """Run the Umphrey's McGee data collection workflow.

    Args:
        skip_validation: Skip Supabase schema validation before upserting.
        start_date: Earliest show date to collect (YYYY-MM-DD).
        end_date: Latest show date to collect (YYYY-MM-DD).
        full_backfill: Re-fetch setlists for all shows regardless of existing rows.
        incremental: Use timestamp-based incremental collection (default: True).
    """
    timer = CollectionTimer()

    print("Starting Umphrey's McGee data collection...")
    try:
        ensure_source_reachable("um")
    except RuntimeError as exc:
        _emit_github_output(
            workflow_state="degraded",
            outcome_code="degraded_upstream_blocked",
            should_retry_collection="false",
            recent_data_usable="true",
            prediction_action="reused_existing",
            failure_reason=str(exc),
        )
        raise
    collector = UmCollector()

    # Determine collection mode
    use_incremental = incremental and not full_backfill
    since_timestamp = None

    if use_incremental:
        from jambandnerd.db.connection import get_supabase_client

        client = get_supabase_client()
        since_timestamp = fetch_last_collection_timestamp("um", client=client)
        if since_timestamp:
            print(f"Using incremental mode (since: {since_timestamp.isoformat()})")
        else:
            print("No previous collection found, falling back to full window mode")
            use_incremental = False

    # Songs -----------------------------------------------------------------
    if use_incremental and since_timestamp:
        songs_data = collector.collect_songs_incremental(since_timestamp)
    else:
        songs_data = collector.collect_songs()

    if songs_data:
        songs_df = pd.DataFrame(songs_data)
        songs_df = songs_df.drop_duplicates(subset=["song_id"]).reset_index(drop=True)
        songs_df = attach_source_hash_column(songs_df)
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
    # Venues don't have timestamp fields, so always do full fetch (small dataset)
    venues_data = collector.collect_venues()
    if venues_data:
        venues_df = pd.DataFrame(venues_data)
        venues_df = attach_source_hash_column(venues_df)
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

    if use_incremental and since_timestamp:
        # Incremental mode: use timestamp + optional date range
        shows_data = collector.collect_shows_incremental(
            since_timestamp, start_date=start_dt, end_date=end_dt
        )
    else:
        # Window mode: use date range only
        if not full_backfill:
            today = date.today()
            if start_dt is None:
                # Use rolling window from collection policy (default: 90 days)
                policy = get_collection_policy("um")
                window_days = policy.rolling_window_days or 90
                start_dt = max(
                    today - timedelta(days=window_days),
                    date(collector.EARLIEST_YEAR, 1, 1),
                )
            if end_dt is None or end_dt < today:
                end_dt = today + timedelta(days=90)

        shows_data = collector.collect_shows(start_date=start_dt, end_date=end_dt)

    if not shows_data:
        print("No UM shows returned by API; skipping show upsert.")
        _finish_collection(timer, skip_validation=skip_validation)
        return

    shows_df = pd.DataFrame(shows_data)
    shows_df = attach_source_hash_column(shows_df)
    _upsert(
        "um_shows_raw",
        shows_df,
        conflict_columns=["show_id"],
        skip_validation=skip_validation,
    )
    print(f"Upserted {len(shows_df)} shows into um_shows_raw.")

    # Setlists -------------------------------------------------------------
    if use_incremental and since_timestamp:
        # Incremental: fetch setlists updated since timestamp
        print(
            f"Collecting setlists incrementally since {since_timestamp.isoformat()}..."
        )
        setlists_data = collector.collect_setlists_incremental(
            since_timestamp, shows_to_process=shows_data
        )
    elif full_backfill:
        shows_to_process = shows_data
        print(f"Collecting setlists for {len(shows_to_process)} shows...")
        setlists_data = collector.collect_setlists(shows_to_process)
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
            print(
                "All UM setlists already ingested; no additional collection required."
            )
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
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="Disable incremental collection (force full window refresh).",
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
        incremental=not args.no_incremental,
    )


if __name__ == "__main__":
    main()
