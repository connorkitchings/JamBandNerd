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


@dataclass
class PastYearAggregation:
    """Container for past-year aggregation outputs required by the notebook model."""

    features: pd.DataFrame
    excluded_recent_songs: List[str]
    latest_show_index: int
    latest_show_date: date


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO-like date string to a date object."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def compute_show_index(shows_df: pd.DataFrame) -> Dict[str, int]:
    """Compute a stable sequential index for shows, ordered chronologically."""
    if shows_df.empty:
        return {}
    working = shows_df.copy()
    working["show_id"] = working["show_id"].astype(str)
    working["_show_date_dt"] = working["show_date"].apply(_parse_iso_date)
    working = working.dropna(subset=["_show_date_dt"])
    working = working.sort_values(by=["_show_date_dt", "show_id"]).reset_index(drop=True)
    return {row["show_id"]: idx + 1 for idx, row in working.iterrows()}


def _resolve_reference_show(
    shows_df: pd.DataFrame, show_idx_map: Dict[str, int], reference_show_date: date
) -> Tuple[int, date]:
    """Finds the reference show index for a given date, raising ValueError if not found."""
    shows_on_date = shows_df[shows_df["show_date"].apply(_parse_iso_date) == reference_show_date]
    if shows_on_date.empty:
        raise ValueError(f"Reference date {reference_show_date} does not exist in shows data.")
    latest_show_on_date = shows_on_date.sort_values(by="show_id").iloc[-1]
    reference_index = show_idx_map[str(latest_show_on_date["show_id"])]
    return reference_index, reference_show_date


def _find_last_completed_show(
    shows_df: pd.DataFrame, setlists_df: pd.DataFrame, show_idx_map: Dict[str, int], ref_date: date
) -> Optional[Tuple[int, date]]:
    """Finds the last show with a setlist strictly before the reference date."""
    completed_show_ids = set(setlists_df["show_id"].dropna().astype(str))
    completed_shows = shows_df[
        (shows_df["show_id"].astype(str).isin(completed_show_ids))
        & (shows_df["show_date"].apply(_parse_iso_date) < ref_date)
    ].copy()
    if completed_shows.empty:
        return None
    completed_shows["_show_date_dt"] = completed_shows["show_date"].apply(_parse_iso_date)
    last_row = completed_shows.sort_values(by=["_show_date_dt", "show_id"]).iloc[-1]
    last_idx = show_idx_map[str(last_row["show_id"])]
    return last_idx, last_row["_show_date_dt"]


def _get_plays_with_indices(
    setlists_df: pd.DataFrame, shows_df: pd.DataFrame, show_idx_map: Dict[str, int]
) -> pd.DataFrame:
    """Merges setlists with show dates and indices, returning a clean DataFrame."""
    plays = setlists_df[["show_id", "song_name"]].copy()
    plays["show_id"] = plays["show_id"].astype(str)
    shows_slim = shows_df[["show_id", "show_date"]].copy()
    shows_slim["show_id"] = shows_slim["show_id"].astype(str)
    shows_slim["_show_date_dt"] = shows_slim["show_date"].apply(_parse_iso_date)
    shows_slim["show_index"] = shows_slim["show_id"].map(show_idx_map)
    plays = plays.merge(shows_slim, on="show_id", how="left")
    return plays.dropna(subset=["_show_date_dt", "show_index", "song_name"])


def _aggregate_features_in_window(
    plays_df: pd.DataFrame, window_start: date, window_end: date, reference_index: int
) -> pd.DataFrame:
    """Computes per-song features within a date window."""
    plays_window = plays_df[
        (plays_df["_show_date_dt"] >= window_start) & (plays_df["_show_date_dt"] <= window_end)
    ]
    agg = plays_window.groupby("song_name", as_index=False).agg(
        plays_past_year=("song_name", "count"),
        last_played_date=("_show_date_dt", "max"),
        last_played_show_index=("show_index", "max"),
    )
    agg["current_gap"] = agg["last_played_show_index"].apply(
        lambda x: (reference_index - 1) - int(x)
    )
    return agg


def _get_recently_played_songs(plays_df: pd.DataFrame, last_completed_index: int) -> List[str]:
    """Gets a list of unique songs played in the last 3 completed shows."""
    last3_indices = range(max(1, last_completed_index - 2), last_completed_index + 1)
    recent_mask = plays_df["show_index"].isin(last3_indices)
    return sorted(set(plays_df.loc[recent_mask, "song_name"].tolist()))


def aggregate_past_year_for_notebook(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_show_date: date,
) -> PastYearAggregation:
    """
    Computes past-year features for the notebook model by orchestrating data transformations.

    Args:
        shows_df: DataFrame of all shows.
        setlists_df: DataFrame of all setlists.
        reference_show_date: The date of the show to generate predictions for.

    Returns:
        A PastYearAggregation object containing the feature DataFrame and metadata.
    """
    if shows_df.empty or setlists_df.empty:
        return PastYearAggregation(pd.DataFrame(), [], 0, date.today())

    show_idx_map = compute_show_index(shows_df)
    if not show_idx_map:
        return PastYearAggregation(pd.DataFrame(), [], 0, date.today())

    reference_index, ref_date = _resolve_reference_show(
        shows_df, show_idx_map, reference_show_date
    )

    last_completed = _find_last_completed_show(shows_df, setlists_df, show_idx_map, ref_date)
    if not last_completed:
        return PastYearAggregation(pd.DataFrame(), [], reference_index, ref_date)
    last_idx, last_date = last_completed

    plays = _get_plays_with_indices(setlists_df, shows_df, show_idx_map)
    window_start = last_date - timedelta(days=365)
    agg_features = _aggregate_features_in_window(plays, window_start, last_date, reference_index)

    recent_songs = _get_recently_played_songs(plays, last_idx)
    filtered_features = agg_features[~agg_features["song_name"].isin(recent_songs)].copy()

    # Final sorting and formatting
    filtered_features = filtered_features.sort_values(
        by=["plays_past_year", "current_gap", "song_name"], ascending=[False, False, True]
    ).reset_index(drop=True)
    filtered_features["last_played_date"] = filtered_features["last_played_date"].apply(
        lambda d: d.isoformat() if isinstance(d, date) else None
    )

    return PastYearAggregation(
        features=filtered_features,
        excluded_recent_songs=recent_songs,
        latest_show_index=reference_index,
        latest_show_date=ref_date,
    )