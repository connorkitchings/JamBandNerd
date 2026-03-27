"""Shared prediction serialization helpers."""

from __future__ import annotations

from typing import Any, Sequence


def serialize_predictions(
    *, model_slug: str, predictions: Sequence[Any]
) -> list[dict[str, Any]]:
    """Convert model outputs into the canonical JSON payload shape."""
    if model_slug == "notebook":
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

    if model_slug == "ckplus":
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

    if model_slug == "deal":
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

    raise ValueError(f"Invalid model slug: {model_slug}")
