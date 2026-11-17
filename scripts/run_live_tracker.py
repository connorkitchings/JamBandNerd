#!/usr/bin/env python3
"""Poll Goose or Phish for changed live setlists and refresh predictions."""

import argparse
import logging
import os
import sys
import time
from dataclasses import replace

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.generate_live_predictions import generate_live_predictions
from src.jambandnerd.db.operations import validate_and_upsert_dataframe

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)


def run_live_tracker(
    band: str,
    target_date: str,
    interval: int = 60,
    max_iterations: int = 300,
):
    """Poll without caching; raise after three consecutive failed polls."""
    logger.info(
        "Starting live tracker for %s on %s (interval: %ss)",
        band.upper(),
        target_date,
        interval,
    )

    if band == "phish":
        from src.jambandnerd.data_collection.phish.collector import (
            PhishCollector as Collector,
        )
        from src.jambandnerd.data_collection.phish.normalizer import (
            normalize_setlists,
            normalize_shows,
        )

        table_name = "phish_setlists_raw"
        conflict_cols = ["api_unique_id"]
        required_cols = ["set_number", "position"]
    elif band == "goose":
        from src.jambandnerd.data_collection.goose.collector import (
            GooseCollector as Collector,
        )
        from src.jambandnerd.data_collection.goose.normalizer import (
            normalize_setlists,
            normalize_shows,
        )

        table_name = "goose_setlists_raw"
        conflict_cols = ["show_id", "set_number", "song_position"]
        required_cols = ["set_number", "song_position"]
    else:
        raise ValueError(f"Live tracking not currently supported for band: {band}")

    collector = Collector()
    collector.cache = None
    # Config objects are shared with daily collectors; change only this instance.
    collector.config = replace(collector.config, timeout=30)

    def poll_setlist():
        raw_shows = collector.collect_shows()
        if collector._consecutive_failures:
            raise RuntimeError("Collector failed to fetch shows")
        shows_df = normalize_shows(raw_shows)
        if shows_df.empty:
            logger.info("No shows fetched.")
            return None

        target_show = shows_df[shows_df["show_date"] == target_date]
        if target_show.empty:
            logger.info("No show found for date %s.", target_date)
            return None

        show_id = str(target_show.iloc[0]["show_id"])
        if band == "phish":
            # The bulk collect_setlists method suppresses per-show failures.
            # Fetch this one show through the same adapter so failures propagate.
            raw_setlists = collector._fetch_phish_endpoint(f"setlists/showid/{show_id}")
        else:
            raw_setlists = collector.collect_setlists()
        # The shared collector returns [] for HTTP 403 and malformed JSON.
        if collector._consecutive_failures:
            raise RuntimeError("Collector failed to fetch setlists")
        setlists_df = normalize_setlists(raw_setlists)
        if setlists_df.empty:
            return None
        return setlists_df[setlists_df["show_id"].astype(str) == show_id]

    last_setlist = None
    consecutive_errors = 0
    successful_polls = 0
    for iteration in range(max_iterations):
        try:
            setlists_df = poll_setlist()
            if setlists_df is not None and not setlists_df.empty:
                # Phish generates created_at on every normalization. Compare stable
                # payloads in key order so response ordering cannot cause updates.
                current_setlist = (
                    setlists_df.drop(columns=["created_at"], errors="ignore")
                    .sort_values(conflict_cols)
                    .reset_index(drop=True)
                )
                if last_setlist is None or not current_setlist.equals(last_setlist):
                    validate_and_upsert_dataframe(
                        table_name=table_name,
                        df=setlists_df,
                        conflict_columns=conflict_cols,
                        required_columns=required_cols,
                        skip_validation=True,
                    )
                    logger.info(
                        "Upserted %s rows into %s.", len(setlists_df), table_name
                    )
                    if not generate_live_predictions(band=band):
                        raise RuntimeError(
                            "Live prediction generation did not complete"
                        )
                    last_setlist = current_setlist.copy()
                    logger.info("Predictions updated for the changed setlist.")
            consecutive_errors = 0
            successful_polls += 1
        except Exception as exc:
            consecutive_errors += 1
            logger.error("Polling failed (%s/3): %s", consecutive_errors, exc)
            if consecutive_errors >= 3:
                raise RuntimeError(
                    "Live tracker failed after three consecutive polling errors"
                ) from exc

        if iteration + 1 < max_iterations:
            logger.info("Sleeping for %ss...", interval)
            time.sleep(interval)

    if max_iterations > 0 and successful_polls == 0:
        raise RuntimeError("Live tracker finished without a successful poll")
    logger.info("Live tracker finished (max iterations reached).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the live show tracker for real-time predictions."
    )
    parser.add_argument(
        "--band", required=True, choices=["phish", "goose"], help="Band to track"
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
    args = parser.parse_args()
    run_live_tracker(
        band=args.band,
        target_date=args.date,
        interval=args.interval,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    main()
