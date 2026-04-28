"""Smoke tests for BandGbmPredictor against a synthetic Goose fixture."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from jambandnerd.models.deal.model import DealPrediction

try:
    from jambandnerd.models.gbm.predictor import BandGbmPredictor

    _LGB_AVAILABLE = True
except ImportError:
    _LGB_AVAILABLE = False

import pandas as pd

pytestmark = pytest.mark.skipif(not _LGB_AVAILABLE, reason="lightgbm not installed")


def _goose_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    from jambandnerd.transformations.gaps import generate_model_data  # noqa: F401

    shows: list[dict] = []
    setlists: list[dict] = []
    start = date(2024, 1, 1)
    rotation = [
        "Arcadia",
        "Hungersite",
        "Tumble",
        "Madhuvan",
        "Creatures",
        "Drive",
        "Echo of a Rose",
        "Factory Fiction",
        "Hot Tea",
        "Rockdale",
        "Animal",
        "Borne",
    ]
    for i in range(50):
        show_id = f"goose-{i}"
        show_date = start + timedelta(days=i * 3)
        shows.append(
            {
                "show_id": show_id,
                "show_date": show_date.isoformat(),
                "venue_name": "Capitol Theatre" if i % 2 == 0 else "Agora",
                "state": "NY" if i % 2 == 0 else "OH",
            }
        )
        songs = [rotation[(i + offset) % len(rotation)] for offset in range(7)]
        for pos, song in enumerate(songs, 1):
            setlists.append(
                {"show_id": show_id, "song_name": song, "song_position": pos}
            )

    return pd.DataFrame(shows), pd.DataFrame(setlists)


def test_gbm_predictor_trains_and_predicts() -> None:
    from jambandnerd.transformations.gaps import generate_model_data

    shows_df, setlists_df = _goose_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 6, 1), band="goose"
    )

    predictor = BandGbmPredictor(
        band="goose",
        persist_artifacts=False,
        min_training_shows=10,
        training_window_shows=30,
        min_data_in_leaf=1,
    )
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._booster is not None
    assert 0 < len(predictions) <= 10
    assert all(isinstance(p, DealPrediction) for p in predictions)
    song_names = [p.song_name for p in predictions]
    assert len(song_names) == len(set(song_names)), "Predictions must be unique songs"


def test_gbm_predictor_no_data_leakage() -> None:
    """Songs from the target show must not appear in training history."""
    from jambandnerd.transformations.gaps import generate_model_data

    shows_df, setlists_df = _goose_fixture()
    # Use last show as target; ref_date = day before
    last_show_date = pd.to_datetime(shows_df["show_date"]).max().date()
    ref_date = last_show_date - timedelta(days=1)
    model_data = generate_model_data(shows_df, setlists_df, ref_date, band="goose")

    # Historical plays must all be strictly before ref_date
    max_date = pd.Timestamp(model_data.historical_plays["show_date"].max()).date()
    assert max_date < ref_date


def test_gbm_predictor_rejects_prediction_without_training() -> None:
    """Predict on zero-history ModelData must return empty list, not raise."""
    from jambandnerd.transformations.gaps import generate_model_data

    empty_shows = pd.DataFrame(columns=["show_id", "show_date", "venue_name", "state"])
    empty_sets = pd.DataFrame(columns=["show_id", "song_name", "song_position"])
    model_data = generate_model_data(
        empty_shows, empty_sets, date(2024, 1, 1), band="goose"
    )

    predictor = BandGbmPredictor(band="goose", persist_artifacts=False)
    result = predictor.predict(model_data, top_k=10)
    assert result == []
