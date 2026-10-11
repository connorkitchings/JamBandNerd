"""Runs the Billy Strings data collection pipeline.

This script mirrors the goose/wsp collectors by normalizing scraped data and
persisting it into the Supabase raw tables. It focuses on shows and setlists,
with placeholders for songs/venues should billybase.net expose richer endpoints
in the future.
"""

from __future__ import annotations

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import argparse
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, cast

from scripts.common import ensure_source_reachable
from src.jambandnerd.data_collection.billy.collector import BillyCollector
from src.jambandnerd.data_collection.billy.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
)
from src.jambandnerd.data_collection.browser import CloudflareBypass
from src.jambandnerd.data_collection.utils import CollectionTimer, compute_source_hash
from src.jambandnerd.db.connection import get_supabase_client
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


def _sync_existing_song_names_by_uuid(songs_df):
    """Update existing Billy song labels when bmfsdb keeps UUIDs but changes casing."""
    if songs_df.empty or "song_uuid" not in songs_df or "song_name" not in songs_df:
        return songs_df

    uuid_to_name = {
        str(row["song_uuid"]): str(row["song_name"])
        for _, row in songs_df[["song_uuid", "song_name"]].dropna().iterrows()
        if str(row["song_uuid"]).strip() and str(row["song_name"]).strip()
    }
    if not uuid_to_name:
        return songs_df

    existing_rows = fetch_rows_by_column_values(
        "billy_songs_raw",
        select_columns=["song_uuid", "song_name"],
        filter_column="song_uuid",
        values=list(uuid_to_name),
    )
    existing_name_by_uuid = {
        str(row["song_uuid"]): str(row.get("song_name") or "")
        for row in existing_rows
        if row.get("song_uuid")
    }
    updates = [
        (
            str(row["song_uuid"]),
            existing_name_by_uuid[str(row["song_uuid"])],
            uuid_to_name[str(row["song_uuid"])],
        )
        for row in existing_rows
        if row.get("song_uuid")
        and existing_name_by_uuid.get(str(row["song_uuid"]))
        != uuid_to_name.get(str(row["song_uuid"]))
    ]
    if not updates:
        return songs_df

    desired_names = [desired_name for _, _, desired_name in updates]
    name_to_uuid = {desired_name: song_uuid for song_uuid, _, desired_name in updates}
    if len(name_to_uuid) != len(updates):
        raise RuntimeError(
            "Cannot reconcile Billy song UUID labels because multiple UUIDs map "
            "to the same scraped song_name."
        )
    existing_name_rows = fetch_rows_by_column_values(
        "billy_songs_raw",
        select_columns=["song_uuid", "song_name"],
        filter_column="song_name",
        values=desired_names,
    )
    conflicting_name_to_uuid = {
        str(row["song_name"]): str(row["song_uuid"])
        for row in existing_name_rows
        if row.get("song_name")
        and row.get("song_uuid")
        and str(row["song_uuid"]) != name_to_uuid.get(str(row["song_name"]))
    }

    adjusted = songs_df.copy()
    safe_updates = []
    for song_uuid, existing_name, desired_name in updates:
        conflicting_uuid = conflicting_name_to_uuid.get(desired_name)
        if conflicting_uuid:
            row_mask = adjusted["song_uuid"].astype(str) == song_uuid
            adjusted.loc[row_mask, "song_name"] = existing_name
            if "source_hash" in adjusted.columns:
                for index in adjusted.loc[row_mask].index:
                    payload = {
                        key: value
                        for key, value in adjusted.loc[index].to_dict().items()
                        if key not in {"created_at", "updated_at", "source_hash"}
                    }
                    adjusted.at[index, "source_hash"] = compute_source_hash(payload)
            print(
                "Keeping existing Billy song label "
                f"'{existing_name}' for UUID {song_uuid}; scraped label "
                f"'{desired_name}' is already owned by UUID {conflicting_uuid}."
            )
            continue
        safe_updates.append((song_uuid, desired_name))

    client = get_supabase_client()
    for song_uuid, song_name in safe_updates:
        client.table("billy_songs_raw").update({"song_name": song_name}).eq(
            "song_uuid", song_uuid
        ).execute()
    if safe_updates:
        print(f"Updated {len(safe_updates)} Billy song label(s) by stable song_uuid.")
    return adjusted


def _normalize_venue_key(name: Optional[str]) -> str:
    """Normalize a venue name for stable matching across sources."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _reconcile_existing_show_uuids_by_date_venue(
    shows_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Reuse existing billy_shows_raw source_uuid when date+venue matches.

    BillyBase uses slug-derived UUIDs while the historical corpus was keyed on
    bmfsdb UUIDs. Matching by natural key preserves ``show_id`` continuity for
    the prediction corpus while still updating venue/source_url from BillyBase.
    """
    if not shows_data:
        return shows_data

    dates = [show["show_date"] for show in shows_data if show.get("show_date")]
    if not dates:
        return shows_data

    min_date = min(dates)
    max_date = max(dates)

    try:
        client = get_supabase_client()
        response = (
            client.table("billy_shows_raw")
            .select("show_id, source_uuid, show_date, venue_name")
            .gte("show_date", min_date)
            .lte("show_date", max_date)
            .execute()
        )
        existing_rows = cast(List[Dict[str, Any]], response.data or [])
    except Exception as exc:  # pragma: no cover - supabase connectivity
        print(
            f"Warning: could not fetch existing Billy shows for reconciliation ({exc})."
        )
        return shows_data

    existing_by_key: Dict[tuple[str, str], str] = {}
    for row in existing_rows:
        key = (
            row["show_date"],
            _normalize_venue_key(row.get("venue_name")),
        )
        existing_by_key[key] = row["source_uuid"]

    updated = 0
    for show in shows_data:
        key = (
            show["show_date"],
            _normalize_venue_key(show.get("venue_name")),
        )
        existing_uuid = existing_by_key.get(key)
        if existing_uuid and existing_uuid != show.get("source_uuid"):
            show["source_uuid"] = existing_uuid
            updated += 1

    if updated:
        print(
            f"Reconciled {updated} BillyBase show(s) to existing source_uuid "
            "by date+venue."
        )
    return shows_data


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
        songs_df = _sync_existing_song_names_by_uuid(songs_df)
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
    shows_data = _reconcile_existing_show_uuids_by_date_venue(shows_data)
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

    # Release the shared Playwright browser if the upcoming-shows fallback used it.
    CloudflareBypass.cleanup()
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
