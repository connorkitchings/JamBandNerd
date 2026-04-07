"""Notebook model prediction serialization."""

from __future__ import annotations

from typing import Any, Sequence


def serialize_predictions(predictions: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert notebook predictions into the canonical JSON payload shape."""
    return [
        {
            "rank": i + 1,
            "song_name": prediction.song_name,
            "plays_past_year": prediction.plays_past_year,
            "current_gap": prediction.current_gap,
            "last_played_date": prediction.last_played_date,
        }
        for i, prediction in enumerate(predictions)
    ]
