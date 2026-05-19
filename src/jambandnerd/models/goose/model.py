"""Goose-specific Phase B predictors."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from jambandnerd.config.bands import get_excluded_songs
from jambandnerd.models.deal.features import build_training_frame
from jambandnerd.models.deal.model import DealPrediction, DealPredictor
from jambandnerd.models.gbm.predictor import BandGbmPredictor
from jambandnerd.transformations.cooccurrence import (
    COOCCURRENCE_FEATURES as _COOCCURRENCE_FEATURES,
)
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.set_position import (
    SET_POSITION_FEATURES as _SET_POSITION_FEATURES,
)

from .experiments import GooseFastPlusNotebookRank
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
    *_SET_POSITION_FEATURES,
    *_COOCCURRENCE_FEATURES,
]

GOOSE_V2_FEATURE_COLUMNS: list[str] = GOOSE_FEATURE_COLUMNS + GOOSE_EXTRA_FEATURES


def _rank_scores(song_names: list[str]) -> dict[str, float]:
    """Map an ordered song list to normalized rank scores."""
    ordered = list(dict.fromkeys(str(name) for name in song_names))
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {ordered[0]: 1.0}
    denominator = len(ordered) - 1
    return {
        song_name: 1.0 - (rank / denominator) for rank, song_name in enumerate(ordered)
    }


def _notebook_ranked_songs(model_data: ModelData, *, band: str) -> list[str]:
    """Return Notebook-style ranking for the supplied reference-date history."""
    features = model_data.master_feature_set
    plays = model_data.historical_plays
    if features.empty or plays.empty:
        return []

    features = features.copy()
    plays = plays.copy()
    features["last_played_date"] = pd.to_datetime(
        features["last_played_date"], errors="coerce"
    )
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")

    last_completed_show_date = features["last_played_date"].max()
    if pd.isna(last_completed_show_date):
        return []

    window_start = last_completed_show_date - timedelta(days=365)
    plays_in_window = plays[plays["show_date"] >= window_start]
    plays_past_year_count = (
        plays_in_window.groupby("song_name")["show_index"]
        .nunique()
        .rename("plays_past_year")
    )

    candidates = features.merge(plays_past_year_count, on="song_name", how="inner")
    if candidates.empty:
        return []

    candidates["current_gap"] = (
        model_data.reference_index - candidates["last_played_index"] - 1
    ).clip(lower=0)
    candidates = candidates[
        ~candidates["song_name"].isin(set(model_data.recently_played_songs))
    ]

    excluded = get_excluded_songs(band)
    if excluded:
        candidates = candidates[
            ~candidates["song_name"].str.lower().str.strip().isin(excluded)
        ]
    if candidates.empty:
        return []

    ranked = candidates.sort_values(
        by=["plays_past_year", "current_gap", "song_name"],
        ascending=[False, False, True],
    )
    return ranked["song_name"].astype(str).tolist()


class GooseNotebookFloorPredictor(DealPredictor):
    """Goose-owned Notebook 1-year floor for the single-band registry.

    The ranking intentionally mirrors NotebookPredictor's 1-year contract:
    plays in the trailing year first, current gap second, song name third.
    It returns DealPrediction objects so the existing single-band serializer
    can publish the results without a separate legacy Notebook shape.
    """

    MODEL_DIR = Path("models/goose")
    MODEL_VERSION = "goose_notebook_floor_v1"

    def __init__(self, band: str = "goose", **kwargs: Any):
        if band != "goose":
            raise ValueError("GooseNotebookFloorPredictor only supports band='goose'.")
        self.band = band

    def train(self, data: ModelData) -> None:
        """No-op: the Notebook floor is a deterministic ranking rule."""
        return None

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[DealPrediction]:
        features = model_data.master_feature_set
        plays = model_data.historical_plays
        if features.empty or plays.empty:
            return []

        features = features.copy()
        plays = plays.copy()
        features["last_played_date"] = pd.to_datetime(
            features["last_played_date"], errors="coerce"
        )
        plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")

        last_completed_show_date = features["last_played_date"].max()
        if pd.isna(last_completed_show_date):
            return []

        window_start = last_completed_show_date - timedelta(days=365)
        plays_in_window = plays[plays["show_date"] >= window_start]
        plays_past_year_count = (
            plays_in_window.groupby("song_name")["show_index"]
            .nunique()
            .rename("plays_past_year")
        )

        candidates = features.merge(plays_past_year_count, on="song_name", how="inner")
        if candidates.empty:
            return []

        candidates["current_gap"] = (
            model_data.reference_index - candidates["last_played_index"] - 1
        ).clip(lower=0)
        candidates = candidates[
            ~candidates["song_name"].isin(set(model_data.recently_played_songs))
        ]
        if candidates.empty:
            return []

        max_show_index = int(plays["show_index"].max())
        recent_start = max(0, max_show_index - 49)
        recent_plays_50 = (
            plays[plays["show_index"] >= recent_start]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename("recent_plays_50")
        )
        candidates = candidates.merge(recent_plays_50, on="song_name", how="left")
        candidates["recent_plays_50"] = candidates["recent_plays_50"].fillna(0)

        ranked = candidates.sort_values(
            by=["plays_past_year", "current_gap", "song_name"],
            ascending=[False, False, True],
        ).head(top_k)

        excluded_songs = get_excluded_songs(self.band)
        if excluded_songs:
            ranked = ranked[
                ~ranked["song_name"].str.lower().str.strip().isin(excluded_songs)
            ]
        if ranked.empty:
            return []

        count = len(ranked)
        denominator = max(1, count - 1)
        predictions: list[DealPrediction] = []
        for rank, (_, row) in enumerate(ranked.iterrows()):
            last_played_date = row.get("last_played_date")
            if pd.isna(last_played_date):
                ltp = None
            else:
                ltp = pd.Timestamp(last_played_date).date().isoformat()
            predictions.append(
                DealPrediction(
                    song_name=str(row["song_name"]),
                    probability=float(1.0 - (rank / denominator)),
                    current_gap=int(row["current_gap"]),
                    plays_past_year=int(row["plays_past_year"]),
                    recent_plays_50=int(row["recent_plays_50"]),
                    LTP=ltp,
                )
            )
        return predictions


def _rank_blended_candidate_features(
    candidates: pd.DataFrame,
    *,
    alpha: float,
) -> pd.DataFrame:
    """Sort scored candidates by GBM/Notebook rank blend."""
    ranked = candidates.copy()
    ranked["probability"] = (
        alpha * ranked["gbm_rank_score"] + (1.0 - alpha) * ranked["notebook_rank_score"]
    )
    return ranked.sort_values(
        by=["probability", "gbm_rank_score", "notebook_rank_score", "song_name"],
        ascending=[False, False, False, True],
    )


def _is_not_part_of_tour(target_show_context: Any) -> bool:
    if target_show_context is None or not hasattr(target_show_context, "get"):
        return False
    value = target_show_context.get("tour_name")
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() == "not part of a tour"


def _notebook_guard_predictions(
    model_data: ModelData,
    *,
    band: str,
    top_k: int,
) -> list[DealPrediction]:
    features = model_data.master_feature_set
    plays = model_data.historical_plays
    if features.empty or plays.empty:
        return []

    features = features.copy()
    plays = plays.copy()
    features["last_played_date"] = pd.to_datetime(
        features["last_played_date"], errors="coerce"
    )
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")

    last_completed_show_date = features["last_played_date"].max()
    if pd.isna(last_completed_show_date):
        return []

    window_start = last_completed_show_date - timedelta(days=365)
    plays_past_year_count = (
        plays[plays["show_date"] >= window_start]
        .groupby("song_name")["show_index"]
        .nunique()
        .rename("plays_past_year")
    )
    candidates = features.merge(plays_past_year_count, on="song_name", how="inner")
    if candidates.empty:
        return []

    candidates["current_gap"] = (
        model_data.reference_index - candidates["last_played_index"] - 1
    ).clip(lower=0)
    candidates = candidates[
        ~candidates["song_name"].isin(set(model_data.recently_played_songs))
    ]

    excluded = get_excluded_songs(band)
    if excluded:
        candidates = candidates[
            ~candidates["song_name"].str.lower().str.strip().isin(excluded)
        ]
    if candidates.empty:
        return []

    max_show_index = int(plays["show_index"].max())
    recent_start = max(0, max_show_index - 49)
    recent_plays_50 = (
        plays[plays["show_index"] >= recent_start]
        .groupby("song_name")["show_index"]
        .nunique()
        .rename("recent_plays_50")
    )
    ranked = candidates.merge(recent_plays_50, on="song_name", how="left")
    ranked["recent_plays_50"] = ranked["recent_plays_50"].fillna(0)
    ranked = ranked.sort_values(
        by=["plays_past_year", "current_gap", "song_name"],
        ascending=[False, False, True],
    ).head(top_k)

    predictions: list[DealPrediction] = []
    for _, row in ranked.iterrows():
        last_played_date = row.get("last_played_date")
        predictions.append(
            DealPrediction(
                song_name=str(row["song_name"]),
                probability=0.0,
                current_gap=int(row["current_gap"]),
                plays_past_year=int(row["plays_past_year"]),
                recent_plays_50=int(row["recent_plays_50"]),
                LTP=(
                    pd.Timestamp(last_played_date).date().isoformat()
                    if pd.notna(last_played_date)
                    else None
                ),
            )
        )
    return predictions


def _merge_rank_guard_predictions(
    *,
    guarded: list[DealPrediction],
    primary: list[DealPrediction],
    guard_count: int,
    top_k: int,
) -> list[DealPrediction]:
    primary_lookup = {str(p.song_name): p for p in primary}
    merged: list[DealPrediction] = []
    seen: set[str] = set()
    for prediction in [*guarded[:guard_count], *primary]:
        song_name = str(prediction.song_name)
        if song_name in seen:
            continue
        seen.add(song_name)
        primary_pred = primary_lookup.get(song_name)
        if primary_pred is not None:
            merged.append(primary_pred)
        else:
            merged.append(prediction)
        if len(merged) >= top_k:
            break

    return merged


class _NotebookTop10GuardMixin:
    """Use Notebook's top 10 as a precision guard, then fill from the ranker."""

    _NOTEBOOK_GUARD_COUNT = 10

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[DealPrediction]:
        primary = super().predict(model_data, top_k=top_k)  # type: ignore[misc]
        guarded = _notebook_guard_predictions(
            model_data,
            band=self.band,
            top_k=max(top_k, self._NOTEBOOK_GUARD_COUNT),
        )
        return _merge_rank_guard_predictions(
            guarded=guarded,
            primary=primary,
            guard_count=self._NOTEBOOK_GUARD_COUNT,
            top_k=top_k,
        )


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


