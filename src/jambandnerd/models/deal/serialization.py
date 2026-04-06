"""Deal model prediction serialization."""

from __future__ import annotations

from typing import Any, Sequence


def serialize_predictions(predictions: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert Deal predictions into the canonical JSON payload shape."""
    return [
        {
            "rank": i + 1,
            "song_name": prediction.song_name,
            "probability": prediction.probability,
            "current_gap": prediction.current_gap,
            "plays_past_year": prediction.plays_past_year,
            "times_played": prediction.times_played,
            "LTP": prediction.LTP,
        }
        for i, prediction in enumerate(predictions)
    ]

