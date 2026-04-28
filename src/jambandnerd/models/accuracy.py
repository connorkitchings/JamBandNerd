from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from jambandnerd.config.models import (
    BAND_DUAL_OBJECTIVE_ALPHA,
    DUAL_OBJECTIVE_ALPHA,
    WEIGHTED_PRECISION_WEIGHTS,
)


@dataclass
class TopKMetrics:
    k: int
    hit_rate: float
    avg_matches: float
    precision: float
    recall: float
    f1: float


def _safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def compute_per_show_metrics(
    pred_songs: List[str], actual_songs: Iterable[str], k: int
) -> Dict[str, float]:
    """Compute per-show top-k metrics given predictions and actual setlist songs (unique)."""
    topk = pred_songs[:k]
    actual_set = set(actual_songs)
    matches = len(set(topk) & actual_set)
    hit = 1.0 if matches > 0 else 0.0
    precision = _safe_div(matches, k)
    recall = _safe_div(matches, len(actual_set))
    f1 = (
        _safe_div(2 * precision * recall, precision + recall)
        if (precision + recall)
        else 0.0
    )
    return {
        "hit": hit,
        "matches": float(matches),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def compute_weighted_precision_score(p10: float, p25: float, p50: float) -> float:
    """Weighted blend of precision@k values using configured weights."""
    return (
        WEIGHTED_PRECISION_WEIGHTS["p10"] * p10
        + WEIGHTED_PRECISION_WEIGHTS["p25"] * p25
        + WEIGHTED_PRECISION_WEIGHTS["p50"] * p50
    )


@dataclass(frozen=True)
class BacktestSummary:
    """Aggregated metrics from a walk-forward backtest on a fixed show window."""

    band: str
    model_version: str
    n_shows: int
    p10: float
    p25: float
    p50: float
    r10: float
    r25: float
    r50: float
    weighted_score: float
    dual_score: float


def dual_objective_score(p10: float, r50: float, alpha: float | None = None) -> float:
    """Blend p@10 and r@50 into a single scalar: α·p10 + (1−α)·r50."""
    a = DUAL_OBJECTIVE_ALPHA if alpha is None else alpha
    return a * p10 + (1.0 - a) * r50


def dual_objective_score_for_band(p10: float, r50: float, band: str) -> float:
    """dual_objective_score using the per-band alpha override when available."""
    alpha = BAND_DUAL_OBJECTIVE_ALPHA.get(band, DUAL_OBJECTIVE_ALPHA)
    return dual_objective_score(p10, r50, alpha=alpha)


def aggregate_metrics(per_show: List[Dict[str, float]], k: int) -> TopKMetrics:
    n = len(per_show) or 1
    hit_rate = sum(m["hit"] for m in per_show) / n
    avg_matches = sum(m["matches"] for m in per_show) / n
    precision = sum(m["precision"] for m in per_show) / n
    recall = sum(m["recall"] for m in per_show) / n
    f1 = sum(m["f1"] for m in per_show) / n
    return TopKMetrics(
        k=k,
        hit_rate=hit_rate,
        avg_matches=avg_matches,
        precision=precision,
        recall=recall,
        f1=f1,
    )
