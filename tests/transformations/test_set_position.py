"""Tests for band-agnostic set-position feature engineering."""

from __future__ import annotations

import pandas as pd
import pytest

from jambandnerd.transformations.set_position import (
    SET_POSITION_FEATURES,
    compute_set_position_features,
)


def _make_plays(
    *,
    include_position: bool = True,
) -> pd.DataFrame:
    rows = [
        {
            "show_index": 1,
            "song_name": "Arrow",
            "set_number": 1,
            "song_position": 1,
            "encore": False,
        },
        {
            "show_index": 1,
            "song_name": "Thatch",
            "set_number": 1,
            "song_position": 5,
            "encore": False,
        },
        {
            "show_index": 1,
            "song_name": "Synrise",
            "set_number": 2,
            "song_position": 1,
            "encore": False,
        },
        {
            "show_index": 1,
            "song_name": "Empress",
            "set_number": 2,
            "song_position": 4,
            "encore": False,
        },
        {
            "show_index": 2,
            "song_name": "Arrow",
            "set_number": 1,
            "song_position": 3,
            "encore": False,
        },
        {
            "show_index": 2,
            "song_name": "Thatch",
            "set_number": 2,
            "song_position": 2,
            "encore": False,
        },
        {
            "show_index": 2,
            "song_name": "Empress",
            "set_number": 2,
            "song_position": 1,
            "encore": True,
        },
        {
            "show_index": 2,
            "song_name": "Stereo",
            "set_number": 1,
            "song_position": 2,
            "encore": False,
        },
        {
            "show_index": 3,
            "song_name": "Arrow",
            "set_number": 1,
            "song_position": 1,
            "encore": False,
        },
        {
            "show_index": 3,
            "song_name": "Stereo",
            "set_number": 2,
            "song_position": 3,
            "encore": False,
        },
    ]
    df = pd.DataFrame(rows)
    if not include_position:
        df = df.drop(columns=["set_number", "song_position", "encore"])
    return df


class TestComputeSetPositionFeatures:

    def test_returns_all_feature_columns(self) -> None:
        result = compute_set_position_features(_make_plays())
        assert "song_name" in result.columns
        for col in SET_POSITION_FEATURES:
            assert col in result.columns

    def test_empty_plays_returns_empty_dataframe(self) -> None:
        result = compute_set_position_features(pd.DataFrame())
        assert result.empty
        assert "song_name" in result.columns
        for col in SET_POSITION_FEATURES:
            assert col in result.columns

    def test_missing_position_columns_defaults_to_zero(self) -> None:
        plays = _make_plays(include_position=False)
        result = compute_set_position_features(plays)
        assert not result.empty
        for col in SET_POSITION_FEATURES:
            assert (result[col] == 0.0).all()

    def test_pct_set_1_counts_correctly(self) -> None:
        result = compute_set_position_features(_make_plays())
        row = result[result["song_name"] == "Arrow"].iloc[0]
        assert row["pct_set_1"] == pytest.approx(1.0)
        assert row["pct_set_2"] == pytest.approx(0.0)

    def test_pct_encore_counts_correctly(self) -> None:
        result = compute_set_position_features(_make_plays())
        row = result[result["song_name"] == "Empress"].iloc[0]
        assert row["pct_encore"] == pytest.approx(0.5)

    def test_set_affinity_is_zero_when_no_set_data(self) -> None:
        result = compute_set_position_features(_make_plays(include_position=False))
        assert (result["set_affinity"] == 0.0).all()

    def test_set_affinity_favors_set_2(self) -> None:
        result = compute_set_position_features(_make_plays())
        empress = result[result["song_name"] == "Empress"].iloc[0]
        assert empress["set_affinity"] > 0.5

    def test_position_consistency_is_low_for_fixed_slot_songs(self) -> None:
        result = compute_set_position_features(_make_plays())
        arrow = result[result["song_name"] == "Arrow"].iloc[0]
        assert arrow["position_consistency"] < 0.5

    def test_no_duplicate_song_names(self) -> None:
        result = compute_set_position_features(_make_plays())
        assert result["song_name"].is_unique

    def test_all_songs_present(self) -> None:
        plays = _make_plays()
        result = compute_set_position_features(plays)
        expected_songs = set(plays["song_name"].unique())
        assert set(result["song_name"].unique()) == expected_songs
