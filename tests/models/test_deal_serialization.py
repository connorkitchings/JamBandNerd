from __future__ import annotations

from dataclasses import dataclass

from jambandnerd.models.deal.serialization import serialize_predictions


@dataclass
class _FastPrediction:
    song_name: str
    probability: float
    gap_shows: int


def test_deal_serializer_accepts_fast_prediction_shape() -> None:
    payload = serialize_predictions(
        [_FastPrediction(song_name="Tweezer", probability=0.42, gap_shows=9)]
    )

    assert payload == [
        {
            "rank": 1,
            "song_name": "Tweezer",
            "probability": 0.42,
            "current_gap": 9,
            "plays_past_year": None,
            "recent_plays_50": None,
            "LTP": None,
        }
    ]
