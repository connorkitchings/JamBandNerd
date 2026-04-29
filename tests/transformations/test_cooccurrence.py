"""Tests for band-agnostic co-occurrence feature engineering."""

from __future__ import annotations

import pandas as pd
import pytest

from jambandnerd.transformations.cooccurrence import (
    COOCCURRENCE_FEATURES,
    build_cooccurrence_matrix,
    compute_cooccurrence_features,
)


def _make_plays() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"show_index": 1, "song_name": "Arrow"},
            {"show_index": 1, "song_name": "Thatch"},
            {"show_index": 1, "song_name": "Synrise"},
            {"show_index": 2, "song_name": "Arrow"},
            {"show_index": 2, "song_name": "Thatch"},
            {"show_index": 2, "song_name": "Empress"},
            {"show_index": 3, "song_name": "Arrow"},
            {"show_index": 3, "song_name": "Stereo"},
            {"show_index": 3, "song_name": "Synrise"},
        ]
    )


def _make_era_plays() -> pd.DataFrame:
    """Plays spanning old and new eras: Thatch dropped, Stereo added."""
    return pd.DataFrame(
        [
            {"show_index": 1, "song_name": "Arrow"},
            {"show_index": 1, "song_name": "Thatch"},
            {"show_index": 2, "song_name": "Arrow"},
            {"show_index": 2, "song_name": "Thatch"},
            {"show_index": 3, "song_name": "Arrow"},
            {"show_index": 3, "song_name": "Thatch"},
            {"show_index": 100, "song_name": "Arrow"},
            {"show_index": 100, "song_name": "Stereo"},
            {"show_index": 101, "song_name": "Arrow"},
            {"show_index": 101, "song_name": "Stereo"},
            {"show_index": 102, "song_name": "Arrow"},
            {"show_index": 102, "song_name": "Stereo"},
        ]
    )


class TestBuildCooccurrenceMatrix:

    def test_empty_plays_returns_empty(self) -> None:
        assert build_cooccurrence_matrix(pd.DataFrame()) == {}

    def test_strong_pair_has_high_cooccurrence(self) -> None:
        matrix = build_cooccurrence_matrix(_make_plays(), decay_shows=float("inf"))
        assert matrix[("Arrow", "Thatch")] == pytest.approx(2 / 3)
        assert matrix[("Thatch", "Arrow")] == pytest.approx(2 / 2)

    def test_self_cooccurrence_is_always_one(self) -> None:
        matrix = build_cooccurrence_matrix(_make_plays())
        assert matrix[("Arrow", "Arrow")] == pytest.approx(1.0)

    def test_non_cooccurring_pair_is_zero(self) -> None:
        matrix = build_cooccurrence_matrix(_make_plays())
        assert matrix.get(("Stereo", "Thatch"), 0.0) == pytest.approx(0.0)
        assert matrix.get(("Thatch", "Stereo"), 0.0) == pytest.approx(0.0)

    def test_matrix_is_symmetric_for_direction(self) -> None:
        matrix = build_cooccurrence_matrix(_make_plays())
        assert ("Arrow", "Synrise") in matrix
        assert ("Synrise", "Arrow") in matrix
        assert matrix[("Arrow", "Synrise")] != matrix[("Synrise", "Arrow")]

    def test_decay_downweights_old_shows(self) -> None:
        matrix = build_cooccurrence_matrix(_make_era_plays(), decay_shows=20.0)
        arrow_stereo = matrix[("Arrow", "Stereo")]
        arrow_thatch = matrix[("Arrow", "Thatch")]
        assert arrow_stereo > arrow_thatch

    def test_infinite_decay_equals_uniform(self) -> None:
        matrix = build_cooccurrence_matrix(_make_era_plays(), decay_shows=float("inf"))
        arrow_stereo = matrix[("Arrow", "Stereo")]
        arrow_thatch = matrix[("Arrow", "Thatch")]
        assert arrow_stereo == pytest.approx(arrow_thatch)

    def test_very_small_decay_ignores_old_shows(self) -> None:
        matrix = build_cooccurrence_matrix(_make_era_plays(), decay_shows=1.0)
        arrow_thatch = matrix[("Arrow", "Thatch")]
        assert arrow_thatch == pytest.approx(0.0)


