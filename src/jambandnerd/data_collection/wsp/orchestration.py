"""Orchestrates the Widespread Panic data collection pipeline.

This module contains the core logic for collecting, processing, and storing
WSP data from various sources.
"""

import logging
import os
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from jambandnerd.db.operations import upsert_dataframe, get_table_schema
from jambandnerd.db.connection import get_supabase_client
from scripts.common import fetch_table, ensure_source_reachable, assert_required_columns
from .collector import WSPCollector
from .tourwrangler import fetch_setlist_from_tourwrangler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def process_wsp_data(
    skip_existing_setlists: bool = True,
    year_start: int | None = None,
    year_end: int | None = None,
    full_backfill: bool = False,
) -> None:
    """Collect all WSP data and store it in Supabase raw tables."""
    logging.info("Starting Widespread Panic data collection...")
    ensure_source_reachable("wsp")
    collector = WSPCollector()
    client = get_supabase_client()

    # 1. Collect and Upsert Songs
    logging.info("--- Starting WSP Song Collection ---")
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = pd.DataFrame(songs_data)
        songs_df.rename(columns={"code": "song_code", "aka": "aka"}, inplace=True)
        for date_col in ["first_played", "last_played"]:
            if date_col in songs_df.columns:
                songs_df[date_col] = pd.to_datetime(songs_df[date_col], errors='coerce').dt.date
                songs_df[date_col] = songs_df[date_col].apply(lambda d: d.isoformat() if pd.notnull(d) else None)
        songs_df = songs_df.where(pd.notnull(songs_df), None)
        upsert_dataframe(
            table_name="wsp_songs_raw",
            df=songs_df,
            conflict_columns=["song_name"],
        )
        logging.info(f"Upserted {len(songs_df)} songs into wsp_songs_raw.")
    logging.info("--- Finished WSP Song Collection ---")

    # 2. Collect and Upsert Shows
    logging.info("--- Starting WSP Show Collection ---")
    shows_data = collector.collect_shows(
        start_date=datetime(year_start, 1, 1).date() if year_start else None,
        end_date=datetime(year_end, 12, 31).date() if year_end else None,
    )
    if shows_data:
        shows_df = pd.DataFrame(shows_data)
        shows_df["show_date"] = pd.to_datetime(shows_df["show_date"], errors='coerce').dt.date
        shows_df["show_date"] = shows_df["show_date"].apply(lambda d: d.isoformat() if pd.notnull(d) else None)
        upsert_dataframe(
            table_name="wsp_shows_raw",
            df=shows_df,
            conflict_columns=["source_url"],
        )
        logging.info(f"Upserted {len(shows_df)} shows into wsp_shows_raw.")
    logging.info("--- Finished WSP Show Collection ---")

    # 3. Fetch shows from DB for the specified year range
    if not full_backfill:
        if year_start and year_end:
            logging.info(f"Fetching shows from database for years {year_start}-{year_end}...")
            shows_response = client.table("wsp_shows_raw").select("*").gte("show_date", f"{year_start}-01-01").lte("show_date", f"{year_end}-12-31").execute()
            shows_to_process_df = pd.DataFrame(shows_response.data)
        else:
            logging.info("Fetching all shows from database...")
            shows_to_process_df = pd.DataFrame(fetch_table("wsp_shows_raw"))
    else:
        logging.info("Fetching all shows from database for full backfill...")
        shows_to_process_df = pd.DataFrame(fetch_table("wsp_shows_raw"))

    if shows_to_process_df.empty:
        logging.error("Could not retrieve shows from database. Aborting setlist collection.")
        return

    # 4. Check for existing setlists to avoid re-scraping
    if skip_existing_setlists:
        try:
            existing_ids = {record["show_id"] for record in client.table("wsp_setlists_raw").select("show_id").in_("show_id", shows_to_process_df["show_id"].tolist()).execute().data}
            shows_to_process_df = shows_to_process_df[~shows_to_process_df["show_id"].isin(existing_ids)]
        except Exception as e:
            logging.warning(f"Could not check existing setlists: {e}. Proceeding with all shows.")

    # 5. Collect and Upsert Setlists
    if not shows_to_process_df.empty:
        records_for_scrape = shows_to_process_df.to_dict("records")
        logging.info(
            f"Starting setlist collection for {len(records_for_scrape)} shows."
        )
        setlists_data = collector.collect_setlists(records_for_scrape)
        if setlists_data:
            setlists_df = pd.DataFrame(setlists_data)
            timestamp = datetime.now(timezone.utc).isoformat()
            setlists_df["created_at"] = timestamp
            setlists_df["updated_at"] = timestamp
            upsert_dataframe(
                table_name="wsp_setlists_raw",
                df=setlists_df,
                conflict_columns=["show_id", "set_number", "song_position"],
            )
            logging.info(
                f"Upserted {len(setlists_df)} setlist records into wsp_setlists_raw."
            )
        else:
            logging.info("No new shows require setlist scraping.")

    # 6. Promote EC over TW for recent shows
    try:
        today = date.today()
        window_days = int(os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - timedelta(days=window_days)
        schema = get_table_schema("wsp_setlists_raw")
        has_source_col = any(
            str(col.get("column_name", "")).lower() == "source" for col in schema
        )

        resp_shows = (
            client.table("wsp_shows_raw")
            .select("show_id, show_date")
            .gte("show_date", window_start.isoformat())
            .lt("show_date", today.isoformat())
            .execute()
        )
        recent_ids = [
            str(r.get("show_id")) for r in (resp_shows.data or []) if r.get("show_id")
        ]

        if has_source_col and recent_ids:
            logging.info(
                "Promoting Everyday Companion data over TourWrangler for recent shows..."
            )
            resp_ec = (
                client.table("wsp_setlists_raw")
                .select("show_id")
                .in_("show_id", recent_ids)
                .eq("source", "everydaycompanion")
                .execute()
            )
            ec_ids = sorted(
                {
                    str(r.get("show_id"))
                    for r in (resp_ec.data or [])
                    if r.get("show_id")
                }
            )
            if ec_ids:
                client.table("wsp_setlists_raw").delete().in_("show_id", ec_ids).eq(
                    "source", "tourwrangler"
                ).execute()
                logging.info(
                    f"Removed TourWrangler rows for {len(ec_ids)} show(s) now covered by EC."
                )
    except Exception as exc:
        logging.warning(f"EC-over-TW promotion step encountered an error: {exc}")

    # 7. TourWrangler fallback for missing recent historical setlists
    try:
        today = date.today()
        window_days = int(os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - timedelta(days=window_days)
        logging.info(
            f"Checking for missing setlists in window {window_start.isoformat()}..{today.isoformat()} (excluding today); window_days={window_days}"
        )

        recent_shows_resp = (
            client.table("wsp_shows_raw")
            .select("show_id, show_date, city, state")
            .gte("show_date", window_start.isoformat())
            .lt("show_date", today.isoformat())
            .execute()
        )
        recent_shows = recent_shows_resp.data or []
        if recent_shows:
            show_ids = [str(r.get("show_id")) for r in recent_shows if r.get("show_id")]
            if show_ids:
                setlists_resp = (
                    client.table("wsp_setlists_raw")
                    .select("show_id")
                    .in_("show_id", show_ids)
                    .execute()
                )
                with_setlists = {
                    str(r.get("show_id"))
                    for r in (setlists_resp.data or [])
                    if r.get("show_id")
                }
            else:
                with_setlists = set()

            missing = [
                r for r in recent_shows if str(r.get("show_id")) not in with_setlists
            ]
            logging.info(
                f"Found {len(missing)} recent shows with empty setlists needing backup."
            )

            backup_rows = []
            if missing:
                for rec in missing:
                    sid = str(rec.get("show_id"))
                    sdate_str = rec.get("show_date")
                    try:
                        sdate = pd.to_datetime(sdate_str).date() if sdate_str else None
                    except Exception:
                        sdate = None
                    if not sdate:
                        continue
                    city = rec.get("city")
                    state = rec.get("state")
                    try:
                        rows = fetch_setlist_from_tourwrangler(sdate, sid, city, state)
                    except Exception as e:
                        logging.warning(
                            f"TourWrangler fetch failed for show_id={sid} ({sdate_str}): {e}"
                        )
                        rows = []
                    if rows:
                        backup_rows.extend(rows)
                        logging.info(
                            f"TourWrangler provided {len(rows)} rows for show_id={sid} ({sdate_str})."
                        )

            if backup_rows:
                backup_df = pd.DataFrame(backup_rows)
                assert_required_columns(
                    "wsp_setlists_raw", backup_df, ["set_number", "song_position"]
                )

                schema = get_table_schema("wsp_setlists_raw")
                if any(
                    str(col.get("column_name", "")).lower() == "source"
                    for col in schema
                ):
                    backup_df["source"] = "tourwrangler"

                upsert_dataframe(
                    table_name="wsp_setlists_raw",
                    df=backup_df,
                    conflict_columns=["show_id", "set_number", "song_position"],
                )
                logging.info(
                    f"Upserted {len(backup_df)} TourWrangler backup setlist rows."
                )
    except Exception as exc:
        logging.warning(f"TourWrangler fallback step encountered an error: {exc}")

    # 8. Log collection run
    try:
        client.table("collection_runs").insert({"band": "wsp"}).execute()
        logging.info("Logged collection run.")
    except Exception as exc:
        logging.warning(f"Could not log collection run ({exc}).")

    logging.info("Widespread Panic data collection finished.")
