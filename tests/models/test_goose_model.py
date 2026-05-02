from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from jambandnerd.models.deal.features import DEAL_FEATURE_COLUMNS
from jambandnerd.models.goose.distilled import (
    GooseDistilledPredictor,
    _build_feature_columns,
)
from jambandnerd.models.goose.fast_predictor import (
    GOOSE_FAST_FEATURE_COLS,
    GOOSE_MATRIX_FEATURE_COLS,
    GOOSE_MATRIX_V2_FEATURE_COLS,
    GooseFastPredictor,
    GooseMatrixPredictor,
    GooseMatrixPredictorV2,
)
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


def test_goose_fast_predictor_owns_experiment_defaults() -> None:
    predictor = GooseFastPredictor(persist_artifacts=False)

    assert predictor.band == "goose"
    assert predictor.MODEL_VERSION == "goose_fast_gbm_v1"
    assert predictor.min_plays_threshold == 3
    assert predictor.retired_gap_threshold == 90
    assert predictor.training_window_shows == 60
    assert predictor.exclusion_window == 3
    assert predictor._FEATURE_COLS == GOOSE_FAST_FEATURE_COLS


def test_goose_fast_predictor_rejects_other_bands() -> None:
    with pytest.raises(ValueError, match="only supports band='goose'"):
        GooseFastPredictor(band="phish")


def test_goose_fast_predictor_trains_and_predicts_without_artifacts() -> None:
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

    predictor = GooseFastPredictor(persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert not frame.empty
    assert set(GOOSE_FAST_FEATURE_COLS).issubset(frame.columns)
    assert frame[GOOSE_FAST_FEATURE_COLS].notna().all().all()
    assert 0 < len(predictions) <= 10
    assert len({prediction.song_name for prediction in predictions}) == len(predictions)


def test_goose_fast_predictor_excludes_recent_songs() -> None:
    shows_df, setlists_df = _goose_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="goose",
    )

    predictor = GooseFastPredictor(persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=20)

    predicted = {prediction.song_name for prediction in predictions}
    assert predicted.isdisjoint(set(model_data.recently_played_songs))


