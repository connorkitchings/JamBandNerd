"""Shared model metadata used by the registry and compatibility shims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelLifecycleStage = Literal[
    "experimental",
    "readiness_verified",
    "web_promoted",
    "retired",
]
ModelWebVisibility = Literal["hidden", "promoted"]


@dataclass(frozen=True)
class ModelMetadata:
    """Model metadata that is independent of predictor imports."""

    slug: str
    display_name: str
    version: str
    prediction_table: str
    enabled_for_pipeline: bool
    enabled_for_backfill: bool
    enabled_for_accuracy_validation: bool
    enabled_for_web: bool
    supports_training: bool
    supports_live_predictions: bool
    supports_backtest: bool
    lifecycle_stage: ModelLifecycleStage
    web_visibility: ModelWebVisibility
    readiness_windows: tuple[int, ...] = (100,)
    readiness_baselines: tuple[str, ...] = ()
    default_top_k: int = 50
    notes: str | None = None


@dataclass(frozen=True)
class BandMetadata:
    """Per-band metadata for the single-model-per-band architecture."""

    band: str
    model_version: str
    default_top_k: int = 25
    notes: str | None = None


BAND_METADATA: tuple[BandMetadata, ...] = (
    BandMetadata(band="goose", model_version="goose_phase_b_v1"),
    BandMetadata(band="phish", model_version="phish_baseline_v1"),
    BandMetadata(band="wsp", model_version="wsp_baseline_v1"),
    BandMetadata(band="billy", model_version="billy_baseline_v1"),
    BandMetadata(band="um", model_version="um_baseline_v1"),
)


MODEL_METADATA: tuple[ModelMetadata, ...] = (
    ModelMetadata(
        slug="notebook",
        display_name="Notebook",
        version="notebook_v1",
        prediction_table="predictions",
        enabled_for_pipeline=True,
        enabled_for_backfill=True,
        enabled_for_accuracy_validation=True,
        enabled_for_web=True,
        supports_training=False,
        supports_live_predictions=True,
        supports_backtest=True,
        lifecycle_stage="web_promoted",
        web_visibility="promoted",
        readiness_windows=(100,),
        readiness_baselines=(),
    ),
    ModelMetadata(
        slug="ckplus",
        display_name="CK+",
        version="ckplus_v1",
        prediction_table="predictions",
        enabled_for_pipeline=False,
        enabled_for_backfill=False,
        enabled_for_accuracy_validation=False,
        enabled_for_web=False,
        supports_training=False,
        supports_live_predictions=False,
        supports_backtest=False,
        lifecycle_stage="retired",
        web_visibility="hidden",
        readiness_windows=(50,),
        readiness_baselines=(),
        notes="Retired 2026-04-11. Replaced by Deal.",
    ),
    ModelMetadata(
        slug="deal",
        display_name="Deal",
        version="deal_v2",
        prediction_table="predictions",
        enabled_for_pipeline=True,
        enabled_for_backfill=True,
        enabled_for_accuracy_validation=True,
        enabled_for_web=True,
        supports_training=True,
        supports_live_predictions=True,
        supports_backtest=True,
        lifecycle_stage="web_promoted",
        web_visibility="promoted",
        readiness_windows=(100,),
        readiness_baselines=("notebook",),
        notes="Promoted 2026-04-11. Replaces CK+.",
    ),
)
