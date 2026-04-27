from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from jambandnerd.config.models import WEIGHTED_PRECISION_WEIGHTS


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
