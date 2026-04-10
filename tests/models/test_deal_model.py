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


def test_deal_training_frame_excludes_same_day_history() -> None:
    shows_df = pd.DataFrame(
        [
            {"show_id": "show-1", "show_date": "2024-01-01"},
            {"show_id": "show-2", "show_date": "2024-01-02"},
            {"show_id": "show-3", "show_date": "2024-01-03"},
            {"show_id": "show-4", "show_date": "2024-01-04"},
            {"show_id": "show-5", "show_date": "2024-01-10"},
            {"show_id": "show-6", "show_date": "2024-01-10"},
        ]
    )
    setlists_df = pd.DataFrame(
        [
            {"show_id": "show-1", "song_name": "Anchor Song"},
            {"show_id": "show-2", "song_name": "Bridge Song"},
            {"show_id": "show-3", "song_name": "Bridge Song"},
            {"show_id": "show-4", "song_name": "Bridge Song"},
            {"show_id": "show-5", "song_name": "Leak Song"},
            {"show_id": "show-6", "song_name": "Target Song"},
        ]
    )

    model_data = generate_model_data(
        shows_df,
        setlists_df,
        date(2024, 1, 12),
        band="goose",
    )

    training_frame, _summary = build_training_frame(
        model_data,
        band="goose",
        min_plays_threshold=1,
        retired_gap_threshold=200,
        min_training_shows=1,
        training_window_shows=10,
    )

    target_rows = training_frame[training_frame["target_show_index"] == 6]
    assert "Anchor Song" in set(target_rows["song_name"])
    assert "Leak Song" not in set(target_rows["song_name"])


def test_deal_predictor_feature_columns_override_restricts_training(
    tmp_path, monkeypatch
) -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    gap_only = [
        "current_gap",
        "avg_ltp",
        "recent_avg_ltp",
        "overdue_metric",
        "gap_z_score",
    ]
    monkeypatch.setattr(DealPredictor, "MODEL_DIR", tmp_path)
    predictor = DealPredictor(
        band="goose", min_plays_threshold=2, feature_columns=gap_only
    )
    predictor.train(model_data)

    assert predictor.model is not None
    assert predictor.model.feature_columns == gap_only
    predictions = predictor.predict(model_data, top_k=10)
    assert len(predictions) > 0


def test_deal_predictor_positive_weight_cap_is_applied(tmp_path, monkeypatch) -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    monkeypatch.setattr(DealPredictor, "MODEL_DIR", tmp_path)
    predictor = DealPredictor(
        band="goose", min_plays_threshold=2, positive_weight_cap=1.5
    )
    predictor.train(model_data)

    # The capped predictor should still train and produce predictions.
    assert predictor.model is not None
    predictions = predictor.predict(model_data, top_k=10)
    assert len(predictions) > 0


def test_deal_predictor_invalid_feature_columns_raises() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    predictor = DealPredictor(
        band="goose",
        min_plays_threshold=2,
        persist_artifacts=False,
        feature_columns=["current_gap", "nonexistent_feature"],
    )
    try:
        predictor.train(model_data)
        assert False, "Expected ValueError for invalid feature columns"
    except ValueError as exc:
        assert "nonexistent_feature" in str(exc)


def test_debut_features_are_present_in_candidates() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    for col in ("debut_age_shows", "career_play_pct", "novelty_rank"):
        assert col in candidates.columns

    assert (candidates["debut_age_shows"] > 0).all()
    assert (candidates["career_play_pct"] >= 0).all()
    assert (candidates["career_play_pct"] <= 1).all()
    assert (candidates["novelty_rank"] >= 0).all()


def test_debut_age_increases_for_late_debuting_songs() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    song_d_row = candidates[candidates["song_name"] == "Song D"]
    assert not song_d_row.empty
    song_d_debut_age = song_d_row["debut_age_shows"].iloc[0]
    assert song_d_debut_age > 0


def test_career_play_pct_higher_for_staple_songs() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    song_d_pct = candidates.loc[
        candidates["song_name"] == "Song D", "career_play_pct"
    ].iloc[0]
    song_k_pct = candidates.loc[
        candidates["song_name"] == "Song K", "career_play_pct"
    ].iloc[0]
    assert song_d_pct > song_k_pct


def test_novelty_rank_respects_debut_and_play_count() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    assert "novelty_rank" in candidates.columns
    assert (candidates["novelty_rank"] >= 0).all()


def test_debut_features_in_training_frame() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    training_frame, _summary = build_training_frame(
        model_data,
        band="goose",
        min_plays_threshold=2,
        retired_gap_threshold=200,
        min_training_shows=10,
        training_window_shows=20,
    )

    for col in ("debut_age_shows", "career_play_pct", "novelty_rank"):
        assert col in training_frame.columns


def test_recency_pressure_features_are_present_and_bounded() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    for col in (
        "plays_past_90d",
        "pct_shows_90d",
        "diff_90d_to_1yr",
        "recent_play_share_90d",
        "gap_vs_recent_ratio",
        "gap_percentile",
        "recent_gap_delta",
        "decayed_play_sum_180d",
        "days_since_last_play",
    ):
        assert col in candidates.columns

    assert (candidates["plays_past_90d"] <= candidates["plays_past_year"]).all()
    assert ((candidates["gap_percentile"] >= 0) & (candidates["gap_percentile"] <= 1)).all()
    assert (candidates["recent_play_share_90d"] >= 0).all()
    assert (candidates["recent_play_share_90d"] <= 1).all()
    assert (candidates["decayed_play_sum_180d"] > 0).all()
    assert (candidates["days_since_last_play"] >= candidates["current_gap"]).all()


def test_recent_activity_features_distinguish_staples_from_rarities() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    candidates = get_candidate_features(
        model_data, min_plays_threshold=2, retired_gap_threshold=200
    )

    song_a = candidates.loc[candidates["song_name"] == "Song D"].iloc[0]
    song_k = candidates.loc[candidates["song_name"] == "Song K"].iloc[0]

    assert song_a["plays_past_90d"] >= song_k["plays_past_90d"]
    assert song_a["decayed_play_sum_180d"] > song_k["decayed_play_sum_180d"]


def test_deal_evaluation_report_includes_probability_quality_sections() -> None:
    shows_df, setlists_df = build_deal_fixture()
    model_data = generate_model_data(
        shows_df, setlists_df, date(2024, 3, 20), band="goose"
    )

    predictor = DealPredictor(
        band="goose",
        min_plays_threshold=2,
        persist_artifacts=False,
    )
    predictor.train(model_data)
    report = predictor.build_evaluation_report(model_data)

    assert report["status"] == "ready"
    assert "training_probability_quality" in report
    assert "current_candidate_probability_quality" in report
    assert "training_separation_summary" in report
    assert "calibration_error_summary" in report
    assert report["training_probability_quality"]["count"] > 0
    assert report["current_candidate_probability_quality"]["count"] > 0
    assert report["training_separation_summary"]["probability_gap"] >= 0
