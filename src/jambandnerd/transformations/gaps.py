"""Goose transformations for show indices, gaps, and past-year aggregation.

This module provides utilities to:
- Compute a sequential show index based on chronological order
- Compute per-song current gaps using show indices
- Aggregate past-year song statistics required by the notebook model
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO-like date string to date.

    Args:
        value: Date string (e.g., 'YYYY-MM-DD').

    Returns:
        A date object or None if parsing fails.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def compute_show_index(shows_df: pd.DataFrame) -> Dict[str, int]:
    """Compute a stable sequential index for shows.

    Orders by `show_date` ascending, then by `show_id` as a deterministic tie-breaker.

    Args:
        shows_df: DataFrame with columns `show_id` (str/int) and `show_date` (str ISO).

    Returns:
        Mapping of show_id (as str) to sequential index starting at 1.
    """
    if shows_df.empty:
        return {}

    working = shows_df.copy()
    # Normalize types
    working["show_id"] = working["show_id"].astype(str)
    working["_show_date_dt"] = working["show_date"].apply(_parse_iso_date)

    # Drop rows without parseable dates
    working = working.dropna(subset=["_show_date_dt"])

    working = working.sort_values(by=["_show_date_dt", "show_id"]).reset_index(drop=True)
    show_index: Dict[str, int] = {}
    for idx, row in working.iterrows():
        show_index[row["show_id"]] = idx + 1
    return show_index


def _latest_show_context(shows_df: pd.DataFrame, show_index: Dict[str, int]) -> Tuple[Optional[date], Optional[int], Optional[str]]:
    """Get the latest show date, index, and id available in the dataset."""
    if shows_df.empty or not show_index:
        return None, None, None
    working = shows_df.copy()
    working["_show_date_dt"] = working["show_date"].apply(_parse_iso_date)
    working = working.dropna(subset=["_show_date_dt"])
    working["show_id"] = working["show_id"].astype(str)
    working = working.sort_values(by=["_show_date_dt", "show_id"]).reset_index(drop=True)
    latest_row = working.iloc[-1]
    latest_id = latest_row["show_id"]
    latest_date = latest_row["_show_date_dt"]
    latest_idx = show_index.get(str(latest_id))
    return latest_date, latest_idx, str(latest_id)


@dataclass
class PastYearAggregation:
    """Container for past-year aggregation outputs required by the notebook model."""

    features: pd.DataFrame
    excluded_recent_songs: List[str]
    latest_show_index: int
    latest_show_date: date


def aggregate_past_year_for_notebook(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_show_date: date,
) -> PastYearAggregation:
    """Compute past-year features for the notebook model.

    Steps:
    - Build sequential show indices
    - Determine reference show/date (latest in data or provided)
    - Filter setlists to the past year window
    - Compute per-song: plays_past_year, last_played_date, last_played_show_index, current_gap
    - Exclude songs played in the last 3 shows
    - Order by plays descending

    Args:
        shows_df: DataFrame of shows with `show_id`, `show_date` columns.
        setlists_df: DataFrame of setlists with `show_id`, `song_name` columns.
        reference_date: Optional date; if None, uses latest show date in data.

    Returns:
        PastYearAggregation dataclass with features and context.
    """
    if shows_df.empty or setlists_df.empty:
        return PastYearAggregation(pd.DataFrame(), [], 0, date.today())

    # Compute show index
    show_idx_map = compute_show_index(shows_df)
    latest_date, latest_index, latest_show_id = _latest_show_context(shows_df, show_idx_map)
    if latest_date is None or latest_index is None:
        return PastYearAggregation(pd.DataFrame(), [], 0, date.today())

    # Normalize and resolve the reference show by date (must exist in shows)
    shows_slim_base = shows_df[["show_id", "show_date"]].copy()
    shows_slim_base["show_id"] = shows_slim_base["show_id"].astype(str)
    shows_slim_base["_show_date_dt"] = shows_slim_base["show_date"].apply(_parse_iso_date)
    shows_slim_base = shows_slim_base.dropna(subset=["_show_date_dt"])  # type: ignore[arg-type]

    # Validate reference date exists in shows and resolve to the latest show_id on that date
    ref_candidates = shows_slim_base[shows_slim_base["_show_date_dt"] == reference_show_date]
    if ref_candidates.empty:
        raise ValueError("reference_show_date does not exist in shows data")
    ref_row = ref_candidates.sort_values(by=["show_id"]).iloc[-1]
    reference_index = int(show_idx_map[str(ref_row["show_id"])])
    ref_date = reference_show_date

    # Determine last completed show as the most recent show with setlist strictly before the reference date
    completed_show_ids = setlists_df[["show_id"]].dropna()["show_id"].astype(str)
    completed_df = shows_slim_base.merge(
        completed_show_ids.to_frame(name="show_id").drop_duplicates(), on="show_id", how="inner"
    )
    completed_df = completed_df[completed_df["_show_date_dt"] < ref_date]
    if completed_df.empty:
        # No completed shows prior to reference; no features
        return PastYearAggregation(pd.DataFrame(), [], reference_index, ref_date)
    last_row = completed_df.sort_values(by=["_show_date_dt", "show_id"]).iloc[-1]
    last_idx = int(show_idx_map[str(last_row["show_id"])])
    last_date = last_row["_show_date_dt"]

    # Past-year window relative to the last completed show
    window_start = last_date - timedelta(days=365)

    # Attach show_date and show_index to setlists
    shows_slim = shows_df[["show_id", "show_date"]].copy()
    shows_slim["show_id"] = shows_slim["show_id"].astype(str)
    shows_slim["_show_date_dt"] = shows_slim["show_date"].apply(_parse_iso_date)
    shows_slim["show_index"] = shows_slim["show_id"].map(show_idx_map)

    plays = setlists_df[["show_id", "song_name"]].copy()
    plays["show_id"] = plays["show_id"].astype(str)
    plays = plays.merge(shows_slim, on="show_id", how="left")
    plays = plays.dropna(subset=["_show_date_dt", "show_index", "song_name"])  # type: ignore[arg-type]

    # Filter to last year window up to and including the last completed show
    plays_window = plays[(plays["_show_date_dt"] >= window_start) & (plays["_show_date_dt"] <= last_date)]

    # Compute last 3 completed shows and the songs played therein (strictly before reference)
    last3_indices = [i for i in range(max(1, last_idx - 2), last_idx + 1)]
    recent_mask = plays["show_index"].isin(last3_indices)
    recent_songs = sorted(set(plays.loc[recent_mask, "song_name"].tolist()))

    # Aggregations within the past-year window
    agg = (
        plays_window.groupby("song_name", as_index=False)
        .agg(
            plays_past_year=("song_name", "count"),
            last_played_date=("_show_date_dt", "max"),
            last_played_show_index=("show_index", "max"),
        )
    )

    # Current gap relative to the reference show index (reference_index - 1 - last_played)
    agg["current_gap"] = agg["last_played_show_index"].apply(lambda x: int((reference_index - 1) - int(x)))

    # Exclude songs played in last 3 shows
    filtered = agg[~agg["song_name"].isin(recent_songs)].copy()

    # Order by plays descending (tie-breaker: larger gap first, then alpha)
    filtered = filtered.sort_values(by=["plays_past_year", "current_gap", "song_name"], ascending=[False, False, True]).reset_index(drop=True)

    # Safeguard: Ensure last_played_date only reflects shows strictly before the reference show.
    # This should not be necessary if windowing logic is correct, but protects against edge cases.
    filtered.loc[filtered["last_played_show_index"] >= reference_index, "last_played_date"] = None
    filtered.loc[filtered["last_played_show_index"] >= reference_index, "last_played_show_index"] = None

    filtered["last_played_date"] = filtered["last_played_date"].apply(lambda d: d.isoformat() if isinstance(d, date) else None)

    return PastYearAggregation(
        features=filtered,
        excluded_recent_songs=recent_songs,
        latest_show_index=int(reference_index),
        latest_show_date=ref_date,
    )