class TestComputeCooccurrenceFeatures:

    def test_returns_all_feature_columns(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Arrow"],
        )
        assert "song_name" in result.columns
        for col in COOCCURRENCE_FEATURES:
            assert col in result.columns

    def test_empty_plays_returns_zero_features(self) -> None:
        result = compute_cooccurrence_features(
            pd.DataFrame(),
            recently_played_songs=["Arrow"],
        )
        assert result.empty

    def test_no_recent_songs_returns_zero_features(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=[],
        )
        for col in COOCCURRENCE_FEATURES:
            assert (result[col] == 0.0).all()

    def test_strong_pair_has_high_avg_cooccurrence(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Arrow"],
            candidate_song_names=["Thatch"],
        )
        thatch = result[result["song_name"] == "Thatch"].iloc[0]
        assert thatch["avg_cooccurrence_with_recent"] == pytest.approx(1.0)

    def test_n_strong_pairs_counts_correctly(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Arrow"],
            candidate_song_names=["Thatch", "Stereo"],
        )
        thatch = result[result["song_name"] == "Thatch"].iloc[0]
        stereo = result[result["song_name"] == "Stereo"].iloc[0]
        assert thatch["n_strong_pairs_recent"] == pytest.approx(1.0)
        assert stereo["n_strong_pairs_recent"] == pytest.approx(1.0)

    def test_pair_affinity_rank_orders_correctly(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Arrow"],
            candidate_song_names=["Thatch", "Stereo"],
        )
        thatch = result[result["song_name"] == "Thatch"].iloc[0]
        stereo = result[result["song_name"] == "Stereo"].iloc[0]
        assert thatch["pair_affinity_rank"] <= stereo["pair_affinity_rank"]

    def test_cooccurrence_with_last_played(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Thatch", "Arrow"],
            candidate_song_names=["Empress"],
        )
        empress = result[result["song_name"] == "Empress"].iloc[0]
        assert empress["cooccurrence_with_last_played"] == pytest.approx(1.0)

    def test_candidate_song_names_limits_output(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Arrow"],
            candidate_song_names=["Thatch"],
        )
        assert set(result["song_name"]) == {"Thatch"}

    def test_song_excluded_from_own_cooccurrence(self) -> None:
        result = compute_cooccurrence_features(
            _make_plays(),
            recently_played_songs=["Arrow"],
            candidate_song_names=["Arrow"],
        )
        arrow = result[result["song_name"] == "Arrow"].iloc[0]
        assert arrow["avg_cooccurrence_with_recent"] == 0.0
        assert arrow["cooccurrence_with_last_played"] == 0.0

    def test_decay_propagated_to_features(self) -> None:
        plays = pd.DataFrame(
            [
                {"show_index": 1, "song_name": "OldPair"},
                {"show_index": 1, "song_name": "Anchor"},
                {"show_index": 1, "song_name": "X"},
                {"show_index": 2, "song_name": "OldPair"},
                {"show_index": 2, "song_name": "Anchor"},
                {"show_index": 100, "song_name": "NewPair"},
                {"show_index": 100, "song_name": "Anchor"},
                {"show_index": 101, "song_name": "NewPair"},
                {"show_index": 101, "song_name": "Anchor"},
                {"show_index": 101, "song_name": "X"},
            ]
        )
        matrix = build_cooccurrence_matrix(plays, decay_shows=20.0)
        x_with_new = matrix[("X", "NewPair")]
        x_with_old = matrix[("X", "OldPair")]
        assert x_with_new > x_with_old

    def test_default_decay_shows_is_80(self) -> None:
        era = _make_era_plays()
        matrix_default = build_cooccurrence_matrix(era)
        matrix_80 = build_cooccurrence_matrix(era, decay_shows=80.0)
        assert matrix_default[("Arrow", "Stereo")] == pytest.approx(
            matrix_80[("Arrow", "Stereo")]
        )
