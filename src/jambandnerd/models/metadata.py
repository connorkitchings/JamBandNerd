"""Shared model metadata used by the registry and compatibility shims."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelMetadata:
    """Model metadata that is independent of predictor imports."""

    slug: str
    display_name: str
    version: str
    prediction_table: str
    aggregate_accuracy_table: str | None
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


MODEL_METADATA: tuple[ModelMetadata, ...] = (
    ModelMetadata(
        slug="notebook",
        display_name="Notebook",
        version="notebook_v1",
        prediction_table="predictions_notebook",
        aggregate_accuracy_table="notebook_accuracy",
        enabled_for_pipeline=True,
        enabled_for_backfill=True,
        enabled_for_accuracy_validation=True,
        enabled_for_aggregate_accuracy=True,
        enabled_for_web=True,
        supports_training=False,
        supports_live_predictions=True,
        supports_backtest=True,
    ),
    ModelMetadata(
        slug="ckplus",
        display_name="CK+",
        version="ckplus_v1",
        prediction_table="predictions_ckplus",
        aggregate_accuracy_table="accuracy_ckplus",
        enabled_for_pipeline=False,
        enabled_for_backfill=False,
        enabled_for_accuracy_validation=False,
        enabled_for_aggregate_accuracy=False,
        enabled_for_web=False,
        supports_training=False,
        supports_live_predictions=False,
        supports_backtest=False,
        notes="Retired 2026-04-10. Replaced by Deal. Historical data retained in predictions_ckplus / accuracy_ckplus.",
    ),
    ModelMetadata(
        slug="deal",
        display_name="Deal",
        version="deal_v2",
        prediction_table="predictions_deal",
        aggregate_accuracy_table="accuracy_deal",
        enabled_for_pipeline=True,
        enabled_for_backfill=True,
        enabled_for_accuracy_validation=True,
        enabled_for_aggregate_accuracy=True,
        enabled_for_web=True,
        supports_training=True,
        supports_live_predictions=True,
        supports_backtest=True,
        notes="Promoted 2026-04-10. Probability calibration (ECE, top-10 mass) is a known follow-up item.",
    ),
)
