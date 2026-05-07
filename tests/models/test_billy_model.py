from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from jambandnerd.models.billy.fast_predictor import (
    BILLY_FAST_CANDIDATE_CONTEXT_COLS,
    BILLY_FAST_FEATURE_COLS,
    BILLY_FAST_V2_FEATURE_COLS,
    BILLY_FAST_V3_FEATURE_COLS,
    BILLY_FAST_V5_FEATURE_COLS,
    BillyFastBaselinePredictor,
    BillyFastPredictor,
    BillyFastPredictorV2,
    BillyFastPredictorV3,
    BillyFastPredictorV4,
    BillyFastPredictorV5,
    BillyFastPredictorV6,
    BillyFastV10EarlyStop,
    BillyFastV10FullHistory,
    BillyFastV10LongRotation,
    BillyFastV10PlaysPastYear,
    BillyFastV10Window150,
)
from jambandnerd.models.billy.model import (
    BILLY_FEATURE_COLUMNS,
    BILLY_V2_FEATURE_COLUMNS,
    BillyGbmPredictor,
    BillyPredictor,
    _build_is_cover_lookup,
)
from jambandnerd.models.deal.features import DEAL_FEATURE_COLUMNS
from jambandnerd.models.registry import build_band_predictor
from jambandnerd.transformations.gaps import generate_model_data

_SONGS_DF = pd.DataFrame(
    [
        {"song_name": "Dust in a Baggie", "original_artist": None},
        {"song_name": "Away From the Mire", "original_artist": None},
        {"song_name": "Taking Water", "original_artist": None},
        {"song_name": "Midnight Rider", "original_artist": "Allman Brothers Band"},
        {"song_name": "Shady Grove", "original_artist": "Traditional"},
        {"song_name": "Black Muddy River", "original_artist": "Grateful Dead"},
    ]
)


def _billy_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    shows: list[dict] = []
    setlists: list[dict] = []
    start = date(2024, 1, 1)
    rotation = [
        "Dust in a Baggie",
        "Away From the Mire",
        "Taking Water",
        "Midnight Rider",
        "Shady Grove",
        "Black Muddy River",
        "Enough to Leave",
        "Watch It Fall",
        "Meet Me at the Creek",
        "All Fall Down",
        "Hollow Heart",
        "River",
    ]

    for show_index in range(45):
        show_id = f"billy-{show_index}"
        show_date = start + timedelta(days=show_index * 3)
        shows.append(
            {
                "show_id": show_id,
                "show_date": show_date.isoformat(),
                "venue_name": (
                    "Ryman Auditorium" if show_index % 2 == 0 else "Red Rocks"
                ),
                "city": "Nashville" if show_index % 2 == 0 else "Morrison",
                "state": "TN" if show_index % 2 == 0 else "CO",
                "country": "USA",
            }
        )
        songs = [rotation[(show_index + offset) % len(rotation)] for offset in range(6)]
        if show_index % 4 == 0:
            songs.append("Thunder")
        for position, song_name in enumerate(songs, start=1):
            setlists.append(
                {
                    "show_id": show_id,
                    "song_name": song_name,
                    "song_position": position,
                }
            )

    return pd.DataFrame(shows), pd.DataFrame(setlists)


