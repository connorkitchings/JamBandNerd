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
from datetime import datetime
from typing import Any, Dict, List
import requests

import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.wsp.collector import WSPCollector
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.db.connection import get_supabase_client
from scripts.common import fetch_table

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


def run_wsp_collection(skip_existing_setlists: bool = True, year_start: int | None = None, year_end: int | None = None, skip_url_validation: bool = False, full_backfill: bool = False) -> None:
    """Collect all WSP data and store it in Supabase raw tables."""
    logging.info("Starting Widespread Panic data collection...")
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
                
            for i, rec in enumerate(progress_bar):
                url = rec.get("source_url")
                try:
                    r = collector.session.get(url, timeout=15, allow_redirects=True)
                    if r.status_code == 200:
                        filtered_records.append(rec)
                        successes += 1
                except Exception:
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
            setlists_df["source_hash"] = setlists_df.apply(_compute_source_hash, axis=1)
            upsert_dataframe(
                table_name="wsp_setlists_raw",
                df=setlists_df,
                conflict_columns=["show_id", "set_number", "song_position"],
            )
            logging.info(f"Upserted {len(setlists_df)} setlist records into wsp_setlists_raw.")
    else:
        logging.info("No new shows require setlist scraping.")

    # 6. Log collection run
    try:
        client.table("collection_runs").insert({"band": "wsp"}).execute()
        logging.info("Logged collection run.")
    except Exception as exc:
        logging.warning(f"Could not log collection run ({exc}).")

    logging.info("Widespread Panic data collection finished.")


if __name__ == "__main__":
    import argparse
    from datetime import datetime as dt

    parser = argparse.ArgumentParser(description="Run Widespread Panic data collection pipeline.")
    parser.add_argument("--skip_existing_setlists", action="store_true", help="Skip shows that already have setlists.")
    parser.add_argument("--year_start", type=int, help="The first year to collect shows for.")
    parser.add_argument("--year_end", type=int, help="The last year to collect shows for.")
    parser.add_argument("--full_backfill", action="store_true", help="Perform a full backfill of all historical data, ignoring year filters.")
    
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
    )
