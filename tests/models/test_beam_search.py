"""Tests for the beam search sequence optimizer."""

from __future__ import annotations

import pandas as pd

from jambandnerd.models.beam_search import beam_search
from jambandnerd.transformations.transitions import TransitionMatrix


def _simple_transition_matrix():
    df = pd.DataFrame(
        [
            ("s1", 1, 1, "A"),
            ("s1", 1, 2, "B"),
            ("s1", 1, 3, "C"),
            ("s2", 1, 1, "A"),
            ("s2", 1, 2, "B"),
            ("s2", 1, 3, "D"),
        ],
        columns=["show_id", "set_number", "song_position", "song_name"],
    )
    return TransitionMatrix().build(df)


def test_beam_search_returns_ranked_songs() -> None:
    probs = {"A": 0.9, "B": 0.8, "C": 0.7, "D": 0.6}
    tm = _simple_transition_matrix()
    result = beam_search(probs, tm, sequence_length=3, beam_width=3)
    assert len(result.ranked_songs) == 4
    assert result.ranked_songs[0] == "A"


def test_beam_search_no_repeats_in_path() -> None:
    probs = {"A": 0.9, "B": 0.8}
    tm = _simple_transition_matrix()
    result = beam_search(probs, tm, sequence_length=3, beam_width=2)
    for path in result.paths:
        assert len(path.songs) == len(set(path.songs))


def test_beam_search_uses_stage1_fallback_for_unseen_transitions() -> None:
    probs = {"X": 0.9, "Y": 0.8}
    tm = _simple_transition_matrix()
    result = beam_search(probs, tm, sequence_length=2, beam_width=2)
    assert len(result.ranked_songs) == 2


def test_beam_search_empty_probs() -> None:
    tm = _simple_transition_matrix()
    result = beam_search({}, tm, sequence_length=3)
    assert result.ranked_songs == []
    assert result.paths == []


def test_beam_search_beam_width_pruning() -> None:
    probs = {f"S{i}": 0.9 - i * 0.1 for i in range(10)}
    tm = _simple_transition_matrix()
    result = beam_search(probs, tm, sequence_length=3, beam_width=3)
    assert len(result.paths) <= 3


def test_beam_search_deterministic() -> None:
    probs = {"A": 0.9, "B": 0.8, "C": 0.7}
    tm = _simple_transition_matrix()
    r1 = beam_search(probs, tm, sequence_length=3, beam_width=3)
    r2 = beam_search(probs, tm, sequence_length=3, beam_width=3)
    assert r1.ranked_songs == r2.ranked_songs


def test_beam_search_max_aggregation() -> None:
    probs = {"A": 0.9, "B": 0.8, "C": 0.7}
    tm = _simple_transition_matrix()
    result = beam_search(probs, tm, sequence_length=3, beam_width=3)
    for song in result.song_scores:
        assert result.song_scores[song] >= 0.0


def test_candidate_songs_filters_to_subset() -> None:
    probs = {"A": 0.9, "B": 0.8, "C": 0.7, "D": 0.1}
    tm = _simple_transition_matrix()
    result = beam_search(
        probs, tm, sequence_length=3, beam_width=3, candidate_songs=["A", "B", "C"]
    )
    assert "D" not in result.ranked_songs
