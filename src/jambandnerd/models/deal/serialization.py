"""Deal model prediction serialization."""

from __future__ import annotations

from typing import Any, Sequence


def _prediction_value(prediction: Any, *names: str) -> Any:
    for name in names:
        if hasattr(prediction, name):
            return getattr(prediction, name)
    return None


def serialize_predictions(predictions: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert Deal-shaped predictions into the canonical JSON payload shape."""
    return [
        {
            "rank": i + 1,
            "song_name": prediction.song_name,
            "probability": prediction.probability,
            "current_gap": _prediction_value(prediction, "current_gap", "gap_shows"),
            "plays_past_year": _prediction_value(prediction, "plays_past_year"),
            "recent_plays_50": _prediction_value(prediction, "recent_plays_50"),
            "LTP": _prediction_value(prediction, "LTP"),
        }
        for i, prediction in enumerate(predictions)
    ]
