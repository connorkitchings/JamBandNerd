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
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from scripts.common import assert_required_columns, ensure_source_reachable, fetch_table
from src.jambandnerd.data_collection.billy.collector import BillyCollector
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import get_table_schema, upsert_dataframe
from src.jambandnerd.db.validation import (
    coerce_df_types,
    validate_dataframe_against_table,
)


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


def _normalize_shows(raw_shows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(raw_shows)
    if df.empty:
        return df

    # Ensure required columns exist
    for column in ["venue_city", "venue_state", "venue_country"]:
        if column not in df.columns:
            df[column] = ""

    df["show_date"] = pd.to_datetime(df["show_date"], errors="coerce").dt.date
    df = df.dropna(subset=["show_date", "source_uuid"])
    df["show_date"] = df["show_date"].apply(
        lambda d: d.isoformat() if pd.notnull(d) else None
    )

    df["source_hash"] = df.apply(lambda row: _hash_row(row.to_dict()), axis=1)
    df["created_at"] = datetime.now(timezone.utc).isoformat()
    df["updated_at"] = datetime.now(timezone.utc).isoformat()
    return df


def _normalize_setlists(raw_setlists: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(raw_setlists)
    if df.empty:
        return df

    timestamp = datetime.now(timezone.utc).isoformat()
    df["created_at"] = timestamp

    # Ensure source_hash is calculated
    df["source_hash"] = df.apply(lambda row: _hash_row(row.to_dict()), axis=1)

    numeric_columns = {
        "set_number": "Int64",
        "song_position": "Int64",
    }
    for column, dtype in numeric_columns.items():
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(dtype)

    bool_columns = ["is_segue", "encore"]
    for column in bool_columns:
        if column in df.columns:
            df[column] = df[column].fillna(False).astype(bool)

    df["song_name"] = df["song_name"].fillna("").astype(str)
    df = df.dropna(subset=["show_id", "song_name"])

    return df


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date '{date_str}'. Use YYYY-MM-DD.")


def _upsert_dataframe(
    table_name: str,
    df: pd.DataFrame,
    conflict_columns: List[str],
    skip_validation: bool,
) -> None:
    schema = get_table_schema(table_name)
    df_to_write = df

    if schema and not skip_validation:
        df_to_write = coerce_df_types(df_to_write, schema)
        report = validate_dataframe_against_table(df_to_write, table_name, schema)
        if not report.is_valid:
            print(f"⚠️  Validation warnings for {table_name}:")
            if report.missing_columns:
                print(f"    Missing columns: {report.missing_columns}")
            if report.type_mismatches:
                print(f"    Type mismatches: {len(report.type_mismatches)} columns")
            if report.nullable_violations:
                print(f"    Nullable violations: {report.nullable_violations}")

    upsert_dataframe(
        table_name=table_name,
        df=df_to_write,
        conflict_columns=conflict_columns,
    )


def run_billy_collection(
    skip_validation: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip_existing_setlists: bool = True,
    full_backfill: bool = False,
    skip_setlists: bool = False,
) -> None:
    print("Starting Billy Strings data collection...")
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
        songs_df = pd.DataFrame(songs_data)
        songs_df = songs_df.drop_duplicates(subset=["song_name"]).reset_index(drop=True)
        songs_df["source_hash"] = songs_df.apply(
            lambda row: _hash_row(row.to_dict()), axis=1
        )
        songs_df["created_at"] = datetime.now(timezone.utc).isoformat()
        songs_df["updated_at"] = datetime.now(timezone.utc).isoformat()
        _upsert_dataframe("billy_songs_raw", songs_df, ["song_name"], skip_validation)
        print(f"Upserted {len(songs_df)} songs into billy_songs_raw.")
    else:
        print("No Billy Strings songs scraped; skipping billy_songs_raw upsert.")

    # Shows
    shows_data = collector.collect_shows(start_date=start_dt, end_date=end_dt)
    if shows_data:
        shows_df = _normalize_shows(shows_data)
        _upsert_dataframe("billy_shows_raw", shows_df, ["source_uuid"], skip_validation)
        print(f"Upserted {len(shows_df)} shows into billy_shows_raw.")
    else:
        print("No Billy Strings shows scraped; skipping show upsert.")

    # Refresh shows from DB to get generated show_id values
    shows_from_db: List[Dict[str, Any]] = []
    try:
        shows_from_db = fetch_table("billy_shows_raw")
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
        _log_collection_run("billy")
        return

    if not shows_requiring_setlists:
        print(
            "No Billy Strings shows with database IDs available for setlist scraping."
        )
        _log_collection_run("billy")
        return

    existing_setlist_show_ids: set[str] = set()
    if skip_existing_setlists:
        try:
            setlists_from_db = fetch_table("billy_setlists_raw")
            existing_setlist_show_ids = {
                str(item["show_id"])
                for item in setlists_from_db
                if item.get("show_id") is not None
            }
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
        _log_collection_run("billy")
        return

    setlists_data = collector.collect_setlists(shows_to_process)
    setlists_df = _normalize_setlists(setlists_data)
    if setlists_df.empty:
        print("No valid Billy Strings setlist rows after normalization.")
        _log_collection_run("billy")
        return

    assert_required_columns(
        "billy_setlists_raw", setlists_df, ["set_number", "song_position"]
    )

    _upsert_dataframe(
        "billy_setlists_raw",
        setlists_df,
        ["show_id", "set_number", "song_position"],
        skip_validation,
    )
    print(f"Upserted {len(setlists_df)} rows into billy_setlists_raw.")

    _log_collection_run("billy")


def _log_collection_run(band: str) -> None:
    try:
        client = get_supabase_client()
        client.table("collection_runs").insert({"band": band}).execute()
        print("Logged collection run.")
    except Exception as exc:  # pragma: no cover - supabase connectivity
        print(f"Warning: could not log collection run ({exc}).")


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
