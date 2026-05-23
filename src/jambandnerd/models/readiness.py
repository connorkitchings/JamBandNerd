"""Band-keyed promotion gate for single-model-per-band architecture."""

from __future__ import annotations

from dataclasses import dataclass

from jambandnerd.models.accuracy import BacktestSummary


@dataclass(frozen=True)
class PromotionDecision:
    """Result of evaluating whether a candidate model should replace the incumbent."""

    eligible: bool
    candidate_version: str
    incumbent_version: str
    n_shows: int
    p10_delta: float
    p25_delta: float
    r50_delta: float
    f1_25_delta: float
    blockers: list[str]


def is_band_promotion_eligible(
    *,
    candidate: BacktestSummary,
    incumbent: BacktestSummary,
    min_p10_delta: float = 0.02,
    min_r50_delta: float = 0.02,
    min_f1_25_delta: float = 0.02,
    max_p25_regression: float = 0.01,
    min_shows: int = 100,
) -> PromotionDecision:
    """Gate whether a Phase B candidate should replace the incumbent model.

    The candidate must improve F1@25 and p@10 without regressing p@25
    beyond ``max_p25_regression``, evaluated across at least ``min_shows``
    shows.  The legacy p@10/r@50 dual-objective checks are retained
    side-by-side during the metric transition period.
    """
    if candidate.band != incumbent.band:
        raise ValueError(
            f"Band mismatch: candidate={candidate.band} incumbent={incumbent.band}"
        )

    p10_delta = candidate.p10 - incumbent.p10
    r50_delta = candidate.r50 - incumbent.r50
    f1_25_delta = candidate.f1_25 - incumbent.f1_25
    p25_delta = candidate.p25 - incumbent.p25
    blockers: list[str] = []

    if candidate.n_shows < min_shows:
        blockers.append(f"insufficient_shows:{candidate.n_shows}<{min_shows}")
    if f1_25_delta < min_f1_25_delta:
        blockers.append(
            f"f1_25_delta_below_threshold:{f1_25_delta:.4f}<{min_f1_25_delta}"
        )
    if p25_delta < -max_p25_regression:
        blockers.append(
            f"p25_regression_exceeds_threshold:{p25_delta:.4f}<-{max_p25_regression}"
        )
    if p10_delta < min_p10_delta:
        blockers.append(f"p10_delta_below_threshold:{p10_delta:.4f}<{min_p10_delta}")
    if r50_delta < min_r50_delta:
        blockers.append(f"r50_delta_below_threshold:{r50_delta:.4f}<{min_r50_delta}")

    return PromotionDecision(
        eligible=not blockers,
        candidate_version=candidate.model_version,
        incumbent_version=incumbent.model_version,
        n_shows=candidate.n_shows,
        p10_delta=p10_delta,
        p25_delta=p25_delta,
        r50_delta=r50_delta,
        f1_25_delta=f1_25_delta,
        blockers=blockers,
    )
