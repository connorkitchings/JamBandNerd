"""Runs the Umphrey's McGee data collection pipeline.

This script coordinates the `UmCollector` to scrape songs, venues, shows,
and setlists from allthings.umphreys.com, normalizes the results, and upserts
them into the Supabase raw tables (`um_*_raw`).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

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
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.db.operations import (  # noqa: E402
    bulk_insert_dataframe,
    dedupe_dataframe_on_conflict,
    fetch_existing_values,
    fetch_rows_by_column_values,
    prepare_dataframe_for_upsert,
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


def _sync_um_songs_raw(songs_df: pd.DataFrame, *, skip_validation: bool) -> None:
    """Persist UM songs when production uses a generated song_id primary key."""

    if songs_df.empty:
        return

    deduped = dedupe_dataframe_on_conflict(
        songs_df,
        conflict_columns=["song_name"],
        table_name="um_songs_raw",
    )
    prepared = prepare_dataframe_for_upsert(
        "um_songs_raw",
        deduped,
        skip_validation=skip_validation,
    )
    if prepared.empty:
        return

    song_names = prepared["song_name"].dropna().astype(str).tolist()
    existing_names = fetch_existing_values(
        "um_songs_raw",
        value_column="song_name",
        candidate_values=song_names,
    )

    existing_df = prepared[prepared["song_name"].astype(str).isin(existing_names)]
    new_df = prepared[~prepared["song_name"].astype(str).isin(existing_names)]

    if not existing_df.empty:
        client = get_supabase_client()
        for record in existing_df.to_dict(orient="records"):
            record = {
                key: None if pd.isna(value) else value for key, value in record.items()
            }
            song_name = record.get("song_name")
            if song_name is None:
                continue
            client.table("um_songs_raw").update(record).eq(
                "song_name", str(song_name)
            ).execute()

    if not new_df.empty:
        next_song_id = _next_um_song_id()
        new_df = new_df.copy()
        new_df["song_id"] = range(next_song_id, next_song_id + len(new_df))
        bulk_insert_dataframe("um_songs_raw", new_df)


def _next_um_song_id() -> int:
    """Return the next available UM song_id for schemas without identity defaults."""

    return _next_numeric_id("um_songs_raw", "song_id")


def _venue_key(record: Dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(record.get("venue_name") or ""),
        str(record.get("venue_city") or ""),
        str(record.get("venue_state") or ""),
        str(record.get("venue_country") or ""),
    )


def _sync_um_venues_raw(venues_df: pd.DataFrame, *, skip_validation: bool) -> None:
    """Persist UM venues when production uses a generated venue_id primary key."""

    if venues_df.empty:
        return

    deduped = dedupe_dataframe_on_conflict(
        venues_df,
        conflict_columns=[
            "venue_name",
            "venue_city",
            "venue_state",
            "venue_country",
        ],
        table_name="um_venues_raw",
    ).copy()
    venue_names = deduped["venue_name"].dropna().astype(str).tolist()
    existing_rows = fetch_rows_by_column_values(
        "um_venues_raw",
        select_columns=[
            "venue_id",
            "venue_name",
            "venue_city",
            "venue_state",
            "venue_country",
        ],
        filter_column="venue_name",
        values=venue_names,
    )
    existing_ids = {_venue_key(row): int(row["venue_id"]) for row in existing_rows}

    next_venue_id = _next_numeric_id("um_venues_raw", "venue_id")
    venue_ids: list[int] = []
    is_existing: list[bool] = []
    for record in deduped.to_dict(orient="records"):
        existing_id = existing_ids.get(_venue_key(record))
        if existing_id is not None:
            venue_ids.append(existing_id)
            is_existing.append(True)
        else:
            venue_ids.append(next_venue_id)
            next_venue_id += 1
            is_existing.append(False)

    deduped["venue_id"] = venue_ids
    deduped["_is_existing"] = is_existing
    prepared = prepare_dataframe_for_upsert(
        "um_venues_raw",
        deduped,
        skip_validation=skip_validation,
    )
    existing_df = prepared[deduped["_is_existing"].to_numpy()]
    new_df = prepared[~deduped["_is_existing"].to_numpy()]

    if not existing_df.empty:
        client = get_supabase_client()
        for record in existing_df.to_dict(orient="records"):
            record = {
                key: None if pd.isna(value) else value for key, value in record.items()
            }
            client.table("um_venues_raw").update(record).eq(
                "venue_id", record["venue_id"]
            ).execute()

    if not new_df.empty:
        bulk_insert_dataframe("um_venues_raw", new_df)


def _sync_um_shows_raw(shows_df: pd.DataFrame, *, skip_validation: bool) -> None:
    """Persist UM shows when production uses a generated show_id primary key."""

    if shows_df.empty:
        return

    deduped = dedupe_dataframe_on_conflict(
        shows_df,
        conflict_columns=["source_url"],
        table_name="um_shows_raw",
    ).copy()
    source_urls = deduped["source_url"].dropna().astype(str).tolist()
    existing_rows = fetch_rows_by_column_values(
        "um_shows_raw",
        select_columns=["show_id", "source_url"],
        filter_column="source_url",
        values=source_urls,
    )
    existing_ids = {
        str(row["source_url"]): int(row["show_id"])
        for row in existing_rows
        if row.get("source_url") and row.get("show_id") is not None
    }

    next_show_id = _next_numeric_id("um_shows_raw", "show_id")
    show_ids: list[int] = []
    is_existing: list[bool] = []
    for source_url in source_urls:
        existing_id = existing_ids.get(str(source_url))
        if existing_id is not None:
            show_ids.append(existing_id)
            is_existing.append(True)
        else:
            show_ids.append(next_show_id)
            next_show_id += 1
            is_existing.append(False)

    deduped["show_id"] = show_ids
    deduped["_is_existing"] = is_existing
    prepared = prepare_dataframe_for_upsert(
        "um_shows_raw",
        deduped,
        skip_validation=skip_validation,
    )
    existing_df = prepared[deduped["_is_existing"].to_numpy()]
    new_df = prepared[~deduped["_is_existing"].to_numpy()]

    if not existing_df.empty:
        client = get_supabase_client()
        for record in existing_df.to_dict(orient="records"):
            record = {
                key: None if pd.isna(value) else value for key, value in record.items()
            }
            client.table("um_shows_raw").update(record).eq(
                "show_id", record["show_id"]
            ).execute()

    if not new_df.empty:
        bulk_insert_dataframe("um_shows_raw", new_df)


def _next_numeric_id(table_name: str, id_column: str) -> int:
    """Return the next available integer ID for schemas without identity defaults."""

    client = get_supabase_client()
    response = (
        client.table(table_name)
        .select(id_column)
        .order(id_column, desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows or rows[0].get(id_column) is None:
        return 1
    return int(rows[0][id_column]) + 1


def _batched(sequence: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(sequence), size):
        yield sequence[start : start + size]


def _fetch_show_id_map(source_urls: Sequence[str]) -> Dict[str, Any]:
    if not source_urls:
        return {}

    client = get_supabase_client()
    mapping: Dict[str, Any] = {}
    for chunk in _batched(list(dict.fromkeys(source_urls)), 50):
        try:
            resp = (
                client.table("um_shows_raw")
                .select("show_id, source_url")
                .in_("source_url", list(chunk))
                .execute()
            )
        except Exception as exc:  # pragma: no cover - Supabase connectivity
            print(f"Warning: could not lookup UM show IDs ({exc}).")
            continue
        for item in resp.data or []:
            source_url = item.get("source_url")
            show_id = item.get("show_id")
            if source_url and show_id is not None:
                mapping[str(source_url)] = show_id
    return mapping


def _shows_to_process(
    shows_df: pd.DataFrame, *, full_backfill: bool
) -> List[Dict[str, Any]]:
    """Determine which shows still require setlist scraping."""

    if shows_df.empty:
        return []

    if "source_url" not in shows_df.columns:
        return []

    source_urls = shows_df["source_url"].dropna().astype(str).unique().tolist()
    if not source_urls:
        return []

    show_id_map = _fetch_show_id_map(source_urls)
    if not show_id_map:
        print("Warning: could not resolve UM show IDs for scraped shows.")
        return []

    pending_show_ids: set[str]
    if full_backfill:
        pending_show_ids = {str(show_id) for show_id in show_id_map.values()}
    else:
        existing_ids = fetch_existing_values(
            "um_setlists_raw",
            value_column="show_id",
            candidate_values=[str(sid) for sid in show_id_map.values()],
        )
        pending_show_ids = {
            str(show_id)
            for show_id in show_id_map.values()
            if str(show_id) not in existing_ids
        }

    print(
        f"UM shows pending setlist scrape: {len(pending_show_ids)}/{len(show_id_map)}"
    )

    shows: List[Dict[str, Any]] = []
    for source_url in source_urls:
        show_id = show_id_map.get(source_url)
        if show_id is None:
            continue
        if not full_backfill and str(show_id) not in pending_show_ids:
            continue
        shows.append({"show_id": show_id, "source_url": source_url})
    return shows


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
        songs_df = songs_df.drop_duplicates(subset=["song_name"]).reset_index(drop=True)
        songs_df = attach_source_hash(songs_df)
        _sync_um_songs_raw(songs_df, skip_validation=skip_validation)
        print(f"Upserted {len(songs_df)} songs into um_songs_raw.")
    else:
        print("No UM songs scraped; skipping um_songs_raw upsert.")

    # Venues ----------------------------------------------------------------
    venues_data = collector.collect_venues()
    if venues_data:
        venues_df = pd.DataFrame(venues_data)
        venues_df = attach_source_hash(venues_df)
        _sync_um_venues_raw(venues_df, skip_validation=skip_validation)
        print(f"Upserted {len(venues_df)} venues into um_venues_raw.")
    else:
        print("No UM venues scraped; skipping um_venues_raw upsert.")

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
        print("No UM shows scraped; skipping show upsert.")
        return

    shows_df = pd.DataFrame(shows_data)
    shows_df = attach_source_hash(shows_df)
    _sync_um_shows_raw(shows_df, skip_validation=skip_validation)
    print(f"Upserted {len(shows_df)} shows into um_shows_raw.")

    shows_to_process = _shows_to_process(shows_df, full_backfill=full_backfill)
    if not shows_to_process:
        print("All UM setlists already ingested; no additional scraping required.")
        return

    setlists_data = collector.collect_setlists(shows_to_process)
    if not setlists_data:
        print("No UM setlists scraped.")
        return

    setlists_df = normalize_setlists(pd.DataFrame(setlists_data))
    _upsert(
        "um_setlists_raw",
        setlists_df,
        conflict_columns=["show_id", "show_position"],
        skip_validation=skip_validation,
        required_columns=["set_number", "song_position"],
    )
    print(f"Upserted {len(setlists_df)} setlist rows into um_setlists_raw.")

    # Upcoming shows from Seated widget
    try:
        upcoming_records = collect_upcoming_shows()
    except UpcomingShowsError as exc:
        print(f"Warning: could not fetch upcoming UM shows ({exc}).")
    else:
        if upcoming_records:
            upcoming_df = pd.DataFrame(upcoming_records)
            upcoming_df = attach_source_hash(upcoming_df)
            _upsert(
                "um_upcoming_shows",
                upcoming_df,
                conflict_columns=["source_uuid"],
                skip_validation=skip_validation,
            )
            print(f"Upserted {len(upcoming_df)} upcoming shows into um_upcoming_shows.")
        else:
            print("No upcoming UM shows found from Seated API.")

    timer.log("um")
    print("UM collection complete.")


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Umphrey's McGee web scraping pipeline."
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
        help="Re-scrape setlists for all shows regardless of existing rows.",
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
