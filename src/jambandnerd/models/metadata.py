"""Band-keyed model metadata for the single-model-per-band architecture."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BandMetadata:
    """Per-band metadata for the single-model-per-band architecture."""

    band: str
    model_version: str
    default_top_k: int = 25
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
