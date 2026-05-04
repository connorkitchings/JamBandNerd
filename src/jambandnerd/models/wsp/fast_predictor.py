"""Widespread Panic fast predictor — based on PhishFastPredictorV2 architecture.

Identical feature set and training approach to PhishFast V2 (16 features,
LightGBM rank_xendcg with early stopping). Adapted for WSP's touring patterns
with adjusted candidate pruning thresholds.
"""

from __future__ import annotations

from typing import Any

from jambandnerd.models.phish.fast_predictor import (
    PhishFastPredictorV2,
    PhishPrediction,
)

_WSP_CANDIDATE_RECENT_SHOWS = 150
_WSP_CANDIDATE_TOP_CAREER = 100


class WSPFastPredictor(PhishFastPredictorV2):
    """Widespread Panic LightGBM predictor using PhishFast V2 architecture.

    16 features: gap, recency windows, career rate, month rate, tour/run
    context, short-window recency, rotation analytics. With early stopping.
    """

    MODEL_VERSION = "wsp_fast_gbm_v1"

    def __init__(self, band: str = "wsp", **kwargs: Any) -> None:
        if band != "wsp":
            raise ValueError("WSPFastPredictor only supports band='wsp'.")
        self.band = band
        self._model = None
        self.best_iteration = None
        self._cache = None
        self.diagnostic_feature_columns = list(
            PhishFastPredictorV2._FEATURE_COLS
        )