def test_goose_fast_predictor_trains_without_venue_context() -> None:
    shows_df, setlists_df = _goose_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="goose",
    )

    predictor = GooseFastPredictor(persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert predictions


def test_goose_matrix_predictor_owns_experiment_defaults() -> None:
    predictor = GooseMatrixPredictor(persist_artifacts=False)

    assert predictor.band == "goose"
    assert predictor.MODEL_VERSION == "goose_matrix_gbm_v1"
    assert predictor._FEATURE_COLS == GOOSE_MATRIX_FEATURE_COLS
    assert set(GOOSE_FAST_FEATURE_COLS).issubset(GOOSE_MATRIX_FEATURE_COLS)
    for column in (
        "avg_ltp",
        "recent_avg_ltp",
        "gap_z_score",
        "pct_shows_1yr",
        "pct_shows_all_time",
        "diff_1yr_to_alltime",
        "pct_set_1",
        "pct_set_2",
        "pct_encore",
        "typical_position_pct",
        "position_consistency",
        "set_affinity",
    ):
        assert column in GOOSE_MATRIX_FEATURE_COLS


def test_goose_matrix_predictor_trains_and_predicts_without_artifacts() -> None:
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

    predictor = GooseMatrixPredictor(persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert not frame.empty
    assert set(GOOSE_MATRIX_FEATURE_COLS).issubset(frame.columns)
    assert frame[GOOSE_MATRIX_FEATURE_COLS].notna().all().all()
    assert 0 < len(predictions) <= 10
    assert len({prediction.song_name for prediction in predictions}) == len(predictions)


def test_goose_matrix_predictor_trains_without_venue_or_set_context() -> None:
    shows_df, setlists_df = _goose_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    setlists_df = setlists_df.drop(columns=["song_position"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="goose",
    )

    predictor = GooseMatrixPredictor(persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert frame["pct_set_1"].eq(0.0).all()
    assert frame["typical_position_pct"].eq(0.0).all()
    assert predictions


def test_goose_matrix_v2_predictor_owns_experiment_defaults() -> None:
    predictor = GooseMatrixPredictorV2(persist_artifacts=False)

    assert predictor.band == "goose"
    assert predictor.MODEL_VERSION == "goose_matrix_gbm_v2"
    assert predictor._FEATURE_COLS == GOOSE_MATRIX_V2_FEATURE_COLS
    assert set(GOOSE_MATRIX_FEATURE_COLS).issubset(GOOSE_MATRIX_V2_FEATURE_COLS)
    for column in (
        "plays_past_year",
        "plays_past_2yr",
        "pct_shows_6mo",
        "diff_6mo_to_1yr",
        "n_shows_same_venue",
        "n_shows_same_state",
        "debut_age_shows",
        "novelty_rank",
        "recent_anchor_cooc_mean",
        "recent_anchor_cooc_max",
        "last_show_cooc_mean",
        "last_show_cooc_max",
    ):
        assert column in GOOSE_MATRIX_V2_FEATURE_COLS


def test_goose_matrix_v2_predictor_trains_and_predicts_without_artifacts() -> None:
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

    predictor = GooseMatrixPredictorV2(persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert not frame.empty
    assert set(GOOSE_MATRIX_V2_FEATURE_COLS).issubset(frame.columns)
    assert frame[GOOSE_MATRIX_V2_FEATURE_COLS].notna().all().all()
    assert frame["plays_past_year"].ge(0.0).all()
    assert frame["recent_anchor_cooc_max"].between(0.0, 1.0).all()
    assert frame["last_show_cooc_max"].between(0.0, 1.0).all()
    assert 0 < len(predictions) <= 10
    assert len({prediction.song_name for prediction in predictions}) == len(predictions)


def test_goose_matrix_v2_predictor_keeps_fast_fallbacks() -> None:
    shows_df, setlists_df = _goose_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    setlists_df = setlists_df.drop(columns=["song_position"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="goose",
    )

    predictor = GooseMatrixPredictorV2(persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)

    assert not frame.empty
    assert frame["n_shows_same_venue"].eq(0.0).all()
    assert frame["n_shows_same_state"].eq(0.0).all()
    assert frame["pct_set_1"].eq(0.0).all()
    assert frame["recent_anchor_cooc_mean"].notna().all()
    assert frame["recent_anchor_cooc_max"].notna().all()


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


class TestGooseDistilledPredictor:
    def test_defaults_to_notebook_family(self) -> None:
        predictor = GooseDistilledPredictor()
        assert predictor.selected_families == ("notebook",)
        assert predictor.feature_columns == ["current_gap", "plays_past_year"]

    def test_rejects_other_bands(self) -> None:
        with pytest.raises(ValueError, match="only supports band='goose'"):
            GooseDistilledPredictor(band="billy")

    def test_rejects_unknown_family(self) -> None:
        with pytest.raises(ValueError, match="Unknown feature family"):
            GooseDistilledPredictor(families=("notebook", "nonsense"))

    def test_rejects_empty_families(self) -> None:
        with pytest.raises(ValueError, match="At least one feature family"):
            GooseDistilledPredictor(families=())

    def test_deduplicates_overlapping_families(self) -> None:
        predictor = GooseDistilledPredictor(
            families=("notebook", "gap"),
        )
        cols = predictor.feature_columns
        assert cols[0] == "current_gap"
        assert cols[1] == "plays_past_year"
        assert "avg_ltp" in cols
        assert len(cols) == len(set(cols))

    def test_model_version_reflects_families(self) -> None:
        predictor = GooseDistilledPredictor(
            families=("notebook", "debut"),
        )
        assert predictor.MODEL_VERSION == "goose_distilled_notebook_debut"

    def test_train_and_predict_notebook_only(self) -> None:
        shows_df, setlists_df = _goose_fixture()
        model_data = generate_model_data(
            shows_df, setlists_df, date(2024, 5, 20), band="goose",
        )
        predictor = GooseDistilledPredictor(
            families=("notebook",),
            persist_artifacts=False,
            min_training_shows=10,
            training_window_shows=25,
        )
        predictor.train(model_data)
        predictions = predictor.predict(model_data, top_k=10)

        assert predictions
        assert len(predictions) <= 10
        assert all(0.0 <= p.probability <= 1.0 for p in predictions)

    def test_feature_columns_additive_order(self) -> None:
        cols = _build_feature_columns(("notebook", "gap", "debut"))
        assert cols[:2] == ["current_gap", "plays_past_year"]
        assert "avg_ltp" in cols
        assert "novelty_rank" in cols
        assert cols.index("current_gap") < cols.index("avg_ltp")
        assert cols.index("avg_ltp") < cols.index("debut_age_shows")
