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
    default_top_k: int = 50
    notes: str | None = None


BAND_METADATA: tuple[BandMetadata, ...] = (
    BandMetadata(
        band="goose",
        model_version="goose_fast_rank_v1_candidate_relaxed_special_nbtop10",
        notes=(
            "Full-history LightGBM with notebook_rank_score, special-show "
            "recent-repeat repair, and Notebook top-10 guard. Beats registered "
            "Goose and Notebook floor on dual, p@25, r@50, and F1@25."
        ),
    ),
    BandMetadata(
        band="phish",
        model_version="phish_fast_gbm_v2_feat_notebook_rank_venue_run",
        notes="Stacked notebook_rank + venue_run on PhishFast V2. dual=0.419 (+0.014 vs V2).",
    ),
    BandMetadata(
        band="wsp",
        model_version="wsp_fast_gbm_v2",
        notes="V2: long rotation features + lr=0.03, rounds=700. dual=0.448 (+0.014 vs V1).",
    ),
    BandMetadata(
        band="billy",
        model_version="billy_fast_gbm_v10_hp_tuned",
        notes="V3 features with HP-tuned leaves=15 + min_leaf=10. dual=0.388 (+0.011 vs V3).",
    ),
    BandMetadata(
        band="um",
        model_version="um_fast_gbm_v2",
        notes="UMFast V2 (HP-tuned leaves=15, lr=0.07, lambda=0.1). dual=0.343 (+0.020 vs V1).",
    ),
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
