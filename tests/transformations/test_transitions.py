"""Tests for the directional within-set bigram transition matrix."""

from __future__ import annotations

import pandas as pd
import pytest

from jambandnerd.transformations.transitions import TransitionMatrix


def _setlists_df(rows):
    return pd.DataFrame(
        rows, columns=["show_id", "set_number", "song_position", "song_name"]
    )


def test_basic_bigram_counting() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s1", 1, 3, "C"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.get_probability("A", "B") == pytest.approx(1.0)
    assert matrix.get_probability("B", "C") == pytest.approx(1.0)
    assert matrix.get_probability("A", "C") is None


def test_conditional_probability_with_multiple_occurrences() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s2", 1, 1, "A"),
            ("s2", 1, 2, "C"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.get_probability("A", "B") == pytest.approx(0.5)
    assert matrix.get_probability("A", "C") == pytest.approx(0.5)


def test_no_cross_set_transitions() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s1", 2, 1, "C"),
            ("s1", 2, 2, "D"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.get_probability("B", "C") is None
    assert matrix.get_probability("A", "B") == pytest.approx(1.0)
    assert matrix.get_probability("C", "D") == pytest.approx(1.0)


def test_no_cross_show_transitions() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s2", 1, 1, "C"),
            ("s2", 1, 2, "D"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.get_probability("B", "C") is None


def test_unseen_pair_returns_none() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.get_probability("Z", "A") is None
    assert matrix.get_probability("A", "Z") is None


def test_single_song_set_produces_no_transitions() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.n_pairs == 0


def test_get_top_transitions() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s2", 1, 1, "A"),
            ("s2", 1, 2, "B"),
            ("s3", 1, 1, "A"),
            ("s3", 1, 2, "C"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    top = matrix.get_top_transitions("A", n=5)
    assert len(top) == 2
    assert top[0][0] == "B"
    assert top[0][1] == pytest.approx(2 / 3)
    assert top[1][0] == "C"
    assert top[1][1] == pytest.approx(1 / 3)


def test_missing_columns_raises() -> None:
    df = pd.DataFrame({"show_id": ["s1"], "song_name": ["A"]})
    with pytest.raises(ValueError, match="missing required columns"):
        TransitionMatrix().build(df)


def test_n_pairs_counts_unique_transitions() -> None:
    df = _setlists_df(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s2", 1, 1, "A"),
            ("s2", 1, 2, "B"),
        ]
    )
    matrix = TransitionMatrix().build(df)
    assert matrix.n_pairs == 1