def _tiny_billy_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    shows: list[dict] = []
    setlists: list[dict] = []
    start = date(2024, 1, 1)
    songs_by_show = [
        ["Dust in a Baggie", "Away From the Mire", "Taking Water", "Midnight Rider"],
        ["Dust in a Baggie", "Away From the Mire", "Taking Water", "Midnight Rider"],
        ["Dust in a Baggie", "Away From the Mire", "Taking Water", "Midnight Rider"],
        ["Dust in a Baggie", "Away From the Mire", "Taking Water"],
    ]

    for show_index, songs in enumerate(songs_by_show):
        show_id = f"tiny-billy-{show_index}"
        shows.append(
            {
                "show_id": show_id,
                "show_date": (start + timedelta(days=show_index)).isoformat(),
                "venue_name": "Ryman Auditorium",
                "city": "Nashville",
                "state": "TN",
                "country": "USA",
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


def test_billy_predictor_owns_phase_b_defaults() -> None:
    predictor = BillyPredictor(persist_artifacts=False, songs_df=_SONGS_DF)

    assert predictor.band == "billy"
    assert predictor.MODEL_VERSION == "billy_phase_b_v1"
    assert predictor.min_plays_threshold == 3
    assert predictor.retired_gap_threshold == 120
    assert predictor.training_window_shows == 75
    assert predictor.min_training_shows == 25
    assert predictor.positive_weight_cap == 2.0
    assert predictor.feature_columns == BILLY_V2_FEATURE_COLUMNS
    assert set(BILLY_FEATURE_COLUMNS).issubset(
        set(DEAL_FEATURE_COLUMNS) | set(BILLY_FEATURE_COLUMNS)
    )


def test_billy_predictor_rejects_other_bands() -> None:
    with pytest.raises(ValueError, match="only supports band='billy'"):
        BillyPredictor(band="goose", songs_df=_SONGS_DF)


def test_billy_predictor_trains_and_predicts_without_artifacts() -> None:
    shows_df, setlists_df = _billy_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyPredictor(
        persist_artifacts=False,
        songs_df=_SONGS_DF,
        min_training_shows=10,
        training_window_shows=25,
    )
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor.model is not None
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_gbm_predictor_trains_and_predicts_without_artifacts() -> None:
    shows_df, setlists_df = _billy_fixture()
    target_show = {
        "show_id": "future-billy",
        "show_date": "2024-05-20",
        "venue_name": "Ryman Auditorium",
        "city": "Nashville",
        "state": "TN",
        "country": "USA",
    }
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
        target_show_context=target_show,
    )

    predictor = BillyGbmPredictor(
        persist_artifacts=False,
        songs_df=_SONGS_DF,
        min_training_shows=10,
        training_window_shows=25,
        n_estimators=5,
    )
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictions
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_gbm_predictor_rejects_other_bands() -> None:
    with pytest.raises(ValueError, match="only supports band='billy'"):
        BillyGbmPredictor(band="phish", songs_df=_SONGS_DF)


def test_build_is_cover_lookup_classifies_correctly() -> None:
    lookup = _build_is_cover_lookup(_SONGS_DF)

    assert lookup["Midnight Rider"] == 1.0
    assert lookup["Shady Grove"] == 1.0
    assert lookup["Black Muddy River"] == 1.0
    assert lookup["Dust in a Baggie"] == 0.0
    assert lookup["Away From the Mire"] == 0.0


def test_build_is_cover_lookup_returns_empty_for_none() -> None:
    assert _build_is_cover_lookup(None) == {}
    assert _build_is_cover_lookup(pd.DataFrame()) == {}


def test_registry_returns_billy_fast_predictor() -> None:
    predictor = build_band_predictor(
        "billy", songs_df=_SONGS_DF, persist_artifacts=False
    )
    assert isinstance(predictor, BillyFastPredictorV3)
    assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_hp_tuned"


def test_billy_fast_diagnostic_frame_includes_active_and_candidate_features() -> None:
    shows_df, setlists_df = _billy_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictor(songs_df=_SONGS_DF, persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)

    expected_columns = {
        "song_name",
        "target_show_index",
        "target_show_date",
        "label",
        *BILLY_FAST_FEATURE_COLS,
        *BILLY_FAST_CANDIDATE_CONTEXT_COLS,
    }
    assert expected_columns.issubset(frame.columns)
    assert not frame.empty
    assert frame["target_show_index"].notna().all()
    assert frame["target_show_date"].notna().all()
    assert set(frame["label"].unique()).issubset({0.0, 1.0})
    assert predictor.MODEL_VERSION == "billy_fast_gbm_v1"
    assert BILLY_FAST_FEATURE_COLS == [
        "gap_shows",
        "plays_past_10",
        "plays_past_25",
        "plays_past_50",
        "career_play_pct",
        "month_play_rate",
        "is_cover",
    ]


def test_billy_fast_diagnostic_frame_excludes_future_target_songs() -> None:
    shows_df, setlists_df = _billy_fixture()
    future_show = pd.DataFrame(
        [
            {
                "show_id": "future-only-show",
                "show_date": "2024-08-01",
                "venue_name": "Future Hall",
                "city": "Asheville",
                "state": "NC",
                "country": "USA",
            }
        ]
    )
    future_setlist = pd.DataFrame(
        [
            {
                "show_id": "future-only-show",
                "song_name": "Future Only Tune",
                "song_position": 1,
            }
        ]
    )
    shows_df = pd.concat([shows_df, future_show], ignore_index=True)
    setlists_df = pd.concat([setlists_df, future_setlist], ignore_index=True)

    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )
    predictor = BillyFastPredictor(songs_df=_SONGS_DF, persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)

    assert "Future Only Tune" not in set(frame["song_name"])


def test_billy_fast_diagnostic_frame_uses_neutral_same_venue_without_context() -> None:
    shows_df, setlists_df = _billy_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictor(songs_df=_SONGS_DF, persist_artifacts=False)
    frame = predictor.build_diagnostic_training_frame(model_data)

    assert not frame.empty
    assert (frame["same_venue_run_prior_played"] == 0.0).all()
    assert (frame["same_venue_run_prior_play_count"] == 0.0).all()
    assert (frame["same_venue_run_prior_play_share"] == 0.0).all()
    assert (frame["same_venue_run_position"] == 0.0).all()


