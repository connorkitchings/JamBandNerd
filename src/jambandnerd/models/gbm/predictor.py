"""LightGBM LambdaRank predictor for per-band Phase B setlist prediction."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

from jambandnerd.config import RETIREMENT_GAPS
from jambandnerd.config.models import (
    DEAL_MIN_PLAYS_THRESHOLD,
    DEAL_MIN_TRAINING_SHOWS,
    DEAL_TRAINING_WINDOW_SHOWS,
)
from jambandnerd.models.base import PredictionModel
from jambandnerd.models.calibration import PlattScaler
from jambandnerd.models.deal.features import (
    DEAL_FEATURE_COLUMNS,
    build_training_frame,
    get_candidate_features,
)
from jambandnerd.models.deal.model import DealPrediction
from jambandnerd.transformations.gaps import ModelData

try:
    import lightgbm as lgb

    _LGB_AVAILABLE = True
except ImportError:  # pragma: no cover
    lgb = None  # type: ignore[assignment]
    _LGB_AVAILABLE = False

from jambandnerd.config.bands import get_excluded_songs


class BandGbmPredictor(PredictionModel):
    """LightGBM LambdaRank predictor sharing the same feature contract as DealPredictor.

    Uses the native LightGBM API (no scikit-learn required) with lambdarank
    objective and group labels = candidate count per target show.
    Returns List[DealPrediction] for full compatibility with the Deal serializer.
    """

    MODEL_DIR = Path("models/gbm")
    MODEL_VERSION = "gbm_v1"

    def __init__(
        self,
        band: str,
        n_estimators: int = 100,
        num_leaves: int = 31,
        learning_rate: float = 0.1,
        min_data_in_leaf: int = 5,
        min_plays_threshold: int = DEAL_MIN_PLAYS_THRESHOLD,
        retired_gap_threshold: Optional[int] = None,
        training_window_shows: int = DEAL_TRAINING_WINDOW_SHOWS,
        min_training_shows: int = DEAL_MIN_TRAINING_SHOWS,
        persist_artifacts: bool = True,
        feature_columns: Optional[List[str]] = None,
    ) -> None:
        if not _LGB_AVAILABLE:
            raise ImportError(
                "lightgbm is required for BandGbmPredictor. "
                "Install it with: uv add lightgbm"
            )
        self.band = band
        self.n_estimators = n_estimators
        self.num_leaves = num_leaves
        self.learning_rate = learning_rate
        self.min_data_in_leaf = min_data_in_leaf
        self.min_plays_threshold = min_plays_threshold
        self.retired_gap_threshold = (
            retired_gap_threshold
            if retired_gap_threshold is not None
            else RETIREMENT_GAPS.get(band, RETIREMENT_GAPS["default"])
        )
        self.training_window_shows = training_window_shows
        self.min_training_shows = min_training_shows
        self.persist_artifacts = persist_artifacts
        self.feature_columns = (
            feature_columns
            if feature_columns is not None
            else list(DEAL_FEATURE_COLUMNS)
        )
        self._booster: Optional[lgb.Booster] = None
        self._calibrator: Optional[PlattScaler] = None

    def _get_model_path(self) -> Path:
        return self.MODEL_DIR / f"{self.band}_{self.MODEL_VERSION}.txt"

    def _get_meta_path(self) -> Path:
        return self.MODEL_DIR / f"{self.band}_{self.MODEL_VERSION}_meta.json"

    def _build_training_frame(self, data: ModelData) -> tuple["pd.DataFrame", "Any"]:
        return build_training_frame(
            data,
            band=self.band,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
            min_training_shows=self.min_training_shows,
            training_window_shows=self.training_window_shows,
        )

    def _get_candidate_features(self, model_data: ModelData) -> "pd.DataFrame":
        candidates = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        return candidates

    def train(self, data: ModelData) -> None:
        training_frame, summary = self._build_training_frame(data)

        if training_frame.empty or summary.positive_rows == 0:
            self._booster = None
            self._calibrator = None
            return

        missing = [c for c in self.feature_columns if c not in training_frame.columns]
        if missing:
            raise ValueError(f"feature_columns not in training frame: {missing}")

        training_frame = training_frame.sort_values("target_show_index").reset_index(
            drop=True
        )

        unique_shows = training_frame["target_show_index"].unique()
        split_point = int(len(unique_shows) * 0.8)
        if split_point < 1:
            split_point = 1
        train_shows = set(unique_shows[:split_point])
        calib_shows = set(unique_shows[split_point:])

        train_frame = training_frame[
            training_frame["target_show_index"].isin(train_shows)
        ]
        calib_frame = training_frame[
            training_frame["target_show_index"].isin(calib_shows)
        ]

        groups = (
            train_frame.groupby("target_show_index", sort=False).size().values.tolist()
        )

        X_train = train_frame[self.feature_columns].fillna(0.0).to_numpy(dtype=float)
        y_train = train_frame["label"].to_numpy(dtype=int)

        train_set = lgb.Dataset(
            X_train, label=y_train, group=groups, free_raw_data=False
        )
        params: dict[str, Any] = {
            "objective": "rank_xendcg",
            "metric": "ndcg",
            "eval_at": [10, 25],
            "num_leaves": self.num_leaves,
            "learning_rate": self.learning_rate,
            "min_data_in_leaf": self.min_data_in_leaf,
            "verbose": -1,
        }
        self._booster = lgb.train(
            params,
            train_set,
            num_boost_round=self.n_estimators,
        )

        if not calib_frame.empty:
            X_calib = (
                calib_frame[self.feature_columns].fillna(0.0).to_numpy(dtype=float)
            )
            y_calib = calib_frame["label"].to_numpy(dtype=float)
            raw_scores = self._booster.predict(X_calib)
            self._calibrator = PlattScaler().fit(raw_scores, y_calib)
        else:
            self._calibrator = None

        if self.persist_artifacts:
            model_path = self._get_model_path()
            meta_path = self._get_meta_path()
            model_path.parent.mkdir(parents=True, exist_ok=True)
            self._booster.save_model(str(model_path))
            meta_path.write_text(
                json.dumps(
                    {
                        "band": self.band,
                        "model_version": self.MODEL_VERSION,
                        "feature_columns": self.feature_columns,
                        "trained_at": datetime.now(UTC)
                        .isoformat(timespec="seconds")
                        .replace("+00:00", "Z"),
                    },
                    indent=2,
                )
            )

    def _load_persisted(self) -> bool:
        model_path = self._get_model_path()
        meta_path = self._get_meta_path()
        if not (model_path.exists() and meta_path.exists()):
            return False
        meta = json.loads(meta_path.read_text())
        self.feature_columns = meta.get("feature_columns", self.feature_columns)
        self._booster = lgb.Booster(model_file=str(model_path))
        self._calibrator = None
        return True

    def predict(self, model_data: ModelData, top_k: int = 50) -> List[DealPrediction]:
        if self._booster is None:
            if self.persist_artifacts and self._load_persisted():
                pass
            else:
                self.train(model_data)

        if self._booster is None:
            return []

        candidates = self._get_candidate_features(model_data)
        if candidates.empty:
            return []

        candidates = candidates.copy()
        excluded = get_excluded_songs(self.band)
        if excluded:
            candidates = candidates[
                ~candidates["song_name"].str.lower().str.strip().isin(excluded)
            ]
        if candidates.empty:
            return []

        X = candidates[self.feature_columns].fillna(0.0).to_numpy(dtype=float)
        raw_scores = self._booster.predict(X)

        if self._calibrator is not None:
            calibrated = self._calibrator.transform(raw_scores)
        else:
            calibrated = raw_scores

        candidates = candidates.copy()
        candidates["probability"] = calibrated

        ranked = candidates.sort_values("probability", ascending=False).head(top_k)

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
            for _, row in ranked.iterrows()
        ]

    def calculate_accuracy(
        self,
        predictions: list[Any],
        actual_songs: list[str],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {}
