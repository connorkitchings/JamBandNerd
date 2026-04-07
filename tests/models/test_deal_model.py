from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.jambandnerd.models.deal.features import (
    DEAL_FEATURE_COLUMNS,
    build_training_frame,
    get_candidate_features,
)
from src.jambandnerd.models.deal.model import DealPredictor
from src.jambandnerd.transformations.gaps import generate_model_data


def build_deal_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    songs_by_show: list[list[str]] = []
    for index in range(60):
        songs = ["Song A"]
        if index % 2 == 0:
            songs.append("Song B")
        if index % 3 == 0:
            songs.append("Song C")
        if index % 4 == 0:
            songs.append("Song D")
        if index % 5 == 0:
            songs.append("Song E")
        if index % 6 == 0:
            songs.append("Song F")
        if index % 7 == 0:
            songs.append("Song G")
        if index % 8 == 0:
            songs.append("Song H")
        if index % 9 == 0:
            songs.append("Song I")
        if index % 10 == 0:
            songs.append("Song J")
        if index % 11 == 0:
            songs.append("Song K")
        if index >= 48:
            songs.append("Late Debut")
        songs_by_show.append(songs)

    start = date(2024, 1, 1)
    shows = []
    setlists = []
    for index, songs in enumerate(songs_by_show, start=1):
        show_id = f"show-{index}"
        show_date = start + timedelta(days=index)
        shows.append(
            {
                "show_id": show_id,
                "show_date": show_date.isoformat(),
                "venue_name": "Venue A" if index % 2 == 0 else "Venue B",
                "city": "City",
                "state": "GA" if index % 3 == 0 else "TN",
            }
        )
        for position, song_name in enumerate(songs, start=1):
            setlists.append(
                {
                    "show_id": show_id,
                    "song_name": song_name,
                    "song_position": position,
                }
            )

    return pd.DataFrame(shows), pd.DataFrame(setlists)


def test_deal_feature_generation_respects_reference_boundary() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 5), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    assert "Late Debut" not in set(candidates["song_name"])


def test_deal_training_frame_builds_true_per_show_rows() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    training_frame, summary = build_training_frame(
        model_data,
        band="goose",
        min_plays_threshold=2,
        retired_gap_threshold=200,
        min_training_shows=10,
        training_window_shows=20,
    )

    assert not training_frame.empty
    assert set(DEAL_FEATURE_COLUMNS).issubset(training_frame.columns)
    assert training_frame["target_show_date"].nunique() > 1
    assert summary.positive_rows > 0
    assert summary.negative_rows > summary.positive_rows


def test_deal_predictor_produces_non_uniform_probabilities(
    tmp_path, monkeypatch
) -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    monkeypatch.setattr(DealPredictor, "MODEL_DIR", tmp_path)
    predictor = DealPredictor(band="goose", min_plays_threshold=2)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=20)

    probabilities = np.array([prediction.probability for prediction in predictions])
    assert len(predictions) > 5
    assert np.std(probabilities) > 0.001
    assert probabilities.max() > probabilities.min()


def test_deal_model_roundtrip_preserves_ranking(tmp_path, monkeypatch) -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    monkeypatch.setattr(DealPredictor, "MODEL_DIR", tmp_path)
    predictor = DealPredictor(band="goose", min_plays_threshold=2)
    predictor.train(model_data)
    original = predictor.predict(model_data, top_k=10)

    reloaded = DealPredictor(band="goose", min_plays_threshold=2)
    reloaded.MODEL_DIR = tmp_path
    restored = reloaded.predict(model_data, top_k=10)

    assert [prediction.song_name for prediction in original[:5]] == [
        prediction.song_name for prediction in restored[:5]
    ]
