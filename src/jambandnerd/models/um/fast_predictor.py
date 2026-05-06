"""Umphrey's McGee fast predictor — based on PhishFastPredictorV2 architecture.

Identical feature set and training approach to PhishFast V2 (16 features,
LightGBM rank_xendcg with early stopping).
"""

from __future__ import annotations

from typing import Any

from jambandnerd.models.phish.fast_predictor import (
    PhishFastPredictorV2,
    _LGB_PARAMS,
)


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
        self.diagnostic_feature_columns = list(PhishFastPredictorV2._FEATURE_COLS)


_UM_V2_LGB_PARAMS: dict[str, Any] = {
    **_LGB_PARAMS,
    "num_leaves": 15,
    "learning_rate": 0.07,
    "reg_lambda": 0.1,
}


class UMFastPredictorV2(UMFastPredictor):
    """UMFast V2 — HP-tuned: leaves=15, lr=0.07, lambda=0.1.

    Combo sweep winner: dual=0.343 (+0.020 vs V1). Lower capacity + L2
    regularization + slightly faster learning rate.
    """

    MODEL_VERSION = "um_fast_gbm_v2"
    _LGB_PARAMS: dict[str, Any] = _UM_V2_LGB_PARAMS
