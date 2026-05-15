"""Canonical band-keyed model registry for orchestration, storage, and serialization."""

from __future__ import annotations

from typing import Any, Callable, Sequence

from jambandnerd.models.base import PredictionModel
from jambandnerd.models.baseline.predictor import BaselinePredictor
from jambandnerd.models.billy.fast_predictor import BillyFastBaselinePredictor
from jambandnerd.models.goose.model import GooseFastRankSpecialNotebookTop10Predictor
from jambandnerd.models.metadata import (
    BAND_METADATA,
    BandMetadata,
)
from jambandnerd.models.phish.experiments import PhishFastPlusNotebookRankVenueRun
from jambandnerd.models.um.fast_predictor import UMFastPredictorV2
from jambandnerd.models.wsp.fast_predictor import WSPFastPredictor

PredictionSerializer = Callable[[Sequence[Any]], list[dict[str, Any]]]


_BAND_METADATA_MAP: dict[str, BandMetadata] = {m.band: m for m in BAND_METADATA}

_BAND_PREDICTOR_CLASSES: dict[str, type[PredictionModel]] = {
    "billy": BillyFastBaselinePredictor,
    "goose": GooseFastRankSpecialNotebookTop10Predictor,
    "phish": PhishFastPlusNotebookRankVenueRun,
    "wsp": WSPFastPredictor,
    "um": UMFastPredictorV2,
}


def list_active_bands() -> list[str]:
    """Return the in-scope bands for the single-model-per-band architecture."""
    return [m.band for m in BAND_METADATA]


def get_band_metadata(band: str) -> BandMetadata:
    """Return per-band metadata for the single-model-per-band architecture."""
    try:
        return _BAND_METADATA_MAP[band]
    except KeyError as exc:
        raise ValueError(f"Unknown band: {band}") from exc


def get_band_model_version(band: str) -> str:
    """Return the active model version string for a band."""
    return get_band_metadata(band).model_version


def build_band_predictor(band: str, **kwargs) -> PredictionModel:
    """Instantiate the active single-model predictor for a band."""
    get_band_metadata(band)
    predictor_cls = _BAND_PREDICTOR_CLASSES.get(band, BaselinePredictor)
    return predictor_cls(band=band, **kwargs)


def get_band_serializer(band: str) -> PredictionSerializer:
    """Return the prediction serializer for a band's current model."""
    get_band_metadata(band)
    from jambandnerd.models.deal.serialization import (
        serialize_predictions as serialize_deal_predictions,
    )

    return serialize_deal_predictions
