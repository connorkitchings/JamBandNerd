"""Band-keyed model metadata for the single-model-per-band architecture."""

from __future__ import annotations

from dataclasses import dataclass


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
        model_version="billy_fast_gbm_v12_gap_scaled_p50",
        notes=(
            "BillyFast V12: V10 HP baseline with plays_past_50_scaled = "
            "p50 * min(gap/4, 1.0) to penalize recently played songs."
        ),
    ),
    BandMetadata(
        band="um",
        model_version="um_fast_gbm_v12_gap_scaled_p50",
        notes="UMFast V12: dedup shows by date for correct gaps, plays_past_50_scaled = p50 * min(gap/4, 1.0), removed plays_past_10. 2 gap<=3 in top 10.",
    ),
)