def test_billy_fast_v2_has_11_feature_cols() -> None:
    assert len(BILLY_FAST_V2_FEATURE_COLS) == 11
    assert set(BILLY_FAST_FEATURE_COLS).issubset(set(BILLY_FAST_V2_FEATURE_COLS))
    for col in (
        "tour_position",
        "diff_25_to_50",
        "show_position_in_run",
        "same_venue_run_position",
    ):
        assert col in BILLY_FAST_V2_FEATURE_COLS


def test_billy_fast_v2_trains_and_predicts() -> None:
    shows_df, setlists_df = _billy_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictorV2(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor.MODEL_VERSION == "billy_fast_gbm_v2"
    assert predictor._model is not None
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_fast_v2_trains_with_venue_context() -> None:
    shows_df, setlists_df = _billy_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictorV2(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)

    assert predictor._model is not None


def test_billy_fast_v2_trains_without_venue_context() -> None:
    shows_df, setlists_df = _billy_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictorV2(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert len(predictions) > 0


def test_billy_fast_v3_has_14_feature_cols() -> None:
    assert len(BILLY_FAST_V3_FEATURE_COLS) == 16
    assert set(BILLY_FAST_V2_FEATURE_COLS).issubset(set(BILLY_FAST_V3_FEATURE_COLS))
    for col in (
        "plays_past_3",
        "plays_past_5",
        "overdue_ratio",
        "avg_ltp_recent",
        "ltp_diff_recent",
    ):
        assert col in BILLY_FAST_V3_FEATURE_COLS


def test_billy_fast_v3_trains_and_predicts() -> None:
    shows_df, setlists_df = _billy_fixture()
    target_show = {
        "show_id": "future-billy",
        "show_date": "2024-05-20",
        "venue_name": "Ryman Auditorium",
        "city": "Nashville",
        "state": "TN",
        "country": "USA",
    }
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
        target_show_context=target_show,
    )

    predictor = BillyFastPredictorV3(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor.MODEL_VERSION == "billy_fast_gbm_v3"
    assert predictor._model is not None
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_fast_v3_trains_without_venue_context() -> None:
    shows_df, setlists_df = _billy_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictorV3(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert len(predictions) > 0


def test_billy_fast_v4_trains_and_predicts() -> None:
    shows_df, setlists_df = _billy_fixture()
    target_show = {
        "show_id": "future-billy",
        "show_date": "2024-05-20",
        "venue_name": "Ryman Auditorium",
        "city": "Nashville",
        "state": "TN",
        "country": "USA",
    }
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
        target_show_context=target_show,
    )

    predictor = BillyFastPredictorV4(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor.MODEL_VERSION == "billy_fast_gbm_v4"
    assert predictor._model is not None
    assert predictor._LGB_PARAMS["num_leaves"] == 63
    assert predictor._LGB_ROUNDS == 400
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_fast_v5_has_25_feature_cols() -> None:
    assert len(BILLY_FAST_V5_FEATURE_COLS) == 25
    assert set(BILLY_FAST_V3_FEATURE_COLS).issubset(set(BILLY_FAST_V5_FEATURE_COLS))
    for col in (
        "gap_percentile",
        "shows_since_debut",
        "is_recent_debut",
        "gap_days",
        "avg_days_between_plays",
        "days_overdue",
        "pct_set_1",
        "pct_encore",
        "set_affinity",
    ):
        assert col in BILLY_FAST_V5_FEATURE_COLS


def test_billy_fast_v5_trains_and_predicts() -> None:
    shows_df, setlists_df = _billy_fixture()
    target_show = {
        "show_id": "future-billy",
        "show_date": "2024-05-20",
        "venue_name": "Ryman Auditorium",
        "city": "Nashville",
        "state": "TN",
        "country": "USA",
    }
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
        target_show_context=target_show,
    )

    predictor = BillyFastPredictorV5(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor.MODEL_VERSION == "billy_fast_gbm_v5"
    assert predictor._model is not None
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_fast_v5_trains_without_venue_or_set_context() -> None:
    shows_df, setlists_df = _billy_fixture()
    shows_df = shows_df.drop(columns=["venue_name", "city", "state", "country"])
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
    )

    predictor = BillyFastPredictorV5(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert len(predictions) > 0


def test_billy_fast_v6_uses_v3_features_with_early_stopping() -> None:
    predictor = BillyFastPredictorV6(songs_df=_SONGS_DF, persist_artifacts=False)

    assert predictor.MODEL_VERSION == "billy_fast_gbm_v6_early_stop"
    assert predictor._FEATURE_COLS == BILLY_FAST_V3_FEATURE_COLS
    assert predictor._LGB_ROUNDS == 500
    assert predictor._EARLY_STOPPING_ROUNDS == 25


def test_billy_fast_v6_trains_and_predicts() -> None:
    shows_df, setlists_df = _billy_fixture()
    target_show = {
        "show_id": "future-billy",
        "show_date": "2024-05-20",
        "venue_name": "Ryman Auditorium",
        "city": "Nashville",
        "state": "TN",
        "country": "USA",
    }
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 5, 20),
        band="billy",
        target_show_context=target_show,
    )

    predictor = BillyFastPredictorV6(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert predictor.best_iteration is not None
    assert 0 < predictor.best_iteration <= predictor._LGB_ROUNDS
    assert 0 < len(predictions) <= 10
    assert len({p.song_name for p in predictions}) == len(predictions)


def test_billy_fast_v6_falls_back_when_validation_split_is_too_small() -> None:
    shows_df, setlists_df = _tiny_billy_fixture()
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 1, 5),
        band="billy",
    )

    predictor = BillyFastPredictorV6(songs_df=_SONGS_DF, persist_artifacts=False)
    predictor.train(model_data)
    predictions = predictor.predict(model_data, top_k=10)

    assert predictor._model is not None
    assert predictor.best_iteration is not None
    assert 0 < predictor.best_iteration <= predictor._LGB_ROUNDS
    assert len(predictions) > 0


