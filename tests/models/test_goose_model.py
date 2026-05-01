from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from jambandnerd.models.deal.features import DEAL_FEATURE_COLUMNS
from jambandnerd.models.goose.model import (
    GOOSE_FEATURE_COLUMNS,
    GooseGbmNotebookBlendPredictor,
    GoosePredictor,
    _rank_blended_candidate_features,
)
from jambandnerd.transformations.gaps import generate_model_data


def _goose_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    shows: list[dict[str, object]] = []
    setlists: list[dict[str, object]] = []
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

    for show_index in range(45):
        show_id = f"goose-{show_index}"
        show_date = start + timedelta(days=show_index * 3)
        shows.append(
            {
                "show_id": show_id,
                "show_date": show_date.isoformat(),
                "venue_name": "Capitol Theatre" if show_index % 2 == 0 else "Agora",
                "city": "Port Chester" if show_index % 2 == 0 else "Cleveland",
                "state": "NY" if show_index % 2 == 0 else "OH",
                "country": "USA",
            }
        )
        songs = [rotation[(show_index + offset) % len(rotation)] for offset in range(6)]
        if show_index % 4 == 0:
            songs.append("Elmeg The Wise")
        for position, song_name in enumerate(songs, start=1):
            setlists.append(
                {
                    "show_id": show_id,
                    "song_name": song_name,
                    "song_position": position,
                }
            )

    return pd.DataFrame(shows), pd.DataFrame(setlists)


def test_goose_predictor_owns_phase_b_defaults() -> None:
    predictor = GoosePredictor(persist_artifacts=False)

    assert predictor.band == "goose"
    assert predictor.MODEL_VERSION == "goose_phase_b_v1"
    assert predictor.min_plays_threshold == 3
    assert predictor.retired_gap_threshold == 90
    assert predictor.training_window_shows == 60
    assert predictor.min_training_shows == 20
    assert predictor.positive_weight_cap == 2.0
    assert predictor.feature_columns == GOOSE_FEATURE_COLUMNS
    assert set(GOOSE_FEATURE_COLUMNS).issubset(DEAL_FEATURE_COLUMNS)


def test_goose_predictor_rejects_other_bands() -> None:
    with pytest.raises(ValueError, match="only supports band='goose'"):
        GoosePredictor(band="phish")


def test_goose_predictor_trains_and_predicts_without_artifacts() -> None:
    shows_df, setlists_df = _goose_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="goose",
    )

    predictor = GoosePredictor(
        persist_artifacts=False,
        min_training_shows=10,
        training_window_shows=25,
    )
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor.model is not None
    assert 0 < len(predictions) <= 10
    assert len({prediction.song_name for prediction in predictions}) == len(predictions)


def test_goose_notebook_blend_defaults_to_evidence_alpha() -> None:
    predictor = GooseGbmNotebookBlendPredictor(persist_artifacts=False)

    assert predictor.MODEL_VERSION == "goose_phase_b_v4_gbm_notebook_blend"
    assert predictor.notebook_blend_alpha == pytest.approx(0.60)


def test_goose_notebook_blend_rejects_invalid_alpha() -> None:
    with pytest.raises(ValueError, match="notebook_blend_alpha"):
        GooseGbmNotebookBlendPredictor(
            persist_artifacts=False,
            notebook_blend_alpha=1.1,
        )


def test_goose_notebook_blend_ranking_combines_rank_scores() -> None:
    candidates = pd.DataFrame(
        [
            {
                "song_name": "GBM Lead",
                "gbm_rank_score": 1.0,
                "notebook_rank_score": 0.0,
            },
            {
                "song_name": "Notebook Lead",
                "gbm_rank_score": 0.0,
                "notebook_rank_score": 1.0,
            },
            {
                "song_name": "Consensus",
                "gbm_rank_score": 0.7,
                "notebook_rank_score": 0.8,
            },
        ]
    )

    ranked = _rank_blended_candidate_features(candidates, alpha=0.60)

    assert ranked["song_name"].tolist() == [
        "Consensus",
        "GBM Lead",
        "Notebook Lead",
    ]
    assert ranked.iloc[0]["probability"] == pytest.approx(0.74)


def test_goose_notebook_blend_trains_and_predicts_without_artifacts() -> None:
    shows_df, setlists_df = _goose_fixture()
    target_show = {
        "show_id": "future-goose",
        "show_date": "2024-05-20",
        "venue_name": "Capitol Theatre",
        "city": "Port Chester",
        "state": "NY",
        "country": "USA",
    }
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="goose",
        target_show_context=target_show,
    )

    predictor = GooseGbmNotebookBlendPredictor(
        persist_artifacts=False,
        min_training_shows=10,
        training_window_shows=25,
        n_estimators=5,
    )
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictions
    assert 0 < len(predictions) <= 10
    assert len({prediction.song_name for prediction in predictions}) == len(predictions)
    assert all(0.0 <= prediction.probability <= 1.0 for prediction in predictions)
