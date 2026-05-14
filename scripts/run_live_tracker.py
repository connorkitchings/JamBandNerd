#!/usr/bin/env python3
"""
Live Tracker for in-progress shows.

Continually polls the band's API for the setlist of a specific date,
bypassing the cache. When a new song is detected, it upserts the setlist
and triggers a fresh prediction run.
"""

import argparse
import logging
import os
import sys
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.generate_predictions import generate_predictions
from src.jambandnerd.db.operations import validate_and_upsert_dataframe

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)


def run_live_tracker(
    band: str,
    target_date: str,
    interval: int = 60,
    max_iterations: int = 300,
    bsky_handle: str = "widespreadpanic.com",
):
    """Poll API for live setlist updates and trigger pipeline."""
    logger.info(
        f"Starting live tracker for {band.upper()} on {target_date} (interval: {interval}s)"
    )

    collector = None
    client = None

    if band == "phish":
        from scripts.run_phish_collection import _normalize_setlists, _normalize_shows
        from src.jambandnerd.data_collection.phish.collector import (
            PhishCollector as Collector,
        )

        table_name = "phish_setlists_raw"
        conflict_cols = ["api_unique_id"]
        required_cols = ["set_number", "position"]
        collector = Collector()
    elif band == "goose":
        from scripts.run_goose_collection import _normalize_setlists, _normalize_shows
        from src.jambandnerd.data_collection.goose.collector import (
            GooseCollector as Collector,
        )

        table_name = "goose_setlists_raw"
        conflict_cols = ["show_id", "set_number", "song_position"]
        required_cols = ["set_number", "song_position"]
        collector = Collector()
    elif band == "wsp":
        import pandas as pd
        import requests
        from bs4 import BeautifulSoup

        from src.jambandnerd.data_collection.wsp.parser import parse_setlist_from_text
        from src.jambandnerd.db.connection import get_supabase_client

        table_name = "wsp_setlists_raw"
        conflict_cols = ["show_id", "set_number", "song_position"]
        required_cols = ["set_number", "song_position"]
        # We use bs4 and requests directly for WSP
        client = get_supabase_client()
    else:
        raise ValueError(f"Live tracking not currently supported for band: {band}")

    if collector:
        # Bypass cache to ensure we fetch fresh data from API on every loop
        collector.cache = None

    last_song_count = -1
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        try:
            # 1. Fetch shows and find show_id for target date
            if band == "wsp":
                assert client is not None
                resp = (
                    client.table("wsp_shows_raw")
                    .select("show_id")
                    .eq("show_date", target_date)
                    .limit(1)
                    .execute()
                )
                if not resp.data:
                    logger.warning(
                        f"No WSP show found in DB for {target_date}. Retrying in {interval}s..."
                    )
                    time.sleep(interval)
                    continue
                show_id = str(resp.data[0]["show_id"])
            else:
                assert collector is not None
                raw_shows = collector.collect_shows()
                shows_df = _normalize_shows(raw_shows)

                if shows_df.empty:
                    logger.warning("No shows fetched.")
                    time.sleep(interval)
                    continue

                # Need to match date format. shows_df['show_date'] should be YYYY-MM-DD
                target_show = shows_df[shows_df["show_date"] == target_date]

                if target_show.empty:
                    logger.warning(
                        f"No show found for date {target_date}. Retrying in {interval}s..."
                    )
                    time.sleep(interval)
                    continue

                show_id_col = "show_id"

                show_id = str(target_show.iloc[0][show_id_col])

            # 2. Fetch setlist for this show
            if band == "wsp":
                logger.debug(f"Fetching Bluesky feed for {bsky_handle}...")
                r = requests.get(
                    f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={bsky_handle}&limit=10"
                )
                r.raise_for_status()
                feed = r.json().get("feed", [])

                # Combine all text from the recent posts into one big block
                # Order them chronologically so parsing is natural (oldest first)
                texts = []
                for item in reversed(feed):
                    post = item.get("post", {}).get("record", {})
                    text = post.get("text", "")
                    if text:
                        texts.append(text)

                combined_text = "\\n".join(texts)

                # Use the parser wrapper
                soup = BeautifulSoup(combined_text, "html.parser")
                raw_setlists = parse_setlist_from_text(soup, show_id)
                setlists_df = pd.DataFrame(raw_setlists)
            else:
                assert collector is not None
                if band == "phish":
                    raw_setlists = collector.collect_setlists(show_ids=[show_id])
                    setlists_df = _normalize_setlists(raw_setlists)
                else:
                    # Goose fetches all setlists, filter in pandas
                    raw_setlists = collector.collect_setlists()
                    setlists_df = _normalize_setlists(raw_setlists)
                    setlists_df = setlists_df[setlists_df["show_id"] == show_id]

            current_song_count = len(setlists_df)

            # 3. Check if song count increased
            if current_song_count > last_song_count:
                logger.info(
                    f"🚨 New song detected! Count increased from {last_song_count} to {current_song_count}."
                )

                # Upsert just this show's setlist
                if not setlists_df.empty:
                    if (
                        band == "phish"
                        and "position" in setlists_df.columns
                        and "song_position" not in setlists_df.columns
                    ):
                        setlists_df.rename(
                            columns={"position": "song_position"}, inplace=True
                        )

                    validate_and_upsert_dataframe(
                        table_name=table_name,
                        df=setlists_df,
                        conflict_columns=conflict_cols,
                        required_columns=required_cols,
                        skip_validation=True,
                    )
                    logger.info(
                        f"Upserted {current_song_count} rows into {table_name}."
                    )

                # Trigger predictions
                logger.info("Regenerating Notebook predictions...")
                generate_predictions(
                    band=band, model="notebook", date_str=None, exclusion_window=3
                )

                logger.info("Regenerating Deal predictions...")
                generate_predictions(
                    band=band, model="deal", date_str=None, exclusion_window=3
                )

                last_song_count = current_song_count
                logger.info(
                    f"Predictions successfully updated for {current_song_count}-song setlist."
                )
            else:
                logger.debug(
                    f"No changes detected (current count: {current_song_count})."
                )

        except Exception as e:
            logger.error(f"Error during polling loop: {e}")

        # Sleep until next interval
        logger.info(f"Sleeping for {interval}s...")
        time.sleep(interval)

    logger.info("Live tracker finished (max iterations reached).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the live show tracker for real-time predictions."
    )
    parser.add_argument(
        "--band", required=True, choices=["phish", "goose", "wsp"], help="Band to track"
    )
    parser.add_argument("--date", required=True, help="Target show date (YYYY-MM-DD)")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds (default 60)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=300,
        help="Maximum number of polling attempts before stopping (default 300, ~5 hours)",
    )
    parser.add_argument(
        "--bsky-handle",
        default="widespreadpanic.com",
        help="Bluesky handle to track for WSP (e.g., widespreadpanic.com)",
    )
    args = parser.parse_args()

    run_live_tracker(
        band=args.band,
        target_date=args.date,
        interval=args.interval,
        max_iterations=args.max_iterations,
        bsky_handle=args.bsky_handle,
    )