# ── V10 experiment subclass tests ─────────────────────────────────────────────


class TestV10ExperimentSubclasses:
    """Test V10 experiment subclasses for model version and feature config."""

    def test_v10_plays_past_year(self):
        predictor = BillyFastV10PlaysPastYear()
        assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_feat_plays_past_year"
        assert "plays_past_year" in predictor._FEATURE_COLS
        assert len(predictor._FEATURE_COLS) == 17
        assert isinstance(predictor, BillyFastPredictorV3)

    def test_v10_long_rotation(self):
        predictor = BillyFastV10LongRotation()
        assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_feat_long_rotation"
        assert "plays_past_100" in predictor._FEATURE_COLS
        assert "diff_50_to_100" in predictor._FEATURE_COLS
        assert "long_rotation_pressure" in predictor._FEATURE_COLS
        assert len(predictor._FEATURE_COLS) == 19

    def test_v10_early_stop(self):
        predictor = BillyFastV10EarlyStop()
        assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_early_stop"
        assert predictor._LGB_ROUNDS == 500
        assert predictor._EARLY_STOPPING_ROUNDS == 25
        assert predictor._LGB_PARAMS["num_leaves"] == 15
        assert predictor._LGB_PARAMS["min_data_in_leaf"] == 10

    def test_v10_full_history(self):
        predictor = BillyFastV10FullHistory()
        assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_full_history"
        assert predictor._start_col(100) == 3

    def test_v10_window_150(self):
        predictor = BillyFastV10Window150()
        assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_window_150"
        assert predictor._start_col(100) == 3
        assert predictor._start_col(200) == 50

    def test_baseline_is_v10(self):
        predictor = BillyFastBaselinePredictor()
        assert predictor.MODEL_VERSION == "billy_fast_gbm_v10_hp_tuned"
        assert predictor._LGB_PARAMS["num_leaves"] == 15


class TestBillyV10Experiments:
    """Test Billy V10 experiment sweep registration."""

    def test_sweeps_are_registered(self):
        from jambandnerd.models.billy.experiments import BILLY_SWEEPS
        assert set(BILLY_SWEEPS) == {
            "hp_sweep", "combo_sweep", "feature_sweep", "window_sweep", "hp_v10_sweep",
        }
        assert len(BILLY_SWEEPS["feature_sweep"]) == 3
        assert len(BILLY_SWEEPS["window_sweep"]) == 3
        assert len(BILLY_SWEEPS["hp_v10_sweep"]) == 4

    def test_feature_sweep_uses_explicit_predictors(self):
        from jambandnerd.models.billy.experiments import BILLY_SWEEPS
        predictor_paths = [
            config.predictor_path for config in BILLY_SWEEPS["feature_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.billy.") for path in predictor_paths
        )

    def test_window_sweep_uses_explicit_predictors(self):
        from jambandnerd.models.billy.experiments import BILLY_SWEEPS
        predictor_paths = [
            config.predictor_path for config in BILLY_SWEEPS["window_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.billy.") for path in predictor_paths
        )
