"""Billy Strings Phase B predictors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from jambandnerd.models.deal.features import (
    DealTrainingSummary,
    build_training_frame,
    get_candidate_features,
)
from jambandnerd.models.deal.model import DealPredictor
from jambandnerd.models.gbm.predictor import BandGbmPredictor
from jambandnerd.transformations.cooccurrence import (
    COOCCURRENCE_FEATURES as _COOCCURRENCE_FEATURES,
)
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.set_position import (
    SET_POSITION_FEATURES as _SET_POSITION_FEATURES,
)

from .features import (
    BILLY_EXTRA_FEATURES,
    augment_training_frame,
    compute_billy_song_features,
)

BILLY_FEATURE_COLUMNS: list[str] = [
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
    *_SET_POSITION_FEATURES,
    *_COOCCURRENCE_FEATURES,
]

BILLY_V2_FEATURE_COLUMNS: list[str] = BILLY_FEATURE_COLUMNS + BILLY_EXTRA_FEATURES

_BILLY_ORIGINAL_ARTISTS: frozenset[str] = frozenset(
    {"Billy Strings", "William Apostol", "Billy Strings Band"}
)


def _build_is_cover_lookup(songs_df: pd.DataFrame | None) -> dict[str, float]:
    """Build a song_name -> is_cover float lookup from billy_songs_raw rows."""
    if songs_df is None or songs_df.empty:
        return {}
    lookup: dict[str, float] = {}
    for _, row in songs_df.iterrows():
        raw = row.get("original_artist")
        artist = "" if pd.isna(raw) else str(raw).strip()
        is_cover = 0.0 if not artist or artist in _BILLY_ORIGINAL_ARTISTS else 1.0
        lookup[str(row["song_name"])] = is_cover
    return lookup


def _fetch_songs_from_supabase() -> pd.DataFrame:
    from jambandnerd.db.connection import get_supabase_client

    client = get_supabase_client()
    response = (
        client.table("billy_songs_raw").select("song_name, original_artist").execute()
    )
    return pd.DataFrame(response.data)


class BillyPredictor(DealPredictor):
    """Billy Strings Phase B v1 logistic predictor with run/tour/cover features.

    Adapts the Goose Phase B feature set for Billy: all 10 Goose run/tour/recency
    features plus is_cover (1.0 for cover songs, 0.0 for originals).
    """

    MODEL_DIR = Path("models/billy")
    MODEL_VERSION = "billy_phase_b_v1"

    def __init__(
        self,
        band: str = "billy",
        songs_df: pd.DataFrame | None = None,
        **kwargs: Any,
    ):
        if band != "billy":
            raise ValueError("BillyPredictor only supports band='billy'.")

        songs_df_resolved = (
            songs_df if songs_df is not None else _fetch_songs_from_supabase()
        )
        self._songs_lookup = _build_is_cover_lookup(songs_df_resolved)

        defaults: dict[str, Any] = {
            "min_plays_threshold": 3,
            "retired_gap_threshold": 120,
            "training_window_shows": 75,
            "min_training_shows": 25,
            "positive_weight_cap": 2.0,
            "feature_columns": list(BILLY_V2_FEATURE_COLUMNS),
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)

    def _get_model_path(self, band: str) -> Path:
        return self.MODEL_DIR / f"{band}_{self.MODEL_VERSION}.json"

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
            frame = augment_training_frame(
                frame,
                data.historical_plays,
                songs_lookup=self._songs_lookup,
            )
        return frame, summary

    def _get_candidate_features(self, model_data: ModelData) -> pd.DataFrame:
        candidates = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        if candidates.empty:
            return candidates
        billy_feats = compute_billy_song_features(
            model_data.historical_plays,
            target_show_date=model_data.reference_date,
            target_show_context=model_data.target_show_context,
            songs_lookup=self._songs_lookup,
        )
        return candidates.merge(billy_feats, on="song_name", how="left").fillna(
            {col: 0.0 for col in BILLY_EXTRA_FEATURES}
        )


class BillyGbmPredictor(BandGbmPredictor):
    """Billy Strings Phase B v2 LightGBM LambdaRank predictor.

    Uses BILLY_V2_FEATURE_COLUMNS (base Deal features + run/tour/recency + is_cover).
    """

    MODEL_DIR = Path("models/billy/gbm")
    MODEL_VERSION = "billy_phase_b_v2_gbm"

    def __init__(
        self,
        band: str = "billy",
        songs_df: pd.DataFrame | None = None,
        **kwargs: Any,
    ):
        if band != "billy":
            raise ValueError("BillyGbmPredictor only supports band='billy'.")

        songs_df_resolved = (
            songs_df if songs_df is not None else _fetch_songs_from_supabase()
        )
        self._songs_lookup = _build_is_cover_lookup(songs_df_resolved)

        defaults: dict[str, Any] = {
            "feature_columns": list(BILLY_V2_FEATURE_COLUMNS),
            "min_plays_threshold": 3,
            "retired_gap_threshold": 120,
            "training_window_shows": 75,
            "min_training_shows": 25,
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
            frame = augment_training_frame(
                frame,
                data.historical_plays,
                songs_lookup=self._songs_lookup,
            )
        return frame, summary

    def _get_candidate_features(self, model_data: ModelData) -> pd.DataFrame:
        candidates = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        if candidates.empty:
            return candidates
        billy_feats = compute_billy_song_features(
            model_data.historical_plays,
            target_show_date=model_data.reference_date,
            target_show_context=model_data.target_show_context,
            songs_lookup=self._songs_lookup,
        )
        return candidates.merge(billy_feats, on="song_name", how="left").fillna(
            {col: 0.0 for col in BILLY_EXTRA_FEATURES}
        )
