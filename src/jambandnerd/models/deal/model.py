"""Explainable Deal model using a logistic ranking objective."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from jambandnerd.config import (
    DEAL_EPOCHS,
    DEAL_L2_REGULARIZATION,
    DEAL_LEARNING_RATE,
    DEAL_MIN_PLAYS_THRESHOLD,
    DEAL_MIN_TRAINING_SHOWS,
    DEAL_RETIREMENT_GAP,
    DEAL_RETRAIN_INTERVAL_DAYS,
    DEAL_TRAINING_WINDOW_SHOWS,
)
from jambandnerd.config.bands import get_excluded_songs
from jambandnerd.models.base import PredictionModel
from jambandnerd.transformations.gaps import ModelData

from .features import (
    DEAL_FEATURE_COLUMNS,
    DealTrainingSummary,
    build_training_frame,
    get_candidate_features,
    summarize_training_summary,
)


@dataclass
class DealPrediction:
    song_name: str
    probability: float
    current_gap: int
    plays_past_year: int
    times_played: int
    LTP: str | None


@dataclass
class DealModelArtifact:
    model_version: str
    trained_at: str
    feature_columns: list[str]
    feature_means: list[float]
    feature_stds: list[float]
    coefficients: list[float]
    intercept: float
    training_summary: dict[str, Any]
    probability_summary: dict[str, float]
    calibration_summary: list[dict[str, float]]
    training_probability_quality_summary: dict[str, float] = field(
        default_factory=dict
    )
    training_separation_summary: dict[str, float] = field(default_factory=dict)
    calibration_error_summary: dict[str, float] = field(default_factory=dict)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _summarize_probabilities(probabilities: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(probabilities)) if probabilities.size else 0.0,
        "p25": float(np.percentile(probabilities, 25)) if probabilities.size else 0.0,
        "median": float(np.median(probabilities)) if probabilities.size else 0.0,
        "p75": float(np.percentile(probabilities, 75)) if probabilities.size else 0.0,
        "max": float(np.max(probabilities)) if probabilities.size else 0.0,
        "mean": float(np.mean(probabilities)) if probabilities.size else 0.0,
        "std": float(np.std(probabilities)) if probabilities.size else 0.0,
    }


def _build_calibration_summary(
    probabilities: np.ndarray, labels: np.ndarray
) -> list[dict[str, float]]:
    if probabilities.size == 0:
        return []

    bins = np.linspace(0.0, 1.0, num=6)
    summary: list[dict[str, float]] = []
    for lower, upper in zip(bins[:-1], bins[1:]):
        if upper == 1.0:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)

        if not mask.any():
            continue

        summary.append(
            {
                "bucket_start": float(lower),
                "bucket_end": float(upper),
                "count": float(mask.sum()),
                "avg_probability": float(probabilities[mask].mean()),
                "observed_rate": float(labels[mask].mean()),
            }
        )
    return summary


def _build_training_separation_summary(
    probabilities: np.ndarray, labels: np.ndarray
) -> dict[str, float]:
    if probabilities.size == 0 or labels.size == 0:
        return {
            "positive_mean_probability": 0.0,
            "negative_mean_probability": 0.0,
            "probability_gap": 0.0,
            "positive_median_probability": 0.0,
            "negative_median_probability": 0.0,
        }

    positive_mask = labels == 1.0
    negative_mask = labels == 0.0
    positive_probs = probabilities[positive_mask]
    negative_probs = probabilities[negative_mask]

    positive_mean = float(positive_probs.mean()) if positive_probs.size else 0.0
    negative_mean = float(negative_probs.mean()) if negative_probs.size else 0.0
    positive_median = float(np.median(positive_probs)) if positive_probs.size else 0.0
    negative_median = float(np.median(negative_probs)) if negative_probs.size else 0.0

    return {
        "positive_mean_probability": positive_mean,
        "negative_mean_probability": negative_mean,
        "probability_gap": positive_mean - negative_mean,
        "positive_median_probability": positive_median,
        "negative_median_probability": negative_median,
    }


def _build_calibration_error_summary(
    calibration_summary: list[dict[str, float]],
    probabilities: np.ndarray,
    labels: np.ndarray,
) -> dict[str, float]:
    if probabilities.size == 0 or labels.size == 0:
        return {
            "brier_score": 0.0,
            "expected_calibration_error": 0.0,
            "max_bucket_gap": 0.0,
        }

    total_count = float(len(probabilities))
    expected_calibration_error = sum(
        abs(bucket["avg_probability"] - bucket["observed_rate"])
        * (bucket["count"] / total_count)
        for bucket in calibration_summary
    )
    max_bucket_gap = max(
        (
            abs(bucket["avg_probability"] - bucket["observed_rate"])
            for bucket in calibration_summary
        ),
        default=0.0,
    )
    brier_score = float(np.mean((probabilities - labels) ** 2))

    return {
        "brier_score": brier_score,
        "expected_calibration_error": float(expected_calibration_error),
        "max_bucket_gap": float(max_bucket_gap),
    }


def _build_probability_quality_summary(probabilities: np.ndarray) -> dict[str, float]:
    if probabilities.size == 0:
        return {
            "count": 0.0,
            "probability_range": 0.0,
            "interquartile_range": 0.0,
            "top_1_minus_top_10_mean": 0.0,
            "top_10_mass_share": 0.0,
            "top_25_mass_share": 0.0,
        }

    sorted_probs = np.sort(probabilities)[::-1]
    probability_sum = float(sorted_probs.sum())
    top_10 = sorted_probs[: min(10, len(sorted_probs))]
    top_25 = sorted_probs[: min(25, len(sorted_probs))]
    top_10_mean = float(top_10.mean()) if top_10.size else 0.0

    return {
        "count": float(len(sorted_probs)),
        "probability_range": float(sorted_probs[0] - sorted_probs[-1]),
        "interquartile_range": float(np.percentile(sorted_probs, 75))
        - float(np.percentile(sorted_probs, 25)),
        "top_1_minus_top_10_mean": float(sorted_probs[0] - top_10_mean),
        "top_10_mass_share": (
            float(top_10.sum() / probability_sum) if probability_sum > 0 else 0.0
        ),
        "top_25_mass_share": (
            float(top_25.sum() / probability_sum) if probability_sum > 0 else 0.0
        ),
    }


class DealPredictor(PredictionModel):
    """Logistic ranking model trained on true per-show candidate rows."""

    MODEL_DIR = Path("models/deal")
    MODEL_VERSION = "deal_v2"

    def __init__(
        self,
        band: str,
        learning_rate: float = DEAL_LEARNING_RATE,
        epochs: int = DEAL_EPOCHS,
        regularization: float = DEAL_L2_REGULARIZATION,
        min_plays_threshold: int = DEAL_MIN_PLAYS_THRESHOLD,
        persist_artifacts: bool = True,
        retired_gap_threshold: Optional[int] = None,
        training_window_shows: int = DEAL_TRAINING_WINDOW_SHOWS,
        min_training_shows: int = DEAL_MIN_TRAINING_SHOWS,
        feature_columns: Optional[List[str]] = None,
        positive_weight_cap: Optional[float] = None,
    ):
        self.band = band
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.regularization = regularization
        self.min_plays_threshold = min_plays_threshold
        self.persist_artifacts = persist_artifacts
        self.retired_gap_threshold = (
            retired_gap_threshold
            if retired_gap_threshold is not None
            else DEAL_RETIREMENT_GAP.get(band, DEAL_RETIREMENT_GAP["default"])
        )
        self.training_window_shows = training_window_shows
        self.min_training_shows = min_training_shows
        self.feature_columns = (
            feature_columns
            if feature_columns is not None
            else list(DEAL_FEATURE_COLUMNS)
        )
        self.positive_weight_cap = positive_weight_cap
        self.model: Optional[DealModelArtifact] = None
        self.model_path: Optional[Path] = None
        self.latest_training_summary: Optional[DealTrainingSummary] = None

    def _get_model_path(self, band: str) -> Path:
        return self.MODEL_DIR / f"{band}_{self.MODEL_VERSION}.json"

    def _model_exists(self, model_path: Path) -> bool:
        return self.persist_artifacts and model_path.exists()

    def _should_retrain(self, model_path: Path) -> bool:
        if not model_path.exists():
            return True

        age_days = (
            datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)
        ).days
        return age_days >= DEAL_RETRAIN_INTERVAL_DAYS

    def _load_model(self, model_path: Path) -> DealModelArtifact:
        payload = json.loads(model_path.read_text())
        return DealModelArtifact(**payload)

    def _save_model(self, model_path: Path, artifact: DealModelArtifact) -> None:
        model_path.write_text(json.dumps(asdict(artifact), indent=2, sort_keys=True))

    def train(self, data: ModelData) -> None:
        model_path = self._get_model_path(self.band)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)

        if self._model_exists(model_path) and not self._should_retrain(model_path):
            self.model = self._load_model(model_path)
            self.model_path = model_path
            return

        training_frame, training_summary = build_training_frame(
            data,
            band=self.band,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
            min_training_shows=self.min_training_shows,
            training_window_shows=self.training_window_shows,
        )
        self.latest_training_summary = training_summary

        if training_frame.empty or training_summary.positive_rows == 0:
            self.model = None
            return

        missing = [c for c in self.feature_columns if c not in training_frame.columns]
        if missing:
            raise ValueError(
                f"feature_columns contains columns not in training frame: {missing}"
            )

        X = training_frame[self.feature_columns].fillna(0.0).to_numpy(dtype=float)
        y = training_frame["label"].to_numpy(dtype=float)
        means = X.mean(axis=0)
        stds = X.std(axis=0)
        stds[stds == 0] = 1.0
        X_scaled = (X - means) / stds

        coefficients = np.zeros(X_scaled.shape[1], dtype=float)
        intercept = float(
            np.log(
                np.clip(y.mean(), 1e-6, 1 - 1e-6)
                / (1 - np.clip(y.mean(), 1e-6, 1 - 1e-6))
            )
        )
        positive_weight = max(
            training_summary.negative_rows / max(training_summary.positive_rows, 1), 1.0
        )
        if self.positive_weight_cap is not None:
            positive_weight = min(positive_weight, self.positive_weight_cap)
        sample_weights = np.where(y == 1.0, positive_weight, 1.0)

        for _ in range(self.epochs):
            logits = X_scaled @ coefficients + intercept
            probabilities = _sigmoid(logits)
            errors = probabilities - y
            weighted_errors = sample_weights * errors
            grad_w = (X_scaled.T @ weighted_errors) / len(X_scaled)
            grad_w += self.regularization * coefficients
            grad_b = float(np.mean(weighted_errors))
            coefficients -= self.learning_rate * grad_w
            intercept -= self.learning_rate * grad_b

        fitted_probabilities = _sigmoid(X_scaled @ coefficients + intercept)
        calibration_summary = _build_calibration_summary(fitted_probabilities, y)
        artifact = DealModelArtifact(
            model_version=self.MODEL_VERSION,
            trained_at=datetime.now(UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            feature_columns=list(self.feature_columns),
            feature_means=means.tolist(),
            feature_stds=stds.tolist(),
            coefficients=coefficients.tolist(),
            intercept=float(intercept),
            training_summary=summarize_training_summary(training_summary),
            probability_summary=_summarize_probabilities(fitted_probabilities),
            calibration_summary=calibration_summary,
            training_probability_quality_summary=_build_probability_quality_summary(
                fitted_probabilities
            ),
            training_separation_summary=_build_training_separation_summary(
                fitted_probabilities,
                y,
            ),
            calibration_error_summary=_build_calibration_error_summary(
                calibration_summary,
                fitted_probabilities,
                y,
            ),
        )
        self.model = artifact
        self.model_path = model_path

        if self.persist_artifacts:
            self._save_model(model_path, artifact)

    def _predict_probabilities(self, candidate_features: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            return np.array([])

        X = (
            candidate_features[self.model.feature_columns]
            .fillna(0.0)
            .to_numpy(dtype=float)
        )
        means = np.asarray(self.model.feature_means, dtype=float)
        stds = np.asarray(self.model.feature_stds, dtype=float)
        stds[stds == 0] = 1.0
        coefficients = np.asarray(self.model.coefficients, dtype=float)
        X_scaled = (X - means) / stds
        return _sigmoid(X_scaled @ coefficients + self.model.intercept)

    def predict(self, model_data: ModelData, top_k: int = 50) -> List[DealPrediction]:
        if self.model is None:
            model_path = self._get_model_path(self.band)
            if self._model_exists(model_path):
                self.model = self._load_model(model_path)
                self.model_path = model_path
            else:
                self.train(model_data)

        if self.model is None:
            return []

        candidate_features = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        if candidate_features.empty:
            return []

        candidate_features = candidate_features.copy()
        candidate_features["probability"] = self._predict_probabilities(
            candidate_features
        )

        excluded_songs = get_excluded_songs(self.band)
        if excluded_songs:
            candidate_features = candidate_features[
                ~candidate_features["song_name"]
                .str.lower()
                .str.strip()
                .isin(excluded_songs)
            ]

        ranked = candidate_features.sort_values(
            ["probability", "current_gap", "plays_past_year", "song_name"],
            ascending=[False, False, False, True],
        ).head(top_k)

        return [
            DealPrediction(
                song_name=str(row["song_name"]),
                probability=float(row["probability"]),
                current_gap=int(row["current_gap"]),
                plays_past_year=int(row["plays_past_year"]),
                times_played=int(row["total_plays"]),
                LTP=(
                    row["last_played_date"].isoformat()
                    if pd.notna(row["last_played_date"])
                    else None
                ),
            )
            for _, row in ranked.iterrows()
        ]

    def build_evaluation_report(self, model_data: ModelData) -> Dict[str, Any]:
        if self.model is None:
            self.train(model_data)
        if self.model is None:
            return {"status": "untrained"}

        candidate_features = get_candidate_features(
            model_data,
            min_plays_threshold=self.min_plays_threshold,
            retired_gap_threshold=self.retired_gap_threshold,
        )
        current_probabilities = np.array([])
        current_probability_summary = {
            "min": 0.0,
            "p25": 0.0,
            "median": 0.0,
            "p75": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
        }
        if not candidate_features.empty:
            current_probabilities = self._predict_probabilities(candidate_features)
            current_probability_summary = _summarize_probabilities(
                current_probabilities
            )

        coefficient_rows = [
            {
                "feature": feature,
                "coefficient": coefficient,
            }
            for feature, coefficient in sorted(
                zip(self.model.feature_columns, self.model.coefficients),
                key=lambda item: abs(item[1]),
                reverse=True,
            )
        ]

        return {
            "status": "ready",
            "model_version": self.model.model_version,
            "trained_at": self.model.trained_at,
            "class_balance": self.model.training_summary,
            "probability_distribution": self.model.probability_summary,
            "training_probability_quality": (
                self.model.training_probability_quality_summary
            ),
            "current_candidate_probability_distribution": current_probability_summary,
            "current_candidate_probability_quality": _build_probability_quality_summary(
                current_probabilities
            ),
            "calibration_summary": self.model.calibration_summary,
            "calibration_error_summary": self.model.calibration_error_summary,
            "training_separation_summary": self.model.training_separation_summary,
            "coefficients": coefficient_rows,
        }

    def calculate_accuracy(
        self,
        predictions: List[DealPrediction],
        actual_songs: List[str],
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        return {}
