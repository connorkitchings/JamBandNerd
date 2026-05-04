"""Umphrey's McGee fast predictor — based on PhishFastPredictorV2 architecture.

Identical feature set and training approach to PhishFast V2 (16 features,
LightGBM rank_xendcg with early stopping).
"""

from __future__ import annotations

from typing import Any

from jambandnerd.models.phish.fast_predictor import PhishFastPredictorV2


class UMFastPredictor(PhishFastPredictorV2):
    """Umphrey's McGee LightGBM predictor using PhishFast V2 architecture.

    16 features: gap, recency windows, career rate, month rate, tour/run
    context, short-window recency, rotation analytics. With early stopping.
    """

    MODEL_VERSION = "um_fast_gbm_v1"

    def __init__(self, band: str = "um", **kwargs: Any) -> None:
        if band != "um":
            raise ValueError("UMFastPredictor only supports band='um'.")
        self.band = band
        self._model = None
        self.best_iteration = None
        self._cache = None
        self.diagnostic_feature_columns = list(
            PhishFastPredictorV2._FEATURE_COLS
        )
