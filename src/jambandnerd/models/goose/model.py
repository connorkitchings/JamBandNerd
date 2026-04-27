"""Goose-specific Phase B predictor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jambandnerd.models.deal.model import DealPredictor

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


class GoosePredictor(DealPredictor):
    """Goose Phase B precision model built on the Deal ranking core.

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
