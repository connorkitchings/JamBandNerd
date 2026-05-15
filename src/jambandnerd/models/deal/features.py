"""Explainable Deal model feature engineering and training data builders."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from jambandnerd.config import BAND_EXCLUSION_WINDOWS, EXCLUSION_WINDOW_DEFAULT
from jambandnerd.models.evaluation import get_evaluation_reference_date
from jambandnerd.transformations.cooccurrence import (
    COOCCURRENCE_FEATURES as _COOCCURRENCE_FEATURES,
)
from jambandnerd.transformations.cooccurrence import (
    compute_cooccurrence_features as _compute_cooccurrence_features,
)
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.run_context import normalize_target_show_context
from jambandnerd.transformations.set_position import (
    SET_POSITION_FEATURES as _SET_POSITION_FEATURES,
)
from jambandnerd.transformations.set_position import (
    compute_set_position_features as _compute_set_position_features,
)

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
    "debut_age_shows",
    "career_play_pct",
    "novelty_rank",
    *_SET_POSITION_FEATURES,
    *_COOCCURRENCE_FEATURES,
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
    # current_gap counts completed shows since the last play, not the target show itself.
    current_gap = max(reference_index - plays_idx[-1] - 1, 0)
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
                "recent_plays_50",
                "last_played_date",
                "total_plays",
            ]
        )

    reference_date = pd.Timestamp(model_data.reference_date)
    reference_index = model_data.reference_index

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

    song_show_counts = plays.groupby("song_name")["show_index"].nunique()
    eligible_songs = song_show_counts[song_show_counts >= min_plays_threshold].index

    if eligible_songs.empty:
        return pd.DataFrame(
            columns=[
                "song_name",
                *DEAL_FEATURE_COLUMNS,
                "recent_plays_50",
                "last_played_date",
                "total_plays",
            ]
        )

    mask_6mo = (plays["show_date"] >= reference_date - timedelta(days=182)) & (
        plays["show_date"] < reference_date
    )
    mask_1yr = (plays["show_date"] >= reference_date - timedelta(days=365)) & (
        plays["show_date"] < reference_date
    )
    mask_2yr = (plays["show_date"] >= reference_date - timedelta(days=730)) & (
        plays["show_date"] < reference_date
    )

    n_6mo = (
        plays[mask_6mo]
        .groupby("song_name")["show_index"]
        .nunique()
        .reindex(eligible_songs, fill_value=0)
    )
    n_1yr = (
        plays[mask_1yr]
        .groupby("song_name")["show_index"]
        .nunique()
        .reindex(eligible_songs, fill_value=0)
    )
    n_2yr = (
        plays[mask_2yr]
        .groupby("song_name")["show_index"]
        .nunique()
        .reindex(eligible_songs, fill_value=0)
    )

    recent_mask = plays["show_index"] >= (reference_index - 50)
    recent_50 = (
        plays[recent_mask]
        .groupby("song_name")["show_index"]
        .nunique()
        .reindex(eligible_songs, fill_value=0)
    )

    sorted_plays = plays.sort_values(["song_name", "show_index"])
    last_plays = sorted_plays.groupby("song_name").last()
    last_plays = last_plays.reindex(eligible_songs)

    debut_idx = plays.groupby("song_name")["show_index"].min().reindex(eligible_songs)

    total_per_song = song_show_counts.reindex(eligible_songs)

    song_plays_map: dict[str, list[int]] = {}
    for song_name, group in plays[plays["song_name"].isin(eligible_songs)].groupby(
        "song_name"
    ):
        song_plays_map[song_name] = sorted(group["show_index"].unique().tolist())

    venue_counts = plays.groupby(["song_name", "venue_name"])["show_index"].nunique()
    state_counts = plays.groupby(["song_name", "state"])["show_index"].nunique()

    features: list[dict[str, Any]] = []
    for song_name in eligible_songs:
        plays_idx = song_plays_map[song_name]
        ltp = _compute_ltp_features(plays_idx, reference_index)
        total_plays = int(total_per_song[song_name])
        debut_show_index = int(debut_idx[song_name])
        debut_age_shows = reference_index - debut_show_index
        n_shows_6mo = int(n_6mo[song_name])
        n_shows_1yr = int(n_1yr[song_name])
        n_shows_2yr = int(n_2yr[song_name])
        pct_shows_6mo = n_shows_6mo / shows_in_6mo
        pct_shows_1yr = n_shows_1yr / shows_in_1yr
        pct_shows_all_time = total_plays / total_shows

        venue_name = (
            last_plays.loc[song_name].get("venue_name")
            if pd.notna(last_plays.loc[song_name].get("venue_name"))
            else None
        )
        state = (
            last_plays.loc[song_name].get("state")
            if pd.notna(last_plays.loc[song_name].get("state"))
            else None
        )

        n_same_venue = 0
        if venue_name:
            try:
                n_same_venue = int(venue_counts.loc[(song_name, venue_name)])
            except KeyError:
                n_same_venue = 0

        n_same_state = 0
        if state:
            try:
                n_same_state = int(state_counts.loc[(song_name, state)])
            except KeyError:
                n_same_state = 0

        features.append(
            {
                "song_name": song_name,
                "current_gap": ltp["current_gap"],
                "avg_ltp": ltp["avg_ltp"],
                "recent_avg_ltp": ltp["recent_avg_ltp"],
                "overdue_metric": ltp["overdue_metric"],
                "gap_z_score": ltp["gap_z_score"],
                "plays_past_year": n_shows_1yr,
                "plays_past_2yr": n_shows_2yr,
                "recent_plays_50": int(recent_50[song_name]),
                "pct_shows_6mo": pct_shows_6mo,
                "pct_shows_1yr": pct_shows_1yr,
                "pct_shows_all_time": pct_shows_all_time,
                "diff_6mo_to_1yr": pct_shows_6mo - pct_shows_1yr,
                "diff_1yr_to_alltime": pct_shows_1yr - pct_shows_all_time,
                "n_shows_same_venue": n_same_venue,
                "n_shows_same_state": n_same_state,
                "debut_age_shows": debut_age_shows,
                "career_play_pct": (
                    total_plays / debut_age_shows if debut_age_shows > 0 else 0.0
                ),
                "novelty_rank": 0,
                "last_played_date": pd.Timestamp(
                    last_plays.loc[song_name, "show_date"]
                ),
                "total_plays": total_plays,
                "_debut_show_index": debut_show_index,
            }
        )

    result = pd.DataFrame(features)
    if not result.empty:
        debuts = result["_debut_show_index"].to_numpy()
        totals = result["total_plays"].to_numpy()
        debut_broadcast = debuts[:, np.newaxis]
        total_broadcast = totals[:, np.newaxis]
        newer_mask = debut_broadcast < debuts
        overtaken_mask = total_broadcast < totals
        result["novelty_rank"] = (newer_mask & overtaken_mask).sum(axis=1)
        result = result.drop(columns=["_debut_show_index"])

        position_features = _compute_set_position_features(plays)
        if not position_features.empty:
            result = result.merge(position_features, on="song_name", how="left")
        for col in _SET_POSITION_FEATURES:
            if col in result.columns:
                result[col] = result[col].fillna(0.0)
            else:
                result[col] = 0.0

        cooc_features = _compute_cooccurrence_features(
            plays,
            recently_played_songs=list(model_data.recently_played_songs),
            candidate_song_names=result["song_name"].astype(str).tolist(),
        )
        if not cooc_features.empty:
            result = result.merge(cooc_features, on="song_name", how="left")
        for col in _COOCCURRENCE_FEATURES:
            if col in result.columns:
                result[col] = result[col].fillna(0.0)
            else:
                result[col] = 0.0

    return result


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
    features = features[features["current_gap"] > 0]
    return features.reset_index(drop=True)


def build_training_frame(
    model_data: ModelData,
    *,
    band: str,
    min_plays_threshold: int,
    retired_gap_threshold: int,
    min_training_shows: int,
    training_window_shows: int,
    candidate_builder: Callable[[ModelData], pd.DataFrame] | None = None,
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
        target_rows = plays[plays["show_index"] == target_show_index]
        if target_rows.empty:
            continue

        target_show_date = pd.Timestamp(target_rows["show_date"].iloc[0]).normalize()
        prediction_date = pd.Timestamp(
            get_evaluation_reference_date(target_show_date.date())
        )
        history = plays[plays["show_date"] <= prediction_date].copy()
        if history["show_index"].nunique() < min_training_shows:
            continue

        reference_index = int(history["show_index"].max()) + 1
        target_show_context = normalize_target_show_context(target_rows.iloc[0])
        recent_window_start = max(1, reference_index - exclusion_window)
        recently_played = sorted(
            set(
                history[
                    history["show_index"].between(
                        recent_window_start, reference_index - 1
                    )
                ]["song_name"].tolist()
            )
        )

        sub_model_data = ModelData(
            historical_plays=history,
            master_feature_set=pd.DataFrame(),
            reference_date=prediction_date.date(),
            reference_index=reference_index,
            recently_played_songs=recently_played,
            diagnostics={
                "reference_date": prediction_date.date().isoformat(),
                "reference_index": reference_index,
                "target_show_date": target_show_date.date().isoformat(),
            },
            target_show_context=target_show_context or None,
        )

        if candidate_builder is None:
            candidates = get_candidate_features(
                sub_model_data,
                min_plays_threshold=min_plays_threshold,
                retired_gap_threshold=retired_gap_threshold,
            )
        else:
            candidates = candidate_builder(sub_model_data)
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
