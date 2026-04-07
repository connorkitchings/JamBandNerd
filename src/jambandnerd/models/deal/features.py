"""Explainable Deal model feature engineering and training data builders."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from jambandnerd.config import BAND_EXCLUSION_WINDOWS, EXCLUSION_WINDOW_DEFAULT
from jambandnerd.transformations.gaps import ModelData

DEAL_FEATURE_COLUMNS: list[str] = [
    "current_gap",
    "avg_ltp",
    "recent_avg_ltp",
    "overdue_metric",
    "gap_z_score",
    "plays_past_year",
    "plays_past_2yr",
    "pct_shows_6mo",
    "pct_shows_1yr",
    "pct_shows_all_time",
    "diff_6mo_to_1yr",
    "diff_1yr_to_alltime",
    "n_shows_same_venue",
    "n_shows_same_state",
]


@dataclass
class DealTrainingSummary:
    total_rows: int
    positive_rows: int
    negative_rows: int
    sampled_show_count: int
    avg_candidates_per_show: float
    min_candidates_per_show: int
    max_candidates_per_show: int


def _clean_plays(plays: pd.DataFrame) -> pd.DataFrame:
    if plays.empty:
        return plays

    cleaned = plays.copy()
    cleaned["show_date"] = pd.to_datetime(cleaned["show_date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["show_date", "song_name", "show_index"])
    cleaned["show_index"] = cleaned["show_index"].astype(int)
    for column in ["venue_name", "state"]:
        if column not in cleaned.columns:
            cleaned[column] = None
    return cleaned


def _compute_ltp_features(
    plays_idx: List[int], reference_index: int
) -> Dict[str, float]:
    if not plays_idx:
        return {
            "avg_ltp": 0.0,
            "recent_avg_ltp": 0.0,
            "overdue_metric": 0.0,
            "gap_z_score": 0.0,
            "current_gap": 0,
        }

    gaps = [plays_idx[i] - plays_idx[i - 1] for i in range(1, len(plays_idx))]
    recent_gaps = gaps[-10:] if len(gaps) >= 10 else gaps
    avg_ltp = float(np.mean(gaps)) if gaps else 0.0
    recent_avg_ltp = float(np.mean(recent_gaps)) if recent_gaps else avg_ltp
    current_gap = reference_index - plays_idx[-1]
    std_gap = float(np.std(gaps, ddof=0)) if gaps else 0.0
    gap_z_score = (current_gap - avg_ltp) / std_gap if std_gap > 0 else 0.0

    return {
        "avg_ltp": avg_ltp,
        "recent_avg_ltp": recent_avg_ltp,
        "overdue_metric": current_gap / avg_ltp if avg_ltp > 0 else 0.0,
        "gap_z_score": gap_z_score,
        "current_gap": current_gap,
    }


def generate_deal_features(
    model_data: ModelData,
    min_plays_threshold: int = 5,
) -> pd.DataFrame:
    plays = _clean_plays(model_data.historical_plays)
    if plays.empty:
        return pd.DataFrame(
            columns=[
                "song_name",
                *DEAL_FEATURE_COLUMNS,
                "last_played_date",
                "total_plays",
            ]
        )

    reference_date = pd.Timestamp(model_data.reference_date)
    reference_index = model_data.reference_index
    features: list[dict[str, Any]] = []

    shows_in_6mo = max(
        1,
        plays[
            (plays["show_date"] >= reference_date - timedelta(days=182))
            & (plays["show_date"] < reference_date)
        ]["show_index"].nunique(),
    )
    shows_in_1yr = max(
        1,
        plays[
            (plays["show_date"] >= reference_date - timedelta(days=365))
            & (plays["show_date"] < reference_date)
        ]["show_index"].nunique(),
    )
    total_shows = max(1, plays["show_index"].nunique())

    for song_name, song_plays in plays.groupby("song_name"):
        plays_idx = sorted(song_plays["show_index"].unique().tolist())
        if len(plays_idx) < min_plays_threshold:
            continue

        n_shows_6mo = song_plays[
            song_plays["show_date"] >= reference_date - timedelta(days=182)
        ]["show_index"].nunique()
        n_shows_1yr = song_plays[
            song_plays["show_date"] >= reference_date - timedelta(days=365)
        ]["show_index"].nunique()
        n_shows_2yr = song_plays[
            song_plays["show_date"] >= reference_date - timedelta(days=730)
        ]["show_index"].nunique()

        ltp = _compute_ltp_features(plays_idx, reference_index)
        total_plays = len(plays_idx)
        pct_shows_6mo = n_shows_6mo / shows_in_6mo
        pct_shows_1yr = n_shows_1yr / shows_in_1yr
        pct_shows_all_time = total_plays / total_shows

        last_play_row = song_plays.sort_values("show_index").iloc[-1]
        venue_name = last_play_row.get("venue_name")
        state = last_play_row.get("state")

        features.append(
            {
                "song_name": song_name,
                "current_gap": ltp["current_gap"],
                "avg_ltp": ltp["avg_ltp"],
                "recent_avg_ltp": ltp["recent_avg_ltp"],
                "overdue_metric": ltp["overdue_metric"],
                "gap_z_score": ltp["gap_z_score"],
                "plays_past_year": int(n_shows_1yr),
                "plays_past_2yr": int(n_shows_2yr),
                "pct_shows_6mo": pct_shows_6mo,
                "pct_shows_1yr": pct_shows_1yr,
                "pct_shows_all_time": pct_shows_all_time,
                "diff_6mo_to_1yr": pct_shows_6mo - pct_shows_1yr,
                "diff_1yr_to_alltime": pct_shows_1yr - pct_shows_all_time,
                "n_shows_same_venue": (
                    int(
                        song_plays[song_plays["venue_name"] == venue_name][
                            "show_index"
                        ].nunique()
                    )
                    if venue_name
                    else 0
                ),
                "n_shows_same_state": (
                    int(
                        song_plays[song_plays["state"] == state]["show_index"].nunique()
                    )
                    if state
                    else 0
                ),
                "last_played_date": pd.Timestamp(last_play_row["show_date"]),
                "total_plays": int(total_plays),
            }
        )

    return pd.DataFrame(features)


def get_candidate_features(
    model_data: ModelData,
    min_plays_threshold: int = 5,
    retired_gap_threshold: int = 150,
) -> pd.DataFrame:
    features = generate_deal_features(model_data, min_plays_threshold)
    if features.empty:
        return features

    recently_played = set(model_data.recently_played_songs)
    features = features[~features["song_name"].isin(recently_played)]
    features = features[features["current_gap"] <= retired_gap_threshold]
    features = features[features["current_gap"] > 1]
    return features.reset_index(drop=True)


def build_training_frame(
    model_data: ModelData,
    *,
    band: str,
    min_plays_threshold: int,
    retired_gap_threshold: int,
    min_training_shows: int,
    training_window_shows: int,
) -> Tuple[pd.DataFrame, DealTrainingSummary]:
    plays = _clean_plays(model_data.historical_plays)
    empty_summary = DealTrainingSummary(0, 0, 0, 0, 0.0, 0, 0)
    if plays.empty:
        return (
            pd.DataFrame(columns=[*DEAL_FEATURE_COLUMNS, "song_name", "label"]),
            empty_summary,
        )

    exclusion_window = BAND_EXCLUSION_WINDOWS.get(band, EXCLUSION_WINDOW_DEFAULT)
    show_indices = sorted(plays["show_index"].unique().tolist())
    if len(show_indices) <= min_training_shows:
        return (
            pd.DataFrame(columns=[*DEAL_FEATURE_COLUMNS, "song_name", "label"]),
            empty_summary,
        )

    start_offset = max(min_training_shows, len(show_indices) - training_window_shows)
    target_indices = show_indices[start_offset:]
    rows: list[pd.DataFrame] = []
    candidate_counts: list[int] = []

    for target_show_index in target_indices:
        history = plays[plays["show_index"] < target_show_index].copy()
        if history["show_index"].nunique() < min_training_shows:
            continue

        target_rows = plays[plays["show_index"] == target_show_index]
        if target_rows.empty:
            continue

        recent_window_start = max(1, target_show_index - exclusion_window)
        recently_played = sorted(
            set(
                history[
                    history["show_index"].between(
                        recent_window_start, target_show_index - 1
                    )
                ]["song_name"].tolist()
            )
        )

        sub_model_data = ModelData(
            historical_plays=history,
            master_feature_set=pd.DataFrame(),
            reference_date=target_rows["show_date"].iloc[0].date(),
            reference_index=target_show_index,
            recently_played_songs=recently_played,
            diagnostics={
                "reference_date": target_rows["show_date"].iloc[0].date().isoformat(),
                "reference_index": target_show_index,
            },
        )

        candidates = get_candidate_features(
            sub_model_data,
            min_plays_threshold=min_plays_threshold,
            retired_gap_threshold=retired_gap_threshold,
        )
        if candidates.empty:
            continue

        actual_songs = set(target_rows["song_name"].astype(str))
        candidate_counts.append(len(candidates))
        candidates = candidates.copy()
        candidates["label"] = candidates["song_name"].isin(actual_songs).astype(int)
        candidates["target_show_index"] = target_show_index
        candidates["target_show_date"] = (
            target_rows["show_date"].iloc[0].date().isoformat()
        )
        rows.append(candidates)

    if not rows:
        return (
            pd.DataFrame(columns=[*DEAL_FEATURE_COLUMNS, "song_name", "label"]),
            empty_summary,
        )

    training_frame = pd.concat(rows, ignore_index=True)
    label_counts = Counter(training_frame["label"].tolist())
    candidate_summary = DealTrainingSummary(
        total_rows=len(training_frame),
        positive_rows=int(label_counts.get(1, 0)),
        negative_rows=int(label_counts.get(0, 0)),
        sampled_show_count=len(candidate_counts),
        avg_candidates_per_show=(
            float(np.mean(candidate_counts)) if candidate_counts else 0.0
        ),
        min_candidates_per_show=min(candidate_counts) if candidate_counts else 0,
        max_candidates_per_show=max(candidate_counts) if candidate_counts else 0,
    )
    return training_frame, candidate_summary


def summarize_training_summary(summary: DealTrainingSummary) -> Dict[str, Any]:
    return asdict(summary)
