"""Deal model - XGBoost-based ML prediction model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import xgboost as xgb

from src.jambandnerd.config import (
    DEAL_ETA,
    DEAL_MAX_DEPTH,
    DEAL_MIN_PLAYS_THRESHOLD,
    DEAL_NROUNDS,
    DEAL_RETIREMENT_GAP,
    DEAL_RETRAIN_INTERVAL_DAYS,
)
from src.jambandnerd.config.bands import get_excluded_songs
from src.jambandnerd.models.base import PredictionModel
from src.jambandnerd.transformations.gaps import ModelData

from .features import get_candidate_features


@dataclass
class DealPrediction:
    """Prediction output for the Deal model."""

    song_name: str
    probability: float
    current_gap: int
    plays_past_year: int
    times_played: int
    LTP: str | None


class DealPredictor(PredictionModel):
    """XGBoost-based prediction model for setlist forecasting."""

    MODEL_DIR = Path("models/deal")

    def __init__(
        self,
        band: str,
        max_depth: int = DEAL_MAX_DEPTH,
        eta: float = DEAL_ETA,
        nrounds: int = DEAL_NROUNDS,
        min_plays_threshold: int = DEAL_MIN_PLAYS_THRESHOLD,
    ):
        self.band = band
        self.max_depth = max_depth
        self.eta = eta
        self.nrounds = nrounds
        self.min_plays_threshold = min_plays_threshold
        self.retired_gap_threshold = DEAL_RETIREMENT_GAP.get(
            band, DEAL_RETIREMENT_GAP["default"]
        )
        self.model: Optional[xgb.Booster] = None
        self.model_path: Optional[Path] = None

    def _get_model_path(self, band: str) -> Path:
        """Get the path for the persisted model."""
        today = datetime.now().strftime("%Y%m%d")
        return self.MODEL_DIR / f"{band}_{today}.json"

    def _model_exists(self, model_path: Path) -> bool:
        """Check if persisted model exists."""
        return model_path.exists()

    def _should_retrain(self, model_path: Path) -> bool:
        """Check if model should be retrained based on age."""
        if not model_path.exists():
            return True

        model_mtime = datetime.fromtimestamp(model_path.stat().st_mtime)
        age_days = (datetime.now() - model_mtime).days
        return age_days >= DEAL_RETRAIN_INTERVAL_DAYS

    def train(self, data: ModelData) -> None:
        """Train the XGBoost model.

        Args:
            data: ModelData container with historical plays
        """
        print(f"[DEAL] Training model for {self.band}...")

        model_path = self._get_model_path(self.band)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        if self._model_exists(model_path) and not self._should_retrain(model_path):
            print(f"[DEAL] Loading existing model from {model_path}")
            self.model = xgb.Booster(model_file=str(model_path))
            self.model_path = model_path
            return

        print("[DEAL] Training new model (or retraining)...")

        from .features import get_candidate_features

        candidate_features = get_candidate_features(
            data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )

        if candidate_features.empty:
            print("[DEAL] No candidate songs available for prediction")
            return

        reference_index = data.reference_index
        test_show_indices = list(range(max(1, reference_index - 50), reference_index))

        plays = data.historical_plays.copy()
        test_shows = plays[plays["show_index"].isin(test_show_indices)]
        positive_songs = set(test_shows["song_name"].unique())

        candidate_features = candidate_features.copy()
        candidate_features["label"] = (
            candidate_features["song_name"].isin(positive_songs).astype(int)
        )

        positive_count = candidate_features["label"].sum()
        negative_count = len(candidate_features) - positive_count

        if positive_count > 0 and negative_count > 0:
            y = candidate_features["label"]
            print(
                f"[DEAL] Training with {positive_count} positives, {negative_count} negatives"
            )
        else:
            print("[DEAL] Using frequency-based ranking target")
            candidate_features["target"] = (
                candidate_features["plays_past_year"] * 10
                + candidate_features["n_shows_6mo"] * 5
                - candidate_features["current_gap"] * 0.1
            )
            max_target = candidate_features["target"].max()
            candidate_features["label"] = (
                candidate_features["target"] / max_target if max_target > 0 else 0
            )
            y = candidate_features["label"]
            print("[DEAL] Training with continuous target (frequency-based)")

        feature_columns = [
            "n_shows_6mo",
            "n_shows_1yr",
            "n_shows_2yr",
            "n_shows_4yr",
            "pct_shows_1yr",
            "pct_shows_2yr",
            "total_plays",
            "plays_past_year",
            "plays_past_2yr",
            "play_rate",
            "ltp_1",
            "ltp_2",
            "ltp_3",
            "ltp_4",
            "ltp_5",
            "ltp_6",
            "ltp_7",
            "ltp_8",
            "ltp_9",
            "ltp_10",
            "avg_ltp",
            "recent_avg_ltp",
            "overdue_metric",
            "ltp_trend",
            "std_gap",
            "min_gap",
            "max_gap",
            "gap_z_score",
            "current_gap",
            "days_since_last",
            "pct_shows_all_time",
            "pct_shows_6mo",
            "diff_6mo_to_1yr",
            "diff_1yr_to_alltime",
            "n_shows_same_venue",
            "n_shows_same_state",
            "pct_shows_same_venue",
            "pct_shows_same_state",
            "diff_same_venue_vs_alltime",
        ]

        X = candidate_features[feature_columns].fillna(0)

        params = {
            "max_depth": 2,
            "eta": 0.3,
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "min_child_weight": 1,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "seed": 42,
            "tree_method": "hist",
        }

        dtrain = xgb.DMatrix(X, label=y)
        evals = [(dtrain, "train")]
        self.model = xgb.train(
            params,
            dtrain,
            num_boost_round=self.nrounds,
            evals=evals,
            verbose_eval=False,
        )

        self.model.save_model(str(model_path))
        self.model_path = model_path
        print(f"[DEAL] Model trained and saved to {model_path}")

    def predict(
        self,
        model_data: ModelData,
        top_k: int = 50,
    ) -> List[DealPrediction]:
        """Generate probability-ranked predictions.

        Args:
            model_data: ModelData container
            top_k: Number of predictions to return

        Returns:
            List of DealPrediction objects sorted by probability
        """
        if self.model is None:
            model_path = self._get_model_path(self.band)
            if model_path.exists():
                self.model = xgb.Booster(model_file=str(model_path))
            else:
                print("[DEAL] No model available. Training first...")
                self.train(model_data)
                if self.model is None:
                    return []

        candidate_features = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )

        if candidate_features.empty:
            print(f"[DEAL] No candidate songs for {self.band}")
            return []

        feature_columns = [
            "n_shows_6mo",
            "n_shows_1yr",
            "n_shows_2yr",
            "n_shows_4yr",
            "pct_shows_1yr",
            "pct_shows_2yr",
            "total_plays",
            "plays_past_year",
            "plays_past_2yr",
            "play_rate",
            "ltp_1",
            "ltp_2",
            "ltp_3",
            "ltp_4",
            "ltp_5",
            "ltp_6",
            "ltp_7",
            "ltp_8",
            "ltp_9",
            "ltp_10",
            "avg_ltp",
            "recent_avg_ltp",
            "overdue_metric",
            "ltp_trend",
            "std_gap",
            "min_gap",
            "max_gap",
            "gap_z_score",
            "current_gap",
            "days_since_last",
            "pct_shows_all_time",
            "pct_shows_6mo",
            "diff_6mo_to_1yr",
            "diff_1yr_to_alltime",
            "n_shows_same_venue",
            "n_shows_same_state",
            "pct_shows_same_venue",
            "pct_shows_same_state",
            "diff_same_venue_vs_alltime",
        ]

        X_candidates = candidate_features[feature_columns].fillna(0)

        dmatrix = xgb.DMatrix(X_candidates)
        probabilities = self.model.predict(dmatrix)

        candidate_features = candidate_features.copy()
        candidate_features["probability"] = probabilities

        excluded_songs = get_excluded_songs(self.band)
        if excluded_songs:
            candidate_features = candidate_features[
                ~candidate_features["song_name"]
                .str.lower()
                .str.strip()
                .isin(excluded_songs)
            ]

        candidate_features = candidate_features.sort_values(
            "probability", ascending=False
        ).head(top_k)

        results: List[DealPrediction] = []
        for _, row in candidate_features.iterrows():
            last_played = row.get("last_played_date")
            ltp_str = (
                last_played.isoformat()
                if last_played is not None and pd.notna(last_played)
                else None
            )

            results.append(
                DealPrediction(
                    song_name=str(row["song_name"]),
                    probability=float(row["probability"]),
                    current_gap=int(row["current_gap"]),
                    plays_past_year=int(row["plays_past_year"]),
                    times_played=int(row["total_plays"]),
                    LTP=ltp_str,
                )
            )

        return results

    def calculate_accuracy(
        self,
        predictions: List[DealPrediction],
        actual_songs: List[str],
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Placeholder for accuracy calculation.

        Accuracy is handled externally by the accuracy module.
        """
        return {}