class GooseGbmNotebookBlendPredictor(GooseGbmV2Predictor):
    """Goose Phase B V2 GBM blended with Notebook rank evidence.

    The blend uses normalized rank scores rather than mixing raw GBM scores with
    Notebook counts. The default alpha keeps 60% weight on the V2 GBM ranking
    and 40% on the Notebook ranking, matching the best 50-show offline evidence.
    """

    MODEL_VERSION = "goose_phase_b_v4_gbm_notebook_blend"

    def __init__(
        self,
        band: str = "goose",
        notebook_blend_alpha: float = 0.60,
        **kwargs: Any,
    ):
        if not 0.0 <= notebook_blend_alpha <= 1.0:
            raise ValueError("notebook_blend_alpha must be between 0.0 and 1.0.")
        self.notebook_blend_alpha = notebook_blend_alpha
        super().__init__(band=band, **kwargs)

    def _score_candidates(self, model_data: ModelData) -> pd.DataFrame:
        if self._booster is None:
            if self.persist_artifacts and self._load_persisted():
                pass
            else:
                self.train(model_data)

        if self._booster is None:
            return pd.DataFrame()

        candidates = self._get_candidate_features(model_data)
        if candidates.empty:
            return candidates

        candidates = candidates.copy()
        excluded = get_excluded_songs(self.band)
        if excluded:
            candidates = candidates[
                ~candidates["song_name"].str.lower().str.strip().isin(excluded)
            ]
        if candidates.empty:
            return candidates

        X = candidates[self.feature_columns].fillna(0.0).to_numpy(dtype=float)
        candidates["gbm_raw_score"] = self._booster.predict(X)
        gbm_ranked = candidates.sort_values(
            by=["gbm_raw_score", "song_name"],
            ascending=[False, True],
        )
        candidates["gbm_rank_score"] = (
            candidates["song_name"]
            .astype(str)
            .map(_rank_scores(gbm_ranked["song_name"].astype(str).tolist()))
        ).fillna(0.0)

        notebook_scores = _rank_scores(
            _notebook_ranked_songs(model_data, band=self.band)
        )
        candidates["notebook_rank_score"] = (
            candidates["song_name"].astype(str).map(notebook_scores)
        ).fillna(0.0)
        return _rank_blended_candidate_features(
            candidates,
            alpha=self.notebook_blend_alpha,
        )

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[DealPrediction]:
        ranked = self._score_candidates(model_data)
        if ranked.empty:
            return []

        return [
            DealPrediction(
                song_name=str(row["song_name"]),
                probability=float(row["probability"]),
                current_gap=int(row["current_gap"]),
                plays_past_year=int(row["plays_past_year"]),
                recent_plays_50=int(row["recent_plays_50"]),
                LTP=(
                    row["last_played_date"].isoformat()
                    if pd.notna(row["last_played_date"])
                    else None
                ),
            )
            for _, row in ranked.head(top_k).iterrows()
        ]


class GooseFastRankPredictor(GooseFastPlusNotebookRank):
    """Goose production predictor: full-history LightGBM with notebook rank feature.

    Beats the Notebook 1-year baseline on dual (0.409 vs 0.408) and F1@25
    (0.282 vs 0.279) across 100-show walk-forward backtests.  Trains on full
    show history filtered by reference_date anti-leakage, scores with a
    17-feature presence-matrix LightGBM LambdaRank model.
    """

    MODEL_VERSION = "goose_fast_rank_v1"


class GooseFastRankSpecialNotebookTop10Predictor(
    _NotebookTop10GuardMixin,
    GooseFastRankPredictor,
):
    """Goose production predictor with special-show candidate repair.

    Ranks 1-10 are guarded by the deterministic Notebook floor. Ranks 11-50 are
    filled from the full-history LightGBM ranker, with immediate repeats allowed
    only for targets whose `tour_name` is `Not Part of a Tour`.
    """

    MODEL_VERSION = "goose_fast_rank_v1_candidate_relaxed_special_nbtop10"

    def _candidate_recent_gap_floor(self, target_show_context: Any) -> int:
        if _is_not_part_of_tour(target_show_context):
            return 0
        return super()._candidate_recent_gap_floor(target_show_context)
