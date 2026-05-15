"""Shared v1 baseline predictor for the single-model-per-band architecture."""

from __future__ import annotations

from pathlib import Path

from jambandnerd.models.deal.model import DealPredictor


class BaselinePredictor(DealPredictor):
    """v1 baseline predictor; wraps DealPredictor keyed to a per-band model artifact."""

    MODEL_DIR = Path("models/baseline")

    def __init__(self, band: str, **kwargs):
        super().__init__(band=band, **kwargs)
        self.MODEL_VERSION = f"{band}_baseline_v1"

    def _get_model_path(self, band: str) -> Path:
        return self.MODEL_DIR / f"{band}_baseline_v1.json"
