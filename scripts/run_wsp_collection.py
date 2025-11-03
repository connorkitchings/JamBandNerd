'''Runs the Widespread Panic data collection pipeline.

This script fetches data from everydaycompanion.com via the `WSPCollector`,
normalizes the responses to the raw table schemas, and performs upserts into
the `wsp_songs_raw`, `wsp_shows_raw`, and `wsp_setlists_raw` tables.
'''
from __future__ import annotations

import hashlib
import json
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests

import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.wsp.collector import WSPCollector
from src.jambandnerd.data_collection.wsp.tourwrangler import fetch_setlist_from_tourwrangler
from src.jambandnerd.db.operations import upsert_dataframe, get_table_schema
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.validation import coerce_df_types, validate_dataframe_against_table
from scripts.common import fetch_table, ensure_source_reachable, assert_required_columns

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _compute_source_hash(record: pd.Series) -> str:
    """Compute a deterministic hash of a JSON-serializable record."""
    # Convert the pandas Series to a dictionary and handle non-serializable types
    record_dict = record.to_dict()
    cleaned_dict = {k: (None if pd.isna(v) else v) for k, v in record_dict.items()}
    payload = json.dumps(cleaned_dict, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_wsp_collection(skip_existing_setlists: bool = True, year_start: int | None = None, year_end: int | None = None, skip_url_validation: bool = False, full_backfill: bool = False, skip_validation: bool = False) -> None:
    """Collect all WSP data and store it in Supabase raw tables."""
    forbidden_error_encountered = False
    logging.info("Starting Widespread Panic data collection...")
    ensure_source_reachable("wsp")
    collector = WSPCollector()
    client = get_supabase_client()

    # 1. Collect and Upsert Songs
    logging.info("--- Starting WSP Song Collection ---")
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = pd.DataFrame(songs_data)
        # Align with the corrected schema
        songs_df.rename(columns={"code": "song_code", "aka": "aka"}, inplace=True)
        # Normalize date columns to ISO strings and replace NaN/NaT with None for JSON serialization
        for date_col in ["first_played", "last_played"]:
            if date_col in songs_df.columns:
                songs_df[date_col] = pd.to_datetime(songs_df[date_col], errors='coerce')
                songs_df[date_col] = songs_df[date_col].dt.date.apply(lambda d: d.isoformat() if pd.notnull(d) else None)
        songs_df = songs_df.where(pd.notnull(songs_df), None)
        songs_df["source_hash"] = songs_df.apply(_compute_source_hash, axis=1)
        songs_df["is_cover"] = None
        songs_df["original_artist"] = None
        songs_df["created_at"] = datetime.now(timezone.utc).isoformat()
        songs_df["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Validation for songs
        schema = get_table_schema("wsp_songs_raw")
        if schema and not skip_validation:
            songs_df = coerce_df_types(songs_df, schema)
            report = validate_dataframe_against_table(songs_df, "wsp_songs_raw", schema)
            if not report.is_valid:
                logging.warning(f"⚠️  Validation warnings for wsp_songs_raw:")
                if report.missing_columns:
                    logging.warning(f"    Missing columns: {report.missing_columns}")
                if report.type_mismatches:
                    logging.warning(f"    Type mismatches: {len(report.type_mismatches)} columns")
                if report.nullable_violations:
                    logging.warning(f"    Nullable violations: {report.nullable_violations}")
        
        upsert_dataframe(
            table_name="wsp_songs_raw",
            df=songs_df,
            conflict_columns=["song_name"],
        )
        logging.info(f"Upserted {len(songs_df)} songs into wsp_songs_raw.")
        logging.info("--- Finished WSP Song Collection ---")

    # Set default year range if not doing a full backfill
    if not full_backfill and year_start is None and year_end is None:
        current_year = datetime.now().year
        year_start = current_year - 1
        year_end = current_year
        logging.info(f"Defaulting to show collection for years: {year_start}-{year_end}")

    # 2. Collect and Upsert Shows
    logging.info("--- Starting WSP Show Collection ---")
    # Optional year filtering for shows
    from datetime import date, datetime as dt
    start_date = date(year_start, 1, 1) if year_start else None
    end_date = date(year_end, 12, 31) if year_end else None
    shows_data = collector.collect_shows(start_date=start_date, end_date=end_date)
    if shows_data:
        shows_df = pd.DataFrame(shows_data)
        shows_df["source_hash"] = shows_df.apply(_compute_source_hash, axis=1)
        shows_df["show_notes"] = None
        shows_df["created_at"] = datetime.now(timezone.utc).isoformat()
        shows_df["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Validation for shows
        schema = get_table_schema("wsp_shows_raw")
        if schema and not skip_validation:
            shows_df = coerce_df_types(shows_df, schema)
            report = validate_dataframe_against_table(shows_df, "wsp_shows_raw", schema)
            if not report.is_valid:
                logging.warning(f"⚠️  Validation warnings for wsp_shows_raw:")
                if report.missing_columns:
                    logging.warning(f"    Missing columns: {report.missing_columns}")
                if report.type_mismatches:
                    logging.warning(f"    Type mismatches: {len(report.type_mismatches)} columns")
                if report.nullable_violations:
                    logging.warning(f"    Nullable violations: {report.nullable_violations}")
        
        upsert_dataframe(
            table_name="wsp_shows_raw",
            df=shows_df,
            conflict_columns=["source_url"],
        )
        logging.info(f"Upserted {len(shows_df)} shows into wsp_shows_raw.")
        logging.info("--- Finished WSP Show Collection ---")

    # 3. Fetch shows back from DB to get generated show_ids (WITH YEAR FILTERING)
    if year_start and year_end:
        logging.info(f"Fetching shows from database for years {year_start}-{year_end}...")
    else:
        logging.info("Fetching shows from database to get generated IDs...")
        
    all_shows_from_db = fetch_table("wsp_shows_raw")
    if not all_shows_from_db:
        logging.error("Could not retrieve shows from database. Aborting setlist collection.")
        return
    
    url_to_id_map = {show['source_url']: show['show_id'] for show in all_shows_from_db}
    shows_to_process = pd.DataFrame(all_shows_from_db)
    
    # Convert show_date to datetime for filtering
    shows_to_process["_show_date_dt"] = pd.to_datetime(shows_to_process["show_date"], errors="coerce")
    
    # Apply year filtering if specified (BEFORE other processing)
    if year_start and year_end:
        start_year_filter = pd.Timestamp(f"{year_start}-01-01")
        end_year_filter = pd.Timestamp(f"{year_end}-12-31")
        shows_before_filter = len(shows_to_process)
        
        shows_to_process = shows_to_process[
            (shows_to_process["_show_date_dt"] >= start_year_filter) & 
            (shows_to_process["_show_date_dt"] <= end_year_filter)
        ]
        
        logging.info(f"Year filter applied: {shows_before_filter} -> {len(shows_to_process)} shows ({year_start}-{year_end})")
    
    # Keep only past shows (setlists exist only after the show)
    shows_to_process = shows_to_process[shows_to_process["_show_date_dt"] <= pd.Timestamp("today")]

    # 4. Check for existing setlists to avoid re-scraping (OPTIMIZED)
    if skip_existing_setlists:
        logging.info("Checking for existing setlists in the database (optimized query)...")
        # Instead of fetching 63K records, just get unique show_ids directly
        try:
            response = client.table("wsp_setlists_raw").select("show_id").execute()
            if response.data:
                existing_ids = set(record["show_id"] for record in response.data)
                shows_to_process = shows_to_process[~shows_to_process["show_id"].isin(existing_ids)]
                logging.info(f"Found {len(existing_ids)} shows with existing setlists. Scraping for {len(shows_to_process)} remaining shows.")
            else:
                logging.info("No existing setlists found in database.")
        except Exception as e:
            logging.warning(f"Could not check existing setlists efficiently: {e}. Proceeding with all shows.")

    # 5. Collect and Upsert Setlists
    if not shows_to_process.empty:
        candidate_records: List[Dict[str, Any]] = shows_to_process.to_dict('records')
        
        if skip_url_validation:
            logging.info(f"Skipping URL validation, proceeding with all {len(candidate_records)} candidate shows.")
            records_for_scrape = candidate_records
        else:
            # Filter to URLs that respond (avoid 404 noise) - WITH PROGRESS TRACKING
            filtered_records: List[Dict[str, Any]] = []
            successes = 0
            total_candidates = len(candidate_records)
            
            logging.info(f"Validating {total_candidates} setlist URLs for availability...")
            
            # Add progress tracking for URL validation
            try:
                from tqdm import tqdm
                progress_bar = tqdm(candidate_records, desc="Validating URLs", unit="url")
            except ImportError:
                progress_bar = candidate_records
                
            nonlocal forbidden_error_encountered
            for i, rec in enumerate(progress_bar):
                url = rec.get("source_url")
                try:
                    r = collector.session.get(url, timeout=15, allow_redirects=True)
                    if r.status_code == 200:
                        filtered_records.append(rec)
                        successes += 1
                    elif r.status_code == 403:
                        logging.warning(f"HTTP error 403: Forbidden for URL {url}. Skipping this URL.")
                        forbidden_error_encountered = True
                except Exception as e:
                    logging.warning(f"URL validation failed for {url} with error: {e}")
                    continue
                    
                # Log progress periodically for users without tqdm
                if not hasattr(progress_bar, 'update') and (i + 1) % 100 == 0:
                    logging.info(f"URL validation progress: {i+1}/{total_candidates} ({successes} valid so far)")
                    
            logging.info(f"Validated {successes}/{len(candidate_records)} setlist URLs with 200 status.")

            # Fallback to original candidate set if validation yields zero
            records_for_scrape = filtered_records if filtered_records else candidate_records
        logging.info(f"Starting setlist collection for {len(records_for_scrape)} shows.")
        setlists_data = collector.collect_setlists(records_for_scrape)
        if setlists_data:
            setlists_df = pd.DataFrame(setlists_data)
            assert_required_columns("wsp_setlists_raw", setlists_df, ["set_number", "song_position"])
            timestamp = datetime.now(timezone.utc).isoformat()
            setlists_df["created_at"] = timestamp
            setlists_df["updated_at"] = timestamp
            setlists_df["source_hash"] = setlists_df.apply(_compute_source_hash, axis=1)

            # Optionally tag source if column exists
            schema = get_table_schema("wsp_setlists_raw")
            has_source_col = False
            if schema:
                for col in schema:
                    if str(col.get("column_name", "")).lower() == "source":
                        has_source_col = True
                        break
            if has_source_col:
                setlists_df["source"] = "everydaycompanion"
            else:
                # If the column doesn't exist, add a light note for future traceability
                if "song_notes" in setlists_df.columns:
                    setlists_df["song_notes"] = setlists_df["song_notes"].fillna("").astype(str)
                    setlists_df["song_notes"] = setlists_df["song_notes"].where(
                        setlists_df["song_notes"].str.contains("from TourWrangler|from Everyday", case=False, na=False),
                        setlists_df["song_notes"].str.cat(pd.Series(["" for _ in range(len(setlists_df))]), sep="")
                    )

            # Validation for setlists
            if schema and not skip_validation:
                setlists_df = coerce_df_types(setlists_df, schema)
                report = validate_dataframe_against_table(setlists_df, "wsp_setlists_raw", schema)
                if not report.is_valid:
                    logging.warning(f"⚠️  Validation warnings for wsp_setlists_raw:")
                    if report.missing_columns:
                        logging.warning(f"    Missing columns: {report.missing_columns}")
                    if report.type_mismatches:
                        logging.warning(f"    Type mismatches: {len(report.type_mismatches)} columns")
                    if report.nullable_violations:
                        logging.warning(f"    Nullable violations: {report.nullable_violations}")
            
            upsert_dataframe(
                table_name="wsp_setlists_raw",
                df=setlists_df,
                conflict_columns=["show_id", "set_number", "song_position"],
            )
            logging.info(f"Upserted {len(setlists_df)} setlist records into wsp_setlists_raw.")
        else:
            logging.info("No new shows require setlist scraping.")

    # 6. Promote EC over TW for recent shows: if EC exists, remove TW rows for those shows
    try:
        from datetime import date as _date, timedelta as _timedelta
        import os as _os
        today = _date.today()
        window_days = int(_os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - _timedelta(days=window_days)
        schema = get_table_schema("wsp_setlists_raw")
        has_source_col = False
        if schema:
            for col in schema:
                if str(col.get("column_name", "")).lower() == "source":
                    has_source_col = True
                    break
        # Get recent show_ids from shows table (before today)
        resp_shows = client.table("wsp_shows_raw").select("show_id, show_date").gte("show_date", window_start.isoformat()).lt("show_date", today.isoformat()).execute()
        recent_ids = [str(r.get("show_id")) for r in (resp_shows.data or []) if r.get("show_id")]
        if has_source_col:
            logging.info("Promoting Everyday Companion data over TourWrangler for recent shows...")
            if recent_ids:
                # Find which of these have EC rows
                resp_ec = client.table("wsp_setlists_raw").select("show_id").in_("show_id", recent_ids).eq("source", "everydaycompanion").execute()
                ec_ids = sorted({str(r.get("show_id")) for r in (resp_ec.data or []) if r.get("show_id")})
                if ec_ids:
                    # Delete TW rows for these shows
                    client.table("wsp_setlists_raw").delete().in_("show_id", ec_ids).eq("source", "tourwrangler").execute()
                    logging.info(f"Removed TourWrangler rows for {len(ec_ids)} show(s) now covered by EC.")
        else:
            logging.info("No 'source' column detected; will attempt structural cleanup instead.")

        # Structural cleanup: for any recent show with EC rows, remove rows not present in EC (handles cases with no source tags)
        if recent_ids:
            # Determine shows with any EC rows (with or without source tag)
            if has_source_col:
                resp_any_ec = client.table("wsp_setlists_raw").select("show_id").in_("show_id", recent_ids).eq("source", "everydaycompanion").execute()
                shows_with_ec = sorted({str(r.get("show_id")) for r in (resp_any_ec.data or []) if r.get("show_id")})
            else:
                # Fallback: assume all rows for a show after this run are EC; safe only if we compare positions
                # Identify EC positions by re-reading rows we just inserted for each recent show
                shows_with_ec = []
                for sid in recent_ids:
                    # Heuristic: check if there are rows for the show at all (post EC upsert)
                    chk = client.table("wsp_setlists_raw").select("show_id").eq("show_id", sid).limit(1).execute()
                    if chk.data:
                        shows_with_ec.append(sid)

            for sid in shows_with_ec:
                # Fetch EC key set (set_number, song_position) for the show
                if has_source_col:
                    ec_rows = client.table("wsp_setlists_raw").select("set_number,song_position").eq("show_id", sid).eq("source", "everydaycompanion").execute().data or []
                else:
                    ec_rows = client.table("wsp_setlists_raw").select("set_number,song_position").eq("show_id", sid).execute().data or []
                ec_keys = {(str(r.get("set_number")), int(r.get("song_position") or 0)) for r in ec_rows}

                # Fetch all rows for the show with ids
                all_rows = client.table("wsp_setlists_raw").select("id,set_number,song_position").eq("show_id", sid).execute().data or []
                extras = [r for r in all_rows if (str(r.get("set_number")), int(r.get("song_position") or 0)) not in ec_keys]
                if extras:
                    ids_to_delete = [r.get("id") for r in extras if r.get("id")]
                    # Batch delete extras
                    if ids_to_delete:
                        client.table("wsp_setlists_raw").delete().in_("id", ids_to_delete).execute()
                        logging.info(f"Cleaned {len(ids_to_delete)} extra setlist rows for show_id={sid} not present in EC.")
    except Exception as exc:
        logging.warning(f"EC-over-TW promotion step encountered an error: {exc}")

    # 7. TourWrangler fallback for missing recent historical setlists (last 3 days, excluding today)
    try:
        from datetime import date as _date, timedelta as _timedelta
        import os as _os
        today = _date.today()
        window_days = int(_os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - _timedelta(days=window_days)
        logging.info(f"Checking for missing setlists in window {window_start.isoformat()}..{today.isoformat()} (excluding today); window_days={window_days}")

        # Fetch recent shows (before today)
        recent_shows_resp = client.table("wsp_shows_raw").select("show_id, show_date, city, state").gte("show_date", window_start.isoformat()).lt("show_date", today.isoformat()).execute()
        recent_shows = recent_shows_resp.data or []
        if recent_shows:
            show_ids = [str(r.get("show_id")) for r in recent_shows if r.get("show_id")]
            # Determine which of these already have any setlist rows
            if show_ids:
                setlists_resp = client.table("wsp_setlists_raw").select("show_id").in_("show_id", show_ids).execute()
                with_setlists = {str(r.get("show_id")) for r in (setlists_resp.data or []) if r.get("show_id")}
            else:
                with_setlists = set()

            missing = [r for r in recent_shows if str(r.get("show_id")) not in with_setlists]
            logging.info(f"Found {len(missing)} recent shows with empty setlists needing backup.")

            backup_rows: List[Dict[str, Any]] = []
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
                        logging.warning(f"TourWrangler fetch failed for show_id={sid} ({sdate_str}): {e}")
                        rows = []
                    if rows:
                        for r in rows:
                            r.setdefault("song_notes", "")
                        backup_rows.extend(rows)
                        logging.info(f"TourWrangler provided {len(rows)} rows for show_id={sid} ({sdate_str}).")

            if backup_rows:
                backup_df = pd.DataFrame(backup_rows)
                assert_required_columns("wsp_setlists_raw", backup_df, ["set_number", "song_position"])
                backup_df["source_hash"] = backup_df.apply(_compute_source_hash, axis=1)

                schema = get_table_schema("wsp_setlists_raw")
                has_source_col = False
                if schema:
                    for col in schema:
                        if str(col.get("column_name", "")).lower() == "source":
                            has_source_col = True
                            break
                if has_source_col:
                    backup_df["source"] = "tourwrangler"
                else:
                    if "song_notes" in backup_df.columns:
                        backup_df["song_notes"] = backup_df["song_notes"].fillna("").astype(str) + (backup_df["song_notes"].map(lambda _: "").astype(str))

                if schema and not skip_validation:
                    backup_df = coerce_df_types(backup_df, schema)
                    report = validate_dataframe_against_table(backup_df, "wsp_setlists_raw", schema)
                    if not report.is_valid:
                        logging.warning("⚠️ Validation warnings for wsp_setlists_raw (TourWrangler backup)")

                upsert_dataframe(
                    table_name="wsp_setlists_raw",
                    df=backup_df,
                    conflict_columns=["show_id", "set_number", "song_position"],
                )
                logging.info(f"Upserted {len(backup_df)} TourWrangler backup setlist rows.")
        else:
            logging.info("No recent historical shows found in window; no backup needed.")
    except Exception as exc:
        logging.warning(f"TourWrangler fallback step encountered an error: {exc}")

    # 8. Log collection run
    try:
        client.table("collection_runs").insert({"band": "wsp"}).execute()
        logging.info("Logged collection run.")
    except Exception as exc:
        logging.warning(f"Could not log collection run ({exc}).")

    logging.info("Widespread Panic data collection finished.")

    if forbidden_error_encountered:
        logging.warning("Collection finished, but one or more URLs returned a 403 Forbidden error.")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    from datetime import datetime as dt

    parser = argparse.ArgumentParser(description="Run Widespread Panic data collection pipeline.")
    parser.add_argument("--skip_existing_setlists", action="store_true", help="Skip shows that already have setlists.")
    parser.add_argument("--year_start", type=int, help="The first year to collect shows for.")
    parser.add_argument("--year_end", type=int, help="The last year to collect shows for.")
    parser.add_argument("--full_backfill", action="store_true", help="Perform a full backfill of all historical data, ignoring year filters.")
    parser.add_argument("--skip_validation", action="store_true", help="Bypass schema validation before upserts.")
    parser.add_argument("--skip_url_validation", action="store_true", help="Skip URL validation for faster processing (use when URLs are known to be good).")

    args = parser.parse_args()

    # Example of runs:
    # uv run python scripts/run_wsp_collection.py                    # Default: last year + this year
    # uv run python scripts/run_wsp_collection.py --year_start 2023 --year_end 2023  # Specific year
    # uv run python scripts/run_wsp_collection.py --full_backfill   # All historical data
    run_wsp_collection(
        skip_existing_setlists=args.skip_existing_setlists,
        year_start=args.year_start,
        year_end=args.year_end,
        skip_url_validation=args.skip_url_validation,
        full_backfill=args.full_backfill,
        skip_validation=args.skip_validation,
    )
