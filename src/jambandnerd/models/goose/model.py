"""Goose-specific Phase B predictors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from jambandnerd.models.deal.features import (
    DealTrainingSummary,
    build_training_frame,
    generate_deal_features,
)
from jambandnerd.models.deal.model import DealPredictor
from jambandnerd.models.gbm.predictor import BandGbmPredictor
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.run_context import same_venue_run_show_indices

from .features import (
    GOOSE_EXTRA_FEATURES,
    augment_training_frame,
    compute_goose_song_features,
)

GOOSE_FEATURE_COLUMNS: list[str] = [
    "current_gap",
    "avg_ltp",
    "recent_avg_ltp",
    "overdue_metric",
    "gap_z_score",
    "plays_past_year",
    "plays_past_2yr",
    "pct_shows_6mo",
    "pct_shows_1yr",
    "diff_6mo_to_1yr",
    "n_shows_same_venue",
    "n_shows_same_state",
    "debut_age_shows",
    "career_play_pct",
    "novelty_rank",
]

GOOSE_V2_FEATURE_COLUMNS: list[str] = GOOSE_FEATURE_COLUMNS + GOOSE_EXTRA_FEATURES

GOOSE_UNUSED_DEAL_FEATURE_COLUMNS: list[str] = [
    "recent_plays_50",
    "pct_shows_all_time",
    "diff_1yr_to_alltime",
]

GOOSE_TOP10_FEATURE_COLUMNS: list[str] = (
    GOOSE_FEATURE_COLUMNS + GOOSE_UNUSED_DEAL_FEATURE_COLUMNS + GOOSE_EXTRA_FEATURES
)


def _goose_v3_candidate_features(
    model_data: ModelData,
    *,
    min_plays_threshold: int,
    retired_gap_threshold: int,
) -> pd.DataFrame:
    features = generate_deal_features(model_data, min_plays_threshold)
    if features.empty:
        return features

    same_run_songs: set[str] = set()
    same_run_indices = same_venue_run_show_indices(
        model_data.historical_plays,
        model_data.target_show_context,
    )
    if same_run_indices:
        same_run_songs = set(
            model_data.historical_plays.loc[
                model_data.historical_plays["show_index"].isin(same_run_indices),
                "song_name",
            ]
            .dropna()
            .astype(str)
        )

    recently_played = set(model_data.recently_played_songs)
    song_names = features["song_name"].astype(str)
    within_retirement = features["current_gap"] <= retired_gap_threshold
    standard_candidates = (
        ~song_names.isin(recently_played)
        & within_retirement
        & (features["current_gap"] > 0)
    )
    same_run_candidates = song_names.isin(same_run_songs) & within_retirement

    return features[standard_candidates | same_run_candidates].reset_index(drop=True)


class GoosePredictor(DealPredictor):
    """Goose Phase B v1 precision model built on the Deal ranking core.

    This keeps the first Goose-specific iteration close to the proven logistic
    baseline while moving Goose tuning into a band-owned module.
    """

    MODEL_DIR = Path("models/goose")
    MODEL_VERSION = "goose_phase_b_v1"

    def __init__(self, band: str = "goose", **kwargs: Any):
        if band != "goose":
            raise ValueError("GoosePredictor only supports band='goose'.")

        defaults: dict[str, Any] = {
            "min_plays_threshold": 3,
            "retired_gap_threshold": 90,
            "training_window_shows": 60,
            "min_training_shows": 20,
            "positive_weight_cap": 2.0,
            "feature_columns": list(GOOSE_FEATURE_COLUMNS),
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)

    def _get_model_path(self, band: str) -> Path:
        return self.MODEL_DIR / f"{band}_{self.MODEL_VERSION}.json"


class GooseLogisticV2Predictor(GoosePredictor):
    """Goose Phase B v2 logistic predictor with Tier A + Tier B features.

    Extends GoosePredictor with band-specific set-position and temporal
    features via goose/features.py.  Uses the same logistic core as v1
    but replaces GOOSE_FEATURE_COLUMNS with GOOSE_V2_FEATURE_COLUMNS.
    """

    MODEL_VERSION = "goose_phase_b_v2_logistic"

    def __init__(self, band: str = "goose", **kwargs: Any):
        defaults: dict[str, Any] = {
            "feature_columns": list(GOOSE_V2_FEATURE_COLUMNS),
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)

    def _build_training_frame(
        self, data: ModelData
    ) -> tuple[pd.DataFrame, DealTrainingSummary]:
        frame, summary = build_training_frame(
            data,
            band=self.band,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
            min_training_shows=self.min_training_shows,
            training_window_shows=self.training_window_shows,
        )
        if not frame.empty:
            frame = augment_training_frame(frame, data.historical_plays)
        return frame, summary

    def _get_candidate_features(self, model_data: ModelData) -> pd.DataFrame:
        from jambandnerd.models.deal.features import get_candidate_features

        candidates = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        if candidates.empty:
            return candidates
        target_show_date = model_data.reference_date
        goose_feats = compute_goose_song_features(
            model_data.historical_plays,
            target_show_date=target_show_date,
            target_show_context=model_data.target_show_context,
        )
        return candidates.merge(goose_feats, on="song_name", how="left").fillna(
            {col: 0.0 for col in GOOSE_EXTRA_FEATURES}
        )


class GooseGbmV2Predictor(BandGbmPredictor):
    """Goose Phase B v2 LightGBM LambdaRank predictor.

    Uses the same GOOSE_V2_FEATURE_COLUMNS as GooseLogisticV2Predictor so
    the two families are directly comparable in the promotion backtest.
    """

    MODEL_DIR = Path("models/goose/gbm")
    MODEL_VERSION = "goose_phase_b_v2_gbm"

    def __init__(self, band: str = "goose", **kwargs: Any):
        if band != "goose":
            raise ValueError("GooseGbmV2Predictor only supports band='goose'.")
        defaults: dict[str, Any] = {
            "feature_columns": list(GOOSE_V2_FEATURE_COLUMNS),
            "min_plays_threshold": 3,
            "retired_gap_threshold": 90,
            "training_window_shows": 60,
            "min_training_shows": 20,
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)

    def _build_training_frame(self, data: ModelData):
        frame, summary = build_training_frame(
            data,
            band=self.band,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
            min_training_shows=self.min_training_shows,
            training_window_shows=self.training_window_shows,
        )
        if not frame.empty:
            frame = augment_training_frame(frame, data.historical_plays)
        return frame, summary

    def _get_candidate_features(self, model_data: ModelData) -> pd.DataFrame:
        from jambandnerd.models.deal.features import get_candidate_features

        candidates = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        if candidates.empty:
            return candidates
        target_show_date = model_data.reference_date
        goose_feats = compute_goose_song_features(
            model_data.historical_plays,
            target_show_date=target_show_date,
            target_show_context=model_data.target_show_context,
        )
        return candidates.merge(goose_feats, on="song_name", how="left").fillna(
            {col: 0.0 for col in GOOSE_EXTRA_FEATURES}
        )


class GooseGbmTop10V3Predictor(BandGbmPredictor):
    """Exploratory Goose GBM candidate optimized for top-10 ranking evidence."""

    MODEL_DIR = Path("models/goose/gbm")
    MODEL_VERSION = "goose_phase_b_v3_gbm_top10"

    def __init__(self, band: str = "goose", **kwargs: Any):
        if band != "goose":
            raise ValueError("GooseGbmTop10V3Predictor only supports band='goose'.")
        defaults: dict[str, Any] = {
            "feature_columns": list(GOOSE_TOP10_FEATURE_COLUMNS),
            "min_plays_threshold": 3,
            "retired_gap_threshold": 90,
            "training_window_shows": 60,
            "min_training_shows": 20,
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)

    def _build_training_frame(self, data: ModelData):
        frame, summary = build_training_frame(
            data,
            band=self.band,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
            min_training_shows=self.min_training_shows,
            training_window_shows=self.training_window_shows,
            candidate_builder=lambda sub_model_data: _goose_v3_candidate_features(
                sub_model_data,
                min_plays_threshold=self.min_plays_threshold,
                retired_gap_threshold=self.retired_gap_threshold,
            ),
        )
        if not frame.empty:
            frame = augment_training_frame(frame, data.historical_plays)
        return frame, summary

    def _get_candidate_features(self, model_data: ModelData) -> pd.DataFrame:
        candidates = _goose_v3_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        if candidates.empty:
            return candidates
        goose_feats = compute_goose_song_features(
            model_data.historical_plays,
            target_show_date=model_data.reference_date,
            target_show_context=model_data.target_show_context,
        )
        return candidates.merge(goose_feats, on="song_name", how="left").fillna(
            {col: 0.0 for col in GOOSE_EXTRA_FEATURES}
        )
