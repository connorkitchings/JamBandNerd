from __future__ import annotations

from src.jambandnerd.models.accuracy import compute_weighted_precision_score


def test_all_zeros():
    assert compute_weighted_precision_score(0.0, 0.0, 0.0) == 0.0


def test_all_ones():
    score = compute_weighted_precision_score(1.0, 1.0, 1.0)
    assert abs(score - 1.0) < 1e-9


def test_only_p25_contributes():
    # p10=0, p50=0 → score = 0.7 * p25
    score = compute_weighted_precision_score(0.0, 1.0, 0.0)
    assert abs(score - 0.7) < 1e-9


def test_weights_sum_to_one():
    from src.jambandnerd.config.models import WEIGHTED_PRECISION_WEIGHTS

    total = sum(WEIGHTED_PRECISION_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9


def test_typical_values():
    score = compute_weighted_precision_score(0.4, 0.6, 0.3)
    expected = 0.2 * 0.4 + 0.7 * 0.6 + 0.1 * 0.3
    assert abs(score - expected) < 1e-9
