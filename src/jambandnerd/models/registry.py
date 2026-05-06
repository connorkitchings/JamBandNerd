"""Canonical model registry for orchestration, storage, and serialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from jambandnerd.models.base import PredictionModel
from jambandnerd.models.baseline.predictor import BaselinePredictor
from jambandnerd.models.billy.fast_predictor import BillyFastBaselinePredictor
from jambandnerd.models.ckplus.model import CKPlusPredictor
from jambandnerd.models.ckplus.serialization import (
    serialize_predictions as serialize_ckplus_predictions,
)
from jambandnerd.models.deal.model import DealPredictor
from jambandnerd.models.deal.serialization import (
    serialize_predictions as serialize_deal_predictions,
)
from jambandnerd.models.goose.model import GooseFastRankPredictor
from jambandnerd.models.metadata import (
    BAND_METADATA,
    MODEL_METADATA,
    BandMetadata,
    ModelLifecycleStage,
    ModelMetadata,
    ModelWebVisibility,
)
from jambandnerd.models.notebook.model import NotebookPredictor
from jambandnerd.models.notebook.serialization import (
    serialize_predictions as serialize_notebook_predictions,
)
from jambandnerd.models.phish.experiments import PhishFastPlusNotebookRankVenueRun
from jambandnerd.models.um.fast_predictor import UMFastPredictor
from jambandnerd.models.wsp.fast_predictor import WSPFastPredictor

PredictionSerializer = Callable[[Sequence[Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class ModelDefinition:
    """Single source-of-truth metadata for a registered prediction model."""

    slug: str
    display_name: str
    predictor_cls: type[PredictionModel]
    version: str
    prediction_table: str
    serializer: PredictionSerializer
    enabled_for_pipeline: bool
    enabled_for_backfill: bool
    enabled_for_accuracy_validation: bool
    enabled_for_web: bool
    supports_training: bool
    supports_live_predictions: bool
    supports_backtest: bool
    lifecycle_stage: ModelLifecycleStage
    web_visibility: ModelWebVisibility
    readiness_windows: tuple[int, ...]
    readiness_baselines: tuple[str, ...]
    default_top_k: int = 50
    notes: str | None = None


_SERIALIZERS: dict[str, PredictionSerializer] = {
    "notebook": serialize_notebook_predictions,
    "ckplus": serialize_ckplus_predictions,
    "deal": serialize_deal_predictions,
}

_PREDICTOR_CLASSES: dict[str, type[PredictionModel]] = {
    "notebook": NotebookPredictor,
    "ckplus": CKPlusPredictor,
    "deal": DealPredictor,
}


def _to_definition(metadata: ModelMetadata) -> ModelDefinition:
    serializer = _SERIALIZERS.get(metadata.slug)
    predictor_cls = _PREDICTOR_CLASSES.get(metadata.slug)
    if serializer is None or predictor_cls is None:
        raise ValueError(f"Missing serializer or predictor class for {metadata.slug}")

    return ModelDefinition(
        slug=metadata.slug,
        display_name=metadata.display_name,
        predictor_cls=predictor_cls,
        version=metadata.version,
        prediction_table=metadata.prediction_table,
        serializer=serializer,
        enabled_for_pipeline=metadata.enabled_for_pipeline,
        enabled_for_backfill=metadata.enabled_for_backfill,
        enabled_for_accuracy_validation=metadata.enabled_for_accuracy_validation,
        enabled_for_web=metadata.enabled_for_web,
        supports_training=metadata.supports_training,
        supports_live_predictions=metadata.supports_live_predictions,
        supports_backtest=metadata.supports_backtest,
        lifecycle_stage=metadata.lifecycle_stage,
        web_visibility=metadata.web_visibility,
        readiness_windows=metadata.readiness_windows,
        readiness_baselines=metadata.readiness_baselines,
        default_top_k=metadata.default_top_k,
        notes=metadata.notes,
    )


_MODEL_DEFINITIONS: tuple[ModelDefinition, ...] = tuple(
    _to_definition(metadata) for metadata in MODEL_METADATA
)

_MODELS_BY_SLUG = {definition.slug: definition for definition in _MODEL_DEFINITIONS}


def get_model_definition(slug: str) -> ModelDefinition:
    """Return the model definition for a slug.

    Args:
        slug: The unique identifier for a prediction model.

    Returns:
        The matched ModelDefinition.

    Raises:
        ValueError: If the requested model slug is not registered.
    """
    try:
        return _MODELS_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"Unknown model slug: {slug}") from exc


def list_models() -> list[ModelDefinition]:
    """Return all registered models in deterministic order."""
    return list(_MODEL_DEFINITIONS)


def list_pipeline_models() -> list[ModelDefinition]:
    """Return models enabled for regular production pipeline runs."""
    return [
        definition
        for definition in _MODEL_DEFINITIONS
        if definition.enabled_for_pipeline
    ]


def list_web_models() -> list[ModelDefinition]:
    """Return models supported by website data/query surfaces."""
    return [
        definition for definition in _MODEL_DEFINITIONS if definition.enabled_for_web
    ]


def list_promoted_web_models() -> list[ModelDefinition]:
    """Return models currently promoted for public website visibility."""
    return [
        definition
        for definition in list_web_models()
        if definition.web_visibility == "promoted"
    ]


def list_backfill_models() -> list[ModelDefinition]:
    """Return models enabled for stale-prediction backfill."""
    return [
        definition
        for definition in _MODEL_DEFINITIONS
        if definition.enabled_for_backfill
    ]


def list_accuracy_validation_models() -> list[ModelDefinition]:
    """Return models that participate in accuracy validation checks."""
    return [
        definition
        for definition in _MODEL_DEFINITIONS
        if definition.enabled_for_accuracy_validation
    ]


def list_backtest_models() -> list[ModelDefinition]:
    """Return models that support backtest workloads."""
    return [
        definition for definition in _MODEL_DEFINITIONS if definition.supports_backtest
    ]


def list_model_slugs() -> list[str]:
    """Return all registered model slugs."""
    return [definition.slug for definition in _MODEL_DEFINITIONS]


def get_prediction_table(slug: str) -> str:
    """Return the prediction table name for a model slug."""
    return get_model_definition(slug).prediction_table


def get_model_version(slug: str) -> str:
    """Return the active model version for a model slug."""
    return get_model_definition(slug).version


def is_model_promoted_to_web(slug: str) -> bool:
    """Return whether a model is currently promoted on website surfaces."""
    definition = get_model_definition(slug)
    return definition.enabled_for_web and definition.web_visibility == "promoted"


def build_predictor(slug: str, *, band: str, **kwargs: Any) -> PredictionModel:
    """Instantiate a model predictor for a specific band.

    Args:
        slug: The model identifier.
        band: The band to predict for.
        **kwargs: Optional model-specific keyword arguments.

    Returns:
        An instantiated PredictionModel object ready for use.
    """
    definition = get_model_definition(slug)
    predictor_cls = definition.predictor_cls
    try:
        return predictor_cls(band=band, **kwargs)
    except TypeError:
        return predictor_cls(**kwargs)


_BAND_METADATA_MAP: dict[str, BandMetadata] = {m.band: m for m in BAND_METADATA}

_BAND_PREDICTOR_CLASSES: dict[str, type[PredictionModel]] = {
    "billy": BillyFastBaselinePredictor,
    "goose": GooseFastRankPredictor,
    "phish": PhishFastPlusNotebookRankVenueRun,
    "wsp": WSPFastPredictor,
    "um": UMFastPredictor,
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
    get_band_metadata(band)  # validates the band slug
    predictor_cls = _BAND_PREDICTOR_CLASSES.get(band, BaselinePredictor)
    return predictor_cls(band=band, **kwargs)


def get_band_serializer(band: str) -> PredictionSerializer:
    """Return the prediction serializer for a band's current model."""
    get_band_metadata(band)  # validates the band slug
    return serialize_deal_predictions


def serialize_model_predictions(
    slug: str,
    predictions: Sequence[Any],
) -> list[dict[str, Any]]:
    """Serialize predictions using the registered model serializer.

    Args:
        slug: The model identifier.
        predictions: The raw predictions sequence.

    Returns:
        A list of dictionaries representing the serialized prediction rows.
    """
    definition = get_model_definition(slug)
    return definition.serializer(predictions)
