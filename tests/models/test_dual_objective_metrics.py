"""Tests for dual_objective_score and is_band_promotion_eligible."""

from __future__ import annotations

import pytest

from jambandnerd.models.accuracy import (
    BacktestSummary,
    dual_f1_objective_score,
    dual_objective_score,
)
from jambandnerd.models.readiness import is_band_promotion_eligible


def _summary(
    band: str = "goose",
    model_version: str = "v1",
    n_shows: int = 100,
    p10: float = 0.3,
    p25: float = 0.4,
    p50: float = 0.5,
    r10: float = 0.2,
    r25: float = 0.3,
    r50: float = 0.4,
    f1_10: float | None = None,
    f1_25: float | None = None,
    f1_50: float | None = None,
) -> BacktestSummary:
    from jambandnerd.models.accuracy import (
        compute_weighted_precision_score,
    )
    from jambandnerd.models.accuracy import (
        dual_f1_objective_score as df1os,
    )
    from jambandnerd.models.accuracy import (
        dual_objective_score as dos,
    )

    _f1_10 = (
        f1_10
        if f1_10 is not None
        else 2 * p10 * r10 / (p10 + r10) if (p10 + r10) > 0 else 0.0
    )
    _f1_25 = (
        f1_25
        if f1_25 is not None
        else 2 * p25 * r25 / (p25 + r25) if (p25 + r25) > 0 else 0.0
    )
    _f1_50 = (
        f1_50
        if f1_50 is not None
        else 2 * p50 * r50 / (p50 + r50) if (p50 + r50) > 0 else 0.0
    )

    return BacktestSummary(
        band=band,
        model_version=model_version,
        n_shows=n_shows,
        p10=p10,
        p25=p25,
        p50=p50,
        r10=r10,
        r25=r25,
        r50=r50,
        f1_10=_f1_10,
        f1_25=_f1_25,
        f1_50=_f1_50,
        weighted_score=compute_weighted_precision_score(p10, p25, p50),
        dual_score=dos(p10, r50),
        dual_f1_score=df1os(_f1_10, _f1_50),
    )


# ── dual_objective_score ──────────────────────────────────────────────────────


def test_dual_score_equal_weight() -> None:
    assert abs(dual_objective_score(0.4, 0.6) - 0.5) < 1e-9


def test_dual_score_alpha_zero_gives_r50() -> None:
    assert abs(dual_objective_score(0.4, 0.6, alpha=0.0) - 0.6) < 1e-9


def test_dual_score_alpha_one_gives_p10() -> None:
    assert abs(dual_objective_score(0.4, 0.6, alpha=1.0) - 0.4) < 1e-9


def test_dual_score_both_zero() -> None:
    assert dual_objective_score(0.0, 0.0) == 0.0


def test_dual_score_both_one() -> None:
    assert abs(dual_objective_score(1.0, 1.0) - 1.0) < 1e-9


# ── is_band_promotion_eligible ────────────────────────────────────────────────


def test_promotion_eligible_when_both_metrics_improve() -> None:
    incumbent = _summary(
        model_version="v1",
        p10=0.30,
        r50=0.40,
        f1_25=0.30,
        p25=0.35,
    )
    candidate = _summary(
        model_version="v2",
        p10=0.35,
        r50=0.45,
        f1_25=0.35,
        p25=0.38,
    )
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert decision.eligible
    assert decision.blockers == []
    assert abs(decision.p10_delta - 0.05) < 1e-9
    assert abs(decision.r50_delta - 0.05) < 1e-9


def test_promotion_blocked_when_p10_regresses() -> None:
    incumbent = _summary(
        model_version="v1",
        p10=0.30,
        r50=0.40,
        f1_25=0.30,
        p25=0.35,
    )
    candidate = _summary(
        model_version="v2",
        p10=0.25,
        r50=0.45,
        f1_25=0.35,
        p25=0.38,
    )
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert not decision.eligible
    assert any("p10_delta" in b for b in decision.blockers)


def test_promotion_blocked_when_r50_regresses() -> None:
    incumbent = _summary(
        model_version="v1",
        p10=0.30,
        r50=0.40,
        f1_25=0.30,
        p25=0.35,
    )
    candidate = _summary(
        model_version="v2",
        p10=0.35,
        r50=0.38,
        f1_25=0.35,
        p25=0.38,
    )
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert not decision.eligible
    assert any("r50_delta" in b for b in decision.blockers)


def test_promotion_blocked_when_insufficient_shows() -> None:
    incumbent = _summary(
        model_version="v1",
        p10=0.30,
        r50=0.40,
        f1_25=0.30,
        p25=0.35,
    )
    candidate = _summary(
        model_version="v2",
        n_shows=50,
        p10=0.35,
        r50=0.45,
        f1_25=0.35,
        p25=0.38,
    )
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert not decision.eligible
    assert any("insufficient_shows" in b for b in decision.blockers)


def test_promotion_raises_on_band_mismatch() -> None:
    incumbent = _summary(band="goose", model_version="v1")
    candidate = _summary(band="phish", model_version="v2")
    with pytest.raises(ValueError, match="Band mismatch"):
        is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)


def test_promotion_version_fields_populated() -> None:
    incumbent = _summary(
        model_version="goose_phase_b_v1",
        p10=0.30,
        r50=0.40,
        f1_25=0.30,
        p25=0.35,
    )
    candidate = _summary(
        model_version="goose_phase_b_v2",
        p10=0.35,
        r50=0.45,
        f1_25=0.35,
        p25=0.38,
    )
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert decision.candidate_version == "goose_phase_b_v2"
    assert decision.incumbent_version == "goose_phase_b_v1"


# ── F1-based dual objective ──────────────────────────────────────────────────


def test_dual_f1_score_equal_weight() -> None:
    assert abs(dual_f1_objective_score(0.4, 0.6) - 0.5) < 1e-9


def test_dual_f1_score_alpha_zero_gives_f1_50() -> None:
    assert abs(dual_f1_objective_score(0.4, 0.6, alpha=0.0) - 0.6) < 1e-9


def test_promotion_blocked_when_f1_25_regresses() -> None:
    incumbent = _summary(model_version="v1", p10=0.30, r50=0.40, f1_25=0.35)
    candidate = _summary(model_version="v2", p10=0.35, r50=0.45, f1_25=0.33)
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert not decision.eligible
    assert any("f1_25_delta" in b for b in decision.blockers)


def test_promotion_blocked_when_p25_regresses_beyond_threshold() -> None:
    incumbent = _summary(model_version="v1", p10=0.30, r50=0.40, p25=0.40)
    candidate = _summary(model_version="v2", p10=0.35, r50=0.45, p25=0.38)
    decision = is_band_promotion_eligible(candidate=candidate, incumbent=incumbent)
    assert not decision.eligible
    assert any("p25_regression" in b for b in decision.blockers)
