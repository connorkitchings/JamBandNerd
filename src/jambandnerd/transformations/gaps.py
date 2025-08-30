"""Band-agnostic transformations for show indices, gaps, and other model features.

This module provides a centralized, refactored pipeline for computing all features
required by the various prediction models. It ensures that data leakage is prevented
by strictly adhering to a `reference_date` cutoff.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd


def _stats_for_song(group: pd.DataFrame) -> pd.Series:
    """Helper function to calculate historical stats for a single song."""
    plays_idx = sorted(group["show_index"].tolist())
    gaps = [plays_idx[i] - plays_idx[i - 1] for i in range(1, len(plays_idx))]
    return pd.Series({
        "times_played": len(plays_idx),
        "last_played_index": plays_idx[-1],
        "last_played_date": group["show_date"].max(),
        "avg_gap": pd.Series(gaps).mean() if gaps else float("nan"),
        "std_gap": pd.Series(gaps).std(ddof=0) if gaps else 0.0,
    })


@dataclass
class ModelData:
    """A container for all data required by prediction models."""

    # A DataFrame of all historical plays before the reference date.
    historical_plays: pd.DataFrame

    # A DataFrame of song features aggregated over their entire history.
    master_feature_set: pd.DataFrame

    # The specific date for which predictions are being generated.
    reference_date: date

    # The chronological index of the reference show.
    reference_index: int

    # A list of songs played in the 3 shows immediately preceding the reference date.
    recently_played_songs: List[str]

    # Diagnostic metadata.
    diagnostics: Dict[str, any]


def _parse_iso_date(value: Optional[str | date]) -> Optional[date]:
    """Safely parse a date-like value to a date object."""
    if isinstance(value, date):
        return value
    if not value or pd.isna(value):
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _compute_base_features(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date: date,
    debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, int, List[str]]:
    """
    First-pass feature engineering.
    """
    if debug:
        print("\n--- Debugging _compute_base_features ---")
        print(f"Initial shows_df shape: {shows_df.shape}")
        print(f"Initial setlists_df shape: {setlists_df.shape}")
        print(f"Reference date: {reference_date}")

    # 1. Set absolute cutoff date
    shows = shows_df.copy()
    shows["show_date"] = shows["show_date"].apply(_parse_iso_date)
    historical_shows = shows[shows["show_date"] < reference_date].copy()
    if debug:
        print(f"Shape after filtering for historical shows: {historical_shows.shape}")

    if historical_shows.empty:
        return pd.DataFrame(), pd.DataFrame(), 0, []

    # 2. Compute stable show index (normalize keys BEFORE building the index map)
    historical_shows = historical_shows.sort_values(
        by=["show_date", "show_id"]
    ).reset_index(drop=True)
    # Normalize ID types to strings for reliable joins
    historical_shows["show_id"] = historical_shows["show_id"].astype(str).str.strip()
    historical_shows["show_index"] = historical_shows.index + 1
    show_idx_map = historical_shows.set_index("show_id")["show_index"].to_dict()

    last_historical_index = historical_shows["show_index"].max()
    reference_index = last_historical_index + 1
    if debug:
        print(f"Computed reference_index: {reference_index}")

    # 3. Merge plays
    plays = setlists_df[["show_id", "song_name"]].copy()
    plays["show_id"] = plays["show_id"].astype(str).str.strip()
    map_keys = set(historical_shows["show_id"].unique())

    if debug:
        print(f"First 5 show_ids from historical_shows: {list(map_keys)[:5]}")
        print(f"First 5 show_ids from setlists_df: {plays['show_id'].unique()[:5]}")

    plays = plays[plays["show_id"].isin(map_keys)]
    if debug:
        print(f"Plays shape after filtering to historical shows: {plays.shape}")

    plays["show_index"] = plays["show_id"].map(show_idx_map)
    plays = plays.merge(
        historical_shows[["show_id", "show_date"]], on="show_id", how="left"
    )
    if debug:
        print(f"Plays shape after merging with show_date: {plays.shape}")
    plays.dropna(subset=["show_index", "song_name"], inplace=True)
    if debug:
        print(f"Plays shape after dropping NA: {plays.shape}")

    # 4. Calculate historical gap stats
    song_features = plays.groupby("song_name").apply(_stats_for_song, include_groups=False).reset_index()
    if debug:
        print(f"Shape of master_feature_set: {song_features.shape}")

    # 5. Identify recently played songs
    last_3_indices = range(max(1, last_historical_index - 2), last_historical_index + 1)
    recent_plays_mask = plays["show_index"].isin(last_3_indices)
    recently_played = sorted(set(plays.loc[recent_plays_mask, "song_name"].tolist()))
    if debug:
        print("--- End Debugging ---\n")

    return plays, song_features, reference_index, recently_played


def generate_model_data(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date: date,
    debug: bool = False
) -> ModelData:
    """
    Orchestrates the full feature generation pipeline.
    """
    # Clean and normalize column names first
    if "api_show_id" in shows_df.columns and "show_id" not in shows_df.columns:
        shows_df["show_id"] = shows_df["api_show_id"]
    if "showdate" in shows_df.columns and "show_date" not in shows_df.columns:
        shows_df["show_date"] = shows_df["showdate"]
    if "api_show_id" in setlists_df.columns and "show_id" not in setlists_df.columns:
        setlists_df["show_id"] = setlists_df["api_show_id"]
    if "song" in setlists_df.columns and "song_name" not in setlists_df.columns:
        setlists_df["song_name"] = setlists_df["song"]

    historical_plays, master_features, ref_index, recent_songs = _compute_base_features(
        shows_df, setlists_df, reference_date, debug
    )

    diagnostics = {
        "reference_date": reference_date.isoformat(),
        "reference_index": ref_index,
        "total_songs_in_history": len(master_features),
        "recently_played_count": len(recent_songs),
    }

    return ModelData(
        historical_plays=historical_plays,
        master_feature_set=master_features,
        reference_date=reference_date,
        reference_index=ref_index,
        recently_played_songs=recent_songs,
        diagnostics=diagnostics,
    )