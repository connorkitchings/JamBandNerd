"""Deal model feature engineering for ML predictions.

This module provides feature generation for the Deal XGBoost model,
extending the base features from transformations/gaps.py with ML-specific features.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.jambandnerd.transformations.gaps import ModelData


@dataclass
class DealFeatures:
    """Container for Deal model features for a single song."""

    song_name: str
    n_shows_6mo: int
    n_shows_1yr: int
    n_shows_2yr: int
    n_shows_4yr: int
    pct_shows_1yr: float
    pct_shows_2yr: float
    total_plays: int
    plays_past_year: int
    plays_past_2yr: int
    play_rate: float
    ltp_1: int
    ltp_2: int
    ltp_3: int
    ltp_4: int
    ltp_5: int
    ltp_6: int
    ltp_7: int
    ltp_8: int
    ltp_9: int
    ltp_10: int
    avg_ltp: float
    recent_avg_ltp: float
    overdue_metric: float
    ltp_trend: float
    std_gap: float
    min_gap: int
    max_gap: int
    gap_z_score: float
    current_gap: int
    days_since_last: int
    pct_shows_all_time: float
    pct_shows_6mo: float
    diff_6mo_to_1yr: float
    diff_1yr_to_alltime: float
    n_shows_same_venue: int
    n_shows_same_state: int
    pct_shows_same_venue: float
    pct_shows_same_state: float
    diff_same_venue_vs_alltime: float


def _compute_temporal_window_counts(
    plays: pd.DataFrame,
    show_dates: pd.Series,
    reference_date: pd.Timestamp,
    window_days: int,
) -> pd.Series:
    """Count unique shows in a time window."""
    window_start = reference_date - timedelta(days=window_days)
    mask = show_dates >= window_start
    return plays[mask].groupby("song_name")["show_index"].nunique()


def _compute_ltp_features(
    plays_idx: List[int],
    reference_index: int,
) -> Dict[str, float]:
    """Compute LTP (Last Time Played) features from sorted play indices."""
    if not plays_idx:
        return {
            "ltp_1": 0,
            "ltp_2": 0,
            "ltp_3": 0,
            "ltp_4": 0,
            "ltp_5": 0,
            "ltp_6": 0,
            "ltp_7": 0,
            "ltp_8": 0,
            "ltp_9": 0,
            "ltp_10": 0,
            "avg_ltp": 0.0,
            "recent_avg_ltp": 0.0,
            "overdue_metric": 0.0,
            "ltp_trend": 0.0,
        }

    gaps = [plays_idx[i] - plays_idx[i - 1] for i in range(1, len(plays_idx))]
    recent_gaps = gaps[-25:] if len(gaps) >= 25 else gaps

    ltp_1 = reference_index - plays_idx[-1] if plays_idx else 0
    ltp_2 = reference_index - plays_idx[-2] if len(plays_idx) >= 2 else 0
    ltp_3 = reference_index - plays_idx[-3] if len(plays_idx) >= 3 else 0
    ltp_4 = reference_index - plays_idx[-4] if len(plays_idx) >= 4 else 0
    ltp_5 = reference_index - plays_idx[-5] if len(plays_idx) >= 5 else 0
    ltp_6 = reference_index - plays_idx[-6] if len(plays_idx) >= 6 else 0
    ltp_7 = reference_index - plays_idx[-7] if len(plays_idx) >= 7 else 0
    ltp_8 = reference_index - plays_idx[-8] if len(plays_idx) >= 8 else 0
    ltp_9 = reference_index - plays_idx[-9] if len(plays_idx) >= 9 else 0
    ltp_10 = reference_index - plays_idx[-10] if len(plays_idx) >= 10 else 0

    avg_ltp = float(np.mean(gaps)) if gaps else 0.0
    recent_avg_ltp = float(np.mean(recent_gaps)) if recent_gaps else 0.0

    overdue_metric = ltp_1 / avg_ltp if avg_ltp > 0 else 0.0
    ltp_trend = recent_avg_ltp - avg_ltp

    return {
        "ltp_1": ltp_1,
        "ltp_2": ltp_2,
        "ltp_3": ltp_3,
        "ltp_4": ltp_4,
        "ltp_5": ltp_5,
        "ltp_6": ltp_6,
        "ltp_7": ltp_7,
        "ltp_8": ltp_8,
        "ltp_9": ltp_9,
        "ltp_10": ltp_10,
        "avg_ltp": avg_ltp,
        "recent_avg_ltp": recent_avg_ltp,
        "overdue_metric": overdue_metric,
        "ltp_trend": ltp_trend,
    }


def _compute_gap_stats(plays_idx: List[int]) -> Dict[str, float]:
    """Compute gap statistics from sorted play indices."""
    if not plays_idx or len(plays_idx) < 2:
        return {
            "std_gap": 0.0,
            "min_gap": 0,
            "max_gap": 0,
        }

    gaps = [plays_idx[i] - plays_idx[i - 1] for i in range(1, len(plays_idx))]
    return {
        "std_gap": float(np.std(gaps, ddof=0)) if gaps else 0.0,
        "min_gap": int(min(gaps)) if gaps else 0,
        "max_gap": int(max(gaps)) if gaps else 0,
    }


def generate_deal_features(
    model_data: ModelData,
    min_plays_threshold: int = 5,
) -> pd.DataFrame:
    """Generate ML features for the Deal model.

    Args:
        model_data: ModelData container with historical plays and master features
        min_plays_threshold: Minimum plays required for a song to be a candidate

    Returns:
        DataFrame with Deal-specific features per song
    """
    plays = model_data.historical_plays
    reference_date = pd.Timestamp(model_data.reference_date)
    reference_index = model_data.reference_index

    if plays.empty:
        return pd.DataFrame()

    plays = plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")
    plays = plays.dropna(subset=["show_date", "song_name"])

    features = []

    for song_name, song_plays in plays.groupby("song_name"):
        plays_idx = sorted(song_plays["show_index"].unique().tolist())

        if len(plays_idx) < min_plays_threshold:
            continue

        last_played_date = song_plays["show_date"].max()
        total_plays = len(plays_idx)

        n_shows_1yr = len(
            song_plays[song_plays["show_date"] >= reference_date - timedelta(days=365)][
                "show_index"
            ].unique()
        )
        n_shows_2yr = len(
            song_plays[song_plays["show_date"] >= reference_date - timedelta(days=730)][
                "show_index"
            ].unique()
        )
        n_shows_4yr = len(
            song_plays[
                song_plays["show_date"] >= reference_date - timedelta(days=1460)
            ]["show_index"].unique()
        )
        n_shows_6mo = len(
            song_plays[song_plays["show_date"] >= reference_date - timedelta(days=182)][
                "show_index"
            ].unique()
        )

        shows_in_1yr = len(
            plays[
                (plays["show_date"] >= reference_date - timedelta(days=365))
                & (plays["show_date"] < reference_date)
            ]["show_index"].unique()
        )
        shows_in_2yr = len(
            plays[
                (plays["show_date"] >= reference_date - timedelta(days=730))
                & (plays["show_date"] < reference_date)
            ]["show_index"].unique()
        )
        shows_in_6mo = len(
            plays[
                (plays["show_date"] >= reference_date - timedelta(days=182))
                & (plays["show_date"] < reference_date)
            ]["show_index"].unique()
        )
        total_shows = len(plays["show_index"].unique())

        pct_shows_1yr = n_shows_1yr / shows_in_1yr if shows_in_1yr > 0 else 0.0
        pct_shows_2yr = n_shows_2yr / shows_in_2yr if shows_in_2yr > 0 else 0.0
        pct_shows_6mo = n_shows_6mo / shows_in_6mo if shows_in_6mo > 0 else 0.0
        pct_shows_all_time = n_shows_1yr / total_shows if total_shows > 0 else 0.0

        plays_past_year = n_shows_1yr
        plays_past_2yr = n_shows_2yr
        play_rate = plays_past_year / total_plays if total_plays > 0 else 0.0

        diff_6mo_to_1yr = pct_shows_6mo - pct_shows_1yr
        diff_1yr_to_alltime = pct_shows_1yr - pct_shows_all_time

        venue_name = (
            song_plays["venue_name"].iloc[0]
            if "venue_name" in song_plays.columns
            else None
        )
        state = song_plays["state"].iloc[0] if "state" in song_plays.columns else None

        n_shows_same_venue = (
            len(
                song_plays[song_plays["venue_name"] == venue_name][
                    "show_index"
                ].unique()
            )
            if venue_name
            else 0
        )
        n_shows_same_state = (
            len(song_plays[song_plays["state"] == state]["show_index"].unique())
            if state
            else 0
        )

        total_venues = (
            len(plays["venue_name"].unique()) if "venue_name" in plays.columns else 1
        )
        total_states = len(plays["state"].unique()) if "state" in plays.columns else 1

        pct_shows_same_venue = (
            n_shows_same_venue / total_venues if total_venues > 0 else 0.0
        )
        pct_shows_same_state = (
            n_shows_same_state / total_states if total_states > 0 else 0.0
        )
        diff_same_venue_vs_alltime = pct_shows_same_venue - pct_shows_all_time

        ltp_features = _compute_ltp_features(plays_idx, reference_index)
        gap_stats = _compute_gap_stats(plays_idx)

        avg_ltp = ltp_features["avg_ltp"]
        std_gap = gap_stats["std_gap"]
        current_gap = ltp_features["ltp_1"]

        gap_z_score = (current_gap - avg_ltp) / std_gap if std_gap > 0 else 0.0

        days_since_last = (reference_date - last_played_date).days

        features.append(
            {
                "song_name": song_name,
                "n_shows_6mo": n_shows_6mo,
                "n_shows_1yr": n_shows_1yr,
                "n_shows_2yr": n_shows_2yr,
                "n_shows_4yr": n_shows_4yr,
                "pct_shows_1yr": pct_shows_1yr,
                "pct_shows_2yr": pct_shows_2yr,
                "total_plays": total_plays,
                "plays_past_year": plays_past_year,
                "plays_past_2yr": plays_past_2yr,
                "play_rate": play_rate,
                "ltp_1": ltp_features["ltp_1"],
                "ltp_2": ltp_features["ltp_2"],
                "ltp_3": ltp_features["ltp_3"],
                "ltp_4": ltp_features.get("ltp_4", 0),
                "ltp_5": ltp_features.get("ltp_5", 0),
                "ltp_6": ltp_features.get("ltp_6", 0),
                "ltp_7": ltp_features.get("ltp_7", 0),
                "ltp_8": ltp_features.get("ltp_8", 0),
                "ltp_9": ltp_features.get("ltp_9", 0),
                "ltp_10": ltp_features.get("ltp_10", 0),
                "avg_ltp": ltp_features["avg_ltp"],
                "recent_avg_ltp": ltp_features["recent_avg_ltp"],
                "overdue_metric": ltp_features["overdue_metric"],
                "ltp_trend": ltp_features["ltp_trend"],
                "std_gap": gap_stats["std_gap"],
                "min_gap": gap_stats["min_gap"],
                "max_gap": gap_stats["max_gap"],
                "gap_z_score": gap_z_score,
                "current_gap": current_gap,
                "days_since_last": days_since_last,
                "pct_shows_all_time": pct_shows_all_time,
                "pct_shows_6mo": pct_shows_6mo,
                "diff_6mo_to_1yr": diff_6mo_to_1yr,
                "diff_1yr_to_alltime": diff_1yr_to_alltime,
                "n_shows_same_venue": n_shows_same_venue,
                "n_shows_same_state": n_shows_same_state,
                "pct_shows_same_venue": pct_shows_same_venue,
                "pct_shows_same_state": pct_shows_same_state,
                "diff_same_venue_vs_alltime": diff_same_venue_vs_alltime,
                "last_played_date": last_played_date,
            }
        )

    return pd.DataFrame(features)


def generate_training_data(
    model_data: ModelData,
    test_show_indices: List[int],
    min_plays_threshold: int = 5,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Generate training data for Deal model.

    Creates (song, show) pairs with features and binary labels.

    Args:
        model_data: ModelData container
        test_show_indices: Show indices to use for test set
        min_plays_threshold: Minimum plays required

    Returns:
        Tuple of (features DataFrame, labels Series)
    """
    all_features = generate_deal_features(model_data, min_plays_threshold)

    if all_features.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    plays = model_data.historical_plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")

    test_shows = plays[plays["show_index"].isin(test_show_indices)]

    positive_songs = set(test_shows["song_name"].unique())

    labels = []
    for song in all_features["song_name"]:
        labels.append(1 if song in positive_songs else 0)

    all_features["label"] = labels

    return all_features, all_features["label"]


def get_candidate_features(
    model_data: ModelData,
    min_plays_threshold: int = 5,
    retired_gap_threshold: int = 150,
) -> pd.DataFrame:
    """Get features for songs that are candidates for prediction.

    Excludes songs played in recent shows and retired songs.

    Args:
        model_data: ModelData container
        min_plays_threshold: Minimum plays required
        retired_gap_threshold: Maximum gap before song is considered retired

    Returns:
        DataFrame of candidate song features
    """
    features = generate_deal_features(model_data, min_plays_threshold)

    if features.empty:
        return pd.DataFrame()

    recently_played = set(model_data.recently_played_songs)
    features = features[~features["song_name"].isin(recently_played)]
    features = features[features["current_gap"] <= retired_gap_threshold]
    features = features[features["current_gap"] > 1]

    return features
