"""Common utility functions for pipeline scripts."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

# Local imports


def completed_show_window(
    *, today: date | None = None, days: int = 7
) -> tuple[str, str]:
    """Return the recent completed-show window, excluding today."""
    today = today or date.today()
    cutoff = today - timedelta(days=days)
    end_date = today - timedelta(days=1)
    return cutoff.isoformat(), end_date.isoformat()


def batched_values(values: Iterable[Any], batch_size: int = 50) -> List[List[Any]]:
    """Split values into stable batches for Supabase `in_` queries."""
    items = list(values)
    return [items[idx : idx + batch_size] for idx in range(0, len(items), batch_size)]


def ensure_source_reachable(band: str, *, timeout: int = 15) -> None:
    """Perform a shallow health check for a band's data source.

    Args:
        band: Band identifier (goose/phish/etc.)
        timeout: Request timeout in seconds.

    Raises:
        RuntimeError: If the upstream endpoint is unreachable or returns a fatal error.
    """
    import requests

    from src.jambandnerd.data_collection.config import get_collector_config

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
    shows_df: pd.DataFrame, setlists_df: pd.DataFrame, *, band: str | None = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean and normalize shows and setlists data for a band.

    This is the shared normalization boundary for prediction scripts.
    """
    from src.jambandnerd.config.bands import (
        get_excluded_prediction_show_dates,
        get_excluded_prediction_show_ids,
    )
    from src.jambandnerd.transformations.normalization import (
        normalize_prediction_inputs,
    )

    prepared_shows, prepared_setlists = normalize_prediction_inputs(
        shows_df, setlists_df, band=band
    )

    if not band:
        return prepared_shows, prepared_setlists

    excluded_show_ids = set(get_excluded_prediction_show_ids(band))

    excluded_dates = get_excluded_prediction_show_dates(band)
    if excluded_dates:
        show_dates = pd.to_datetime(
            prepared_shows["show_date"], errors="coerce"
        ).dt.date
        date_mask = show_dates.astype(str).isin(excluded_dates)
        excluded_show_ids.update(prepared_shows.loc[date_mask, "show_id"].astype(str))

    if not excluded_show_ids:
        return prepared_shows, prepared_setlists

    prepared_show_ids = prepared_shows["show_id"].astype(str)
    excluded_mask = prepared_show_ids.isin(excluded_show_ids)
    if not excluded_mask.any():
        return prepared_shows, prepared_setlists

    filtered_shows = prepared_shows.loc[~excluded_mask].copy()
    filtered_setlists = prepared_setlists[
        ~prepared_setlists["show_id"].astype(str).isin(excluded_show_ids)
    ].copy()
    return filtered_shows, filtered_setlists


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
    from src.jambandnerd.db.connection import get_supabase_client

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


def fetch_table_rows(
    table_name: str,
    *,
    select: str = "*",
    filters: Iterable[tuple[str, str, Any]] | None = None,
    order_by: Iterable[tuple[str, bool]] | None = None,
    chunk_size: int = 1000,
    limit: int | None = None,
    client=None,
) -> List[Dict]:
    """Fetch rows from a Supabase table with pagination and optional filters."""
    from src.jambandnerd.db.connection import get_supabase_client

    client = client or get_supabase_client()
    rows: List[Dict] = []
    offset = 0
    remaining = limit

    while True:
        page_size = chunk_size if remaining is None else min(chunk_size, remaining)
        if page_size <= 0:
            break

        query = client.table(table_name).select(select)
        for operator, column, value in filters or []:
            if operator == "eq":
                query = query.eq(column, value)
            elif operator == "gte":
                query = query.gte(column, value)
            elif operator == "lte":
                query = query.lte(column, value)
            elif operator == "in":
                query = query.in_(column, value)
            else:
                raise ValueError(f"Unsupported filter operator: {operator}")

        for column, desc in order_by or []:
            query = query.order(column, desc=desc)

        response = query.range(offset, offset + page_size - 1).execute()
        page_rows = response.data or []
        rows.extend(page_rows)

        if remaining is not None:
            remaining -= len(page_rows)

        if not page_rows or len(page_rows) < page_size:
            break

        offset += len(page_rows)

    return rows


def fetch_column_values_for_ids(
    table_name: str,
    *,
    id_column: str,
    ids: Iterable[Any],
    select_column: str | None = None,
    batch_size: int = 50,
    client=None,
) -> set[str]:
    """Fetch selected column values for a set of IDs using batched `in_` queries."""
    from src.jambandnerd.db.connection import get_supabase_client

    query_ids = [value for value in ids if value is not None]
    if not query_ids:
        return set()

    client = client or get_supabase_client()
    select_column = select_column or id_column
    values: set[str] = set()

    for chunk in batched_values(query_ids, batch_size=batch_size):
        response = (
            client.table(table_name)
            .select(select_column)
            .in_(id_column, chunk)
            .execute()
        )
        for item in response.data or []:
            value = item.get(select_column)
            if value is not None:
                values.add(str(value))

    return values


# Backward compatibility alias for callers using the old private name
_fetch_table = fetch_table
