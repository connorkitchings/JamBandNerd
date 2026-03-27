"""Canonical model registry for orchestration, storage, and serialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from src.jambandnerd.models.base import PredictionModel
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.models.ckplus.serialization import (
    serialize_predictions as serialize_ckplus_predictions,
)
from src.jambandnerd.models.deal.model import DealPredictor
from src.jambandnerd.models.deal.serialization import (
    serialize_predictions as serialize_deal_predictions,
)
from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.models.notebook.serialization import (
    serialize_predictions as serialize_notebook_predictions,
)
from src.jambandnerd.models.metadata import MODEL_METADATA, ModelMetadata

PredictionSerializer = Callable[[Sequence[Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class ModelDefinition:
    """Single source-of-truth metadata for a registered prediction model."""

    slug: str
    display_name: str
    predictor_cls: type[PredictionModel]
    version: str
    prediction_table: str
    aggregate_accuracy_table: str | None
    serializer: PredictionSerializer
    enabled_for_pipeline: bool
    enabled_for_backfill: bool
    enabled_for_accuracy_validation: bool
    enabled_for_aggregate_accuracy: bool
    enabled_for_web: bool
    supports_training: bool
    supports_live_predictions: bool
    supports_backtest: bool
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
        aggregate_accuracy_table=metadata.aggregate_accuracy_table,
        serializer=serializer,
        enabled_for_pipeline=metadata.enabled_for_pipeline,
        enabled_for_backfill=metadata.enabled_for_backfill,
        enabled_for_accuracy_validation=metadata.enabled_for_accuracy_validation,
        enabled_for_aggregate_accuracy=metadata.enabled_for_aggregate_accuracy,
        enabled_for_web=metadata.enabled_for_web,
        supports_training=metadata.supports_training,
        supports_live_predictions=metadata.supports_live_predictions,
        supports_backtest=metadata.supports_backtest,
        default_top_k=metadata.default_top_k,
        notes=metadata.notes,
    )


_MODEL_DEFINITIONS: tuple[ModelDefinition, ...] = tuple(
    _to_definition(metadata) for metadata in MODEL_METADATA
)

_MODELS_BY_SLUG = {definition.slug: definition for definition in _MODEL_DEFINITIONS}


def get_model_definition(slug: str) -> ModelDefinition:
    """Return the model definition for a slug."""
    try:
        return _MODELS_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"Unknown model slug: {slug}") from exc


def list_models() -> list[ModelDefinition]:
    """Return all registered models in deterministic order."""
    return list(_MODEL_DEFINITIONS)


def list_pipeline_models() -> list[ModelDefinition]:
    """Return models enabled for regular production pipeline runs."""
    return [definition for definition in _MODEL_DEFINITIONS if definition.enabled_for_pipeline]


def list_web_models() -> list[ModelDefinition]:
    """Return models enabled for website surfaces."""
    return [definition for definition in _MODEL_DEFINITIONS if definition.enabled_for_web]


def list_backfill_models() -> list[ModelDefinition]:
    """Return models enabled for stale-prediction backfill."""
    return [definition for definition in _MODEL_DEFINITIONS if definition.enabled_for_backfill]


def list_accuracy_validation_models() -> list[ModelDefinition]:
    """Return models that participate in accuracy validation checks."""
    return [
        definition
        for definition in _MODEL_DEFINITIONS
        if definition.enabled_for_accuracy_validation
    ]


def list_backtest_models() -> list[ModelDefinition]:
    """Return models that support backtest workloads."""
    return [definition for definition in _MODEL_DEFINITIONS if definition.supports_backtest]


def list_aggregate_accuracy_models() -> list[ModelDefinition]:
    """Return models that participate in aggregate accuracy table writes."""
    return [
        definition
        for definition in _MODEL_DEFINITIONS
        if definition.enabled_for_aggregate_accuracy
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


def get_aggregate_accuracy_table(slug: str) -> str | None:
    """Return aggregate accuracy table name for a model slug, if configured."""
    return get_model_definition(slug).aggregate_accuracy_table


def build_predictor(slug: str, *, band: str, **kwargs: Any) -> PredictionModel:
    """Instantiate a model predictor for a specific band."""
    definition = get_model_definition(slug)
    predictor_cls = definition.predictor_cls
    try:
        return predictor_cls(band=band, **kwargs)
    except TypeError:
        return predictor_cls(**kwargs)


def serialize_model_predictions(
    slug: str,
    predictions: Sequence[Any],
) -> list[dict[str, Any]]:
    """Serialize predictions using the registered model serializer."""
    definition = get_model_definition(slug)
    return definition.serializer(predictions)
