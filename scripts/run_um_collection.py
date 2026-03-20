"""Runs the Umphrey's McGee data collection pipeline.

This script coordinates the `UmCollector` to scrape songs, venues, shows,
and setlists from allthings.umphreys.com, normalizes the results, and upserts
them into the Supabase raw tables (`um_*_raw`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
from src.jambandnerd.data_collection.um.upcoming import (  # noqa: E402
    UpcomingShowsError,
    collect_upcoming_shows,
)
from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.db.operations import validate_and_upsert_dataframe  # noqa: E402


def _hash_row(record: Dict[str, Any]) -> str:
    """Compute a deterministic hash for a record, handling NaN values."""

    cleaned = {}
    for key, value in record.items():
        if value is None:
            cleaned[key] = None
            continue
        try:
            if pd.isna(value):
                cleaned[key] = None
                continue
        except TypeError:
            pass
        cleaned[key] = value

    payload = json.dumps(
        cleaned, sort_keys=True, ensure_ascii=False, default=str
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
    validate_and_upsert_dataframe(
        table_name=table_name,
        df=df,
        conflict_columns=list(conflict_columns),
        required_columns=required_columns,
        skip_validation=skip_validation,
    )


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


def _load_existing_setlist_ids(show_ids: Sequence[Any]) -> set[str]:
    if not show_ids:
        return set()

    client = get_supabase_client()
    existing: set[str] = set()
    unique_ids = list(dict.fromkeys(show_ids))
    for chunk in _batched(unique_ids, 50):
        try:
            resp = (
                client.table("um_setlists_raw")
                .select("show_id")
                .in_("show_id", list(chunk))
                .execute()
            )
        except Exception as exc:  # pragma: no cover - Supabase connectivity
            print(f"Warning: could not lookup existing UM setlist IDs ({exc}).")
            continue
        for item in resp.data or []:
            show_id = item.get("show_id")
            if show_id is not None:
                existing.add(str(show_id))
    return existing


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
        existing_ids = _load_existing_setlist_ids(show_id_map.values())
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


def _compute_source_hash(df: pd.DataFrame) -> pd.DataFrame:
    """Attach source hash column to a DataFrame."""

    if df.empty:
        return df
    df = df.copy()
    df = df.where(pd.notnull(df), None)
    df["source_hash"] = df.apply(lambda row: _hash_row(row.to_dict()), axis=1)
    return df


def run_um_collection(
    *,
    skip_validation: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    full_backfill: bool = False,
) -> None:
    """Run the Umphrey's McGee data collection workflow."""

    print("Starting Umphrey's McGee data collection...")
    ensure_source_reachable("um")
    collector = UmCollector()

    # Songs -----------------------------------------------------------------
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = pd.DataFrame(songs_data)
        songs_df = songs_df.drop_duplicates(subset=["song_name"]).reset_index(drop=True)
        songs_df = _compute_source_hash(songs_df)
        _upsert(
            "um_songs_raw",
            songs_df,
            conflict_columns=["song_name"],
            skip_validation=skip_validation,
        )
        print(f"Upserted {len(songs_df)} songs into um_songs_raw.")
    else:
        print("No UM songs scraped; skipping um_songs_raw upsert.")

    # Venues ----------------------------------------------------------------
    venues_data = collector.collect_venues()
    if venues_data:
        venues_df = pd.DataFrame(venues_data)
        venues_df = _compute_source_hash(venues_df)
        _upsert(
            "um_venues_raw",
            venues_df,
            conflict_columns=[
                "venue_name",
                "venue_city",
                "venue_state",
                "venue_country",
            ],
            skip_validation=skip_validation,
        )
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
    shows_df = _compute_source_hash(shows_df)
    _upsert(
        "um_shows_raw",
        shows_df,
        conflict_columns=["source_url"],
        skip_validation=skip_validation,
    )
    print(f"Upserted {len(shows_df)} shows into um_shows_raw.")

    shows_to_process = _shows_to_process(shows_df, full_backfill=full_backfill)
    if not shows_to_process:
        print("All UM setlists already ingested; no additional scraping required.")
        return

    setlists_data = collector.collect_setlists(shows_to_process)
    if not setlists_data:
        print("No UM setlists scraped.")
        return

    setlists_df = pd.DataFrame(setlists_data)

    # Normalize numeric/boolean columns
    numeric_columns = {
        "set_sequence": "Int64",
        "song_position": "Int64",
        "show_position": "Int64",
    }
    for column, dtype in numeric_columns.items():
        if column in setlists_df.columns:
            setlists_df[column] = pd.to_numeric(
                setlists_df[column], errors="coerce"
            ).astype(dtype)

    bool_columns = ["is_segue", "encore"]
    for column in bool_columns:
        if column in setlists_df.columns:
            setlists_df[column] = setlists_df[column].fillna(False).astype(bool)

    if "set_label" in setlists_df.columns and "set_number" not in setlists_df.columns:
        setlists_df["set_number"] = setlists_df["set_label"].fillna("").astype(str)

    setlists_df = _compute_source_hash(setlists_df)
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
            upcoming_df = _compute_source_hash(upcoming_df)
            _upsert(
                "um_upcoming_shows",
                upcoming_df,
                conflict_columns=["source_uuid"],
                skip_validation=skip_validation,
            )
            print(f"Upserted {len(upcoming_df)} upcoming shows into um_upcoming_shows.")
        else:
            print("No upcoming UM shows found from Seated API.")


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
