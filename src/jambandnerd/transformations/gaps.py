"""Band-agnostic transformations for show indices, gaps, and past-year aggregation.

This module provides utilities to:
- Compute a sequential show index based on chronological order.
- Compute per-song current gaps using show indices.
- Aggregate past-year song statistics required by the notebook model.
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
    window_start_date: Optional[date] = None
    window_end_date: Optional[date] = None
    plays_in_window: int = 0
    unique_songs_in_window: int = 0


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO-like date string to a date object."""
    if not value or pd.isna(value):
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _get_all_plays(shows_df: pd.DataFrame, setlists_df: pd.DataFrame) -> pd.DataFrame:
    """Merge shows and setlists and compute a stable chronological show index."""
    if shows_df.empty or setlists_df.empty:
        return pd.DataFrame()

    # 1. Prepare shows data and compute index
    shows = shows_df.copy()
    shows["show_id"] = shows["show_id"].astype(str)
    shows["_show_date_dt"] = shows["show_date"].apply(_parse_iso_date)
    shows = shows.dropna(subset=["_show_date_dt"])
    shows = shows.sort_values(by=["_show_date_dt", "show_id"]).reset_index(drop=True)
    shows["show_index"] = shows.index + 1
    show_idx_map = shows.set_index("show_id")["show_index"].to_dict()

    # 2. Prepare setlists and merge
    plays = setlists_df[["show_id", "song_name"]].copy()
    plays["show_id"] = plays["show_id"].astype(str)
    plays["show_index"] = plays["show_id"].map(show_idx_map)

    # 3. Merge with show dates
    show_dates = shows[["show_id", "_show_date_dt"]]
    plays = plays.merge(show_dates, on="show_id", how="left")

    return plays.dropna(subset=["_show_date_dt", "show_index", "song_name"])


def _resolve_reference_show(
    shows_df: pd.DataFrame, reference_show_date: date
) -> Tuple[int, date]:
    """Finds the reference show index for a given date, raising ValueError if not found."""
    shows_on_date = shows_df[shows_df["show_date"].apply(_parse_iso_date) == reference_show_date]
    if shows_on_date.empty:
        raise ValueError(f"Reference date {reference_show_date} does not exist in shows data.")

    # Re-compute index locally to find the correct reference index
    temp_shows = shows_df.copy()
    temp_shows["_show_date_dt"] = temp_shows["show_date"].apply(_parse_iso_date)
    temp_shows = temp_shows.dropna(subset=["_show_date_dt"])
    temp_shows = temp_shows.sort_values(by=["_show_date_dt", "show_id"]).reset_index(drop=True)
    temp_shows["show_index"] = temp_shows.index + 1

    latest_show_on_date = shows_on_date.sort_values(by="show_id").iloc[-1]
    ref_in_temp = temp_shows[temp_shows["show_id"] == latest_show_on_date["show_id"]]
    if ref_in_temp.empty:
        raise ValueError("Could not resolve reference index.")

    return int(ref_in_temp["show_index"].iloc[0]), reference_show_date


def _find_last_completed_show(
    plays_df: pd.DataFrame, ref_date: date
) -> Optional[Tuple[int, date]]:
    """Finds the last show with a setlist strictly before the reference date."""
    completed_shows = plays_df[plays_df["_show_date_dt"] < ref_date].copy()
    if completed_shows.empty:
        return None

    last_row = completed_shows.sort_values(by=["_show_date_dt", "show_index"]).iloc[-1]
    return int(last_row["show_index"]), last_row["_show_date_dt"]


def _aggregate_features_in_window(
    plays_df: pd.DataFrame, window_start: date, window_end: date, reference_index: int
) -> pd.DataFrame:
    """Computes per-song features within a date window."""
    plays_window = plays_df[
        (plays_df["_show_date_dt"] >= window_start) & (plays_df["_show_date_dt"] <= window_end)
    ]
    agg = plays_window.groupby("song_name", as_index=False).agg(
        plays_past_year=("song_name", "count"),
        last_played_date= ("_show_date_dt", "max"),
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
    # Normalize column names for Phish data
    if "api_show_id" in shows_df.columns and "show_id" not in shows_df.columns:
        shows_df["show_id"] = shows_df["api_show_id"]
    if "api_show_id" in setlists_df.columns and "show_id" not in setlists_df.columns:
        setlists_df["show_id"] = setlists_df["api_show_id"]
    if "showdate" in shows_df.columns and "show_date" not in shows_df.columns:
        shows_df["show_date"] = shows_df["showdate"]
    if "song" in setlists_df.columns and "song_name" not in setlists_df.columns:
        setlists_df["song_name"] = setlists_df["song"]

    plays_df = _get_all_plays(shows_df, setlists_df)
    if plays_df.empty:
        return PastYearAggregation(pd.DataFrame(), [], 0, date.today())

    reference_index, ref_date = _resolve_reference_show(shows_df, reference_show_date)

    last_completed = _find_last_completed_show(plays_df, ref_date)
    if not last_completed:
        return PastYearAggregation(pd.DataFrame(), [], reference_index, ref_date)
    last_idx, last_date = last_completed

    window_start = last_date - timedelta(days=365)
    
    # Capture window stats for diagnostics
    plays_in_window_df = plays_df[
        (plays_df["_show_date_dt"] >= window_start) & (plays_df["_show_date_dt"] <= last_date)
    ]
    plays_count = len(plays_in_window_df)
    unique_songs_count = plays_in_window_df["song_name"].nunique()

    agg_features = _aggregate_features_in_window(plays_df, window_start, last_date, reference_index)

    recent_songs = _get_recently_played_songs(plays_df, last_idx)
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
        latest_show_date=last_date, # Use the actual last completed date for diagnostics
        window_start_date=window_start,
        window_end_date=last_date,
        plays_in_window=plays_count,
        unique_songs_in_window=unique_songs_count,
    )