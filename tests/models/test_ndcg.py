"""Tests for NDCG metric computation."""

from __future__ import annotations

from jambandnerd.models.accuracy import _ndcg_at_k, compute_per_show_metrics


def test_ndcg_perfect_ranking() -> None:
    preds = ["A", "B", "C"]
    actual = ["A", "B", "C"]
    ndcg = _ndcg_at_k(preds, actual, k=3)
    assert ndcg == 1.0


def test_ndcg_no_matches() -> None:
    preds = ["X", "Y", "Z"]
    actual = ["A", "B"]
    ndcg = _ndcg_at_k(preds, actual, k=3)
    assert ndcg == 0.0


def test_ndcg_partial_match() -> None:
    preds = ["A", "X", "B"]
    actual = ["A", "B", "C"]
    ndcg = _ndcg_at_k(preds, actual, k=3)
    assert 0.0 < ndcg < 1.0


def test_ndcg_in_compute_per_show_metrics() -> None:
    result = compute_per_show_metrics(["A", "B", "C"], ["B", "D"], k=3)
    assert "ndcg" in result
    assert result["ndcg"] > 0.0


def test_ndcg_empty_actual() -> None:
    ndcg = _ndcg_at_k(["A", "B"], [], k=2)
    assert ndcg == 0.0
