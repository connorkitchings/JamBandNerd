"""CK+ model prediction serialization."""

from __future__ import annotations

from typing import Any, Sequence


def serialize_predictions(predictions: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert CK+ predictions into the canonical JSON payload shape."""
    return [
        {
            "rank": i + 1,
            "song_name": prediction.song_name,
            "times_played": prediction.times_played,
            "current_gap": prediction.current_gap,
            "avg_gap": prediction.avg_gap,
            "recent_avg_gap": prediction.recent_avg_gap,
            "gap_ratio": prediction.gap_ratio,
            "gap_z_score": prediction.gap_z_score,
            "ckplus_score": prediction.ckplus_score,
            "LTP": prediction.LTP,
        }
        for i, prediction in enumerate(predictions)
    ]

