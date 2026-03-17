"""Common utility functions for pipeline scripts."""

from __future__ import annotations

import sys
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

from src.jambandnerd.data_collection.config import get_collector_config

# Local imports
from src.jambandnerd.db.connection import get_supabase_client


def ensure_source_reachable(band: str, *, timeout: int = 15) -> None:
    """Perform a shallow health check for a band's data source.

    Args:
        band: Band identifier (goose/phish/etc.)
        timeout: Request timeout in seconds.

    Raises:
        RuntimeError: If the upstream endpoint is unreachable or returns a fatal error.
    """
    config = get_collector_config(band)
    url = config.base_url
    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": config.user_agent},
        )
        status = response.status_code
        # Treat any network-level errors or 5xx responses as fatal. 4xx responses imply the host is reachable.
        if status >= 500:
            raise RuntimeError(f"Received status {status} from {url}")
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to contact {url}: {exc}") from exc


def assert_required_columns(
    table_name: str, df: pd.DataFrame, columns: Iterable[str]
) -> None:
    """Ensure that a DataFrame contains the required columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise RuntimeError(
            f"{table_name} missing expected columns: {', '.join(missing)}"
        )


def prepare_band_data(
    shows_df: pd.DataFrame, setlists_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean and normalize shows and setlists data for a band.

    - Handles different column names for show_id and song_name.
    - Converts show_date to datetime.date objects.
    - Drops rows with null essential values.
    - Converts IDs to strings for consistency.
    """
    # Normalize column names
    if "api_show_id" in shows_df.columns and "show_id" not in shows_df.columns:
        shows_df["show_id"] = shows_df["api_show_id"]
    if "showdate" in shows_df.columns and "show_date" not in shows_df.columns:
        shows_df["show_date"] = shows_df["showdate"]
    if "api_show_id" in setlists_df.columns and "show_id" not in setlists_df.columns:
        setlists_df["show_id"] = setlists_df["api_show_id"]
    if "song" in setlists_df.columns and "song_name" not in setlists_df.columns:
        setlists_df["song_name"] = setlists_df["song"]

    # Data cleaning and type conversion
    shows_df["show_date"] = pd.to_datetime(
        shows_df["show_date"], errors="coerce"
    ).dt.date
    shows_df.dropna(subset=["show_date", "show_id"], inplace=True)
    setlists_df.dropna(subset=["show_id", "song_name"], inplace=True)

    shows_df["show_id"] = shows_df["show_id"].astype(str)
    setlists_df["show_id"] = setlists_df["show_id"].astype(str)

    return shows_df, setlists_df


def resolve_reference_date(
    date_str: str | None,
    shows_df: pd.DataFrame,
    *,
    upcoming_df: Optional[pd.DataFrame] = None,
) -> date:
    """
    Resolves the reference date for predictions.

    - If a specific date is provided, it is used directly.
    - If no date is provided or if the provided date is today, the function
      finds the date of the next upcoming show in the dataset.
    """
    today = date.today()
    target_date = today
    is_today = True

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if target_date != today:
                is_today = False
        except ValueError:
            print(f"Error: Invalid date format '{date_str}'. Please use YYYY-MM-DD.")
            sys.exit(1)

    if is_today:
        # Ensure _show_date_dt is created on a copy to avoid SettingWithCopyWarning
        shows_df_copy = shows_df.copy()
        shows_df_copy["_show_date_dt"] = pd.to_datetime(
            shows_df_copy["show_date"]
        ).dt.normalize()
        today_ts = pd.Timestamp(today).normalize()
        future_shows = shows_df_copy[shows_df_copy["_show_date_dt"] >= today_ts]

        if not future_shows.empty:
            next_show_date = future_shows["_show_date_dt"].min()
            print(
                f"No specific date provided; defaulting to next upcoming show: {next_show_date.date().isoformat()}"
            )
            return next_show_date.date()

        if upcoming_df is not None and not upcoming_df.empty:
            upcoming_copy = upcoming_df.copy()
            for column in ("show_date", "starts_at", "starts_at_local"):
                if column not in upcoming_copy.columns:
                    continue
                parsed = pd.to_datetime(upcoming_copy[column], errors="coerce")
                if parsed.isna().all():
                    continue
                future_candidates = [
                    d.date() for d in parsed.dropna() if d.date() >= today
                ]
                if future_candidates:
                    next_show = min(future_candidates)
                    print(
                        "Using upcoming shows table for next show date: "
                        f"{next_show.isoformat()}"
                    )
                    return next_show

        # Fallback: use most recent past show when no future shows are available
        past_shows = shows_df_copy[shows_df_copy["_show_date_dt"] < today_ts]
        if past_shows.empty:
            print("Error: No shows found in the database to use as a reference.")
            sys.exit(1)
        last_show_date = past_shows["_show_date_dt"].max()
        print(
            f"No future shows found; defaulting to most recent past show: {last_show_date.date().isoformat()}"
        )
        return last_show_date.date()
    else:
        # If a specific historical date is given, use it
        print(f"Using specified historical date: {target_date.isoformat()}")
        return target_date


def fetch_table(table_name: str, chunk_size: int = 10000) -> List[Dict]:
    """Fetch all rows from a Supabase table with robust, verbose pagination."""
    client = get_supabase_client()
    all_data = []
    offset = 0

    try:
        # Correctly pass count as a keyword argument
        count_response = (
            client.table(table_name).select("*", count="exact").limit(0).execute()
        )
        total_rows = count_response.count
        print(f"Found {total_rows} total rows in {table_name}.")
    except Exception as e:
        print(f"Could not get count from {table_name}: {e}. Fetching until empty.")
        total_rows = -1

    print(f"Fetching all records from {table_name} in chunks of {chunk_size}...")
    while True:
        try:
            print(f"Fetching rows from offset {offset}...")
            response = (
                client.table(table_name)
                .select("*")
                .range(offset, offset + chunk_size - 1)
                .execute()
            )

            if not response.data:
                print("Received no more data. Ending fetch.")
                break

            num_fetched = len(response.data)
            all_data.extend(response.data)
            print(f"Fetched {num_fetched} rows. Total so far: {len(all_data)}.")

            if total_rows != -1 and len(all_data) >= total_rows:
                print("Fetched all expected rows based on count. Ending fetch.")
                break
            if num_fetched < chunk_size:
                print("Fetched last chunk. Ending fetch.")
                break

            offset += num_fetched

        except Exception as e:
            print(f"An error occurred during fetch: {e}")
            break

    print(f"Fetched a total of {len(all_data)} records from {table_name}.")
    return all_data


# Backward compatibility alias for callers using the old private name
_fetch_table = fetch_table
