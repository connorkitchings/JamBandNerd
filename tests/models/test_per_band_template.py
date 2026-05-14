"""Framework contract: every active band must have a registered predictor and metadata."""

from __future__ import annotations

import pytest

from jambandnerd.config.models import ACTIVE_BANDS
from jambandnerd.models.base import PredictionModel
from jambandnerd.models.registry import build_band_predictor, get_band_metadata


@pytest.mark.parametrize("band", ACTIVE_BANDS)
def test_band_has_metadata(band: str) -> None:
    meta = get_band_metadata(band)
    assert meta.band == band
    assert meta.model_version, f"{band}: model_version must not be empty"
    assert meta.default_top_k > 0, f"{band}: default_top_k must be positive"


@pytest.mark.parametrize("band", ACTIVE_BANDS)
def test_band_predictor_is_prediction_model(band: str) -> None:
    predictor = build_band_predictor(band, persist_artifacts=False)
    assert isinstance(
        predictor, PredictionModel
    ), f"{band}: build_band_predictor must return a PredictionModel subclass"


@pytest.mark.parametrize("band", ACTIVE_BANDS)
def test_band_predictor_band_attribute_matches(band: str) -> None:
    predictor = build_band_predictor(band, persist_artifacts=False)
    assert hasattr(
        predictor, "band"
    ), f"{band}: predictor must expose a .band attribute"
    assert predictor.band == band
