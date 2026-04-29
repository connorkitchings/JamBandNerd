"""Band-agnostic song co-occurrence feature engineering.

Computes per-song affinity features from a recency-weighted song×song
co-occurrence matrix derived from historical plays.  Co-occurrence captures
patterns like "song A and song B tend to appear in the same show" which are
invisible to per-song gap/frequency features.

The matrix applies exponential decay by ``show_index`` so that recent shows
contribute more strongly than old ones.  This is critical for bands like
Goose whose repertoire has evolved significantly over time — a co-occurrence
pattern from 2016 is far less predictive than one from last month.

All aggregations operate strictly on plays before the prediction
``reference_date``.  When there is insufficient history the features default
to 0.0.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

COOCCURRENCE_FEATURES: list[str] = [
    "avg_cooccurrence_with_recent",
    "max_cooccurrence_with_recent",
    "n_strong_pairs_recent",
    "cooccurrence_with_last_played",
    "pair_affinity_rank",
]

_DEFAULT_DECAY_SHOWS: float = 80.0


def build_cooccurrence_matrix(
    historical_plays: pd.DataFrame,
    *,
    decay_shows: float = _DEFAULT_DECAY_SHOWS,
) -> dict[tuple[str, str], float]:
    """Build a recency-weighted co-occurrence matrix from historical plays.

    Each show's contribution is weighted by ``exp(-(max_index - show_index) /
    decay_shows)``.  With the default ``decay_shows=80``, a show 80 shows ago
    contributes ~37% of the weight of the most recent show; a show 200 shows
    ago contributes ~8%.

    Parameters
    ----------
    historical_plays
        DataFrame with ``song_name`` and ``show_index`` columns.
    decay_shows
        Exponential decay half-life in shows.  Lower values weight recent
        shows more aggressively.  Set to ``float("inf")`` for uniform
        (unweighted) co-occurrence.

    Returns
    -------
    dict mapping ``(song_a, song_b)`` → weighted co-occurrence ratio.
    The forward direction ``(song_a, song_b)`` is the weighted fraction of
    song_a's presence that overlaps with song_b.
    """
    if historical_plays.empty:
        return {}

    plays = historical_plays.copy()
    if "show_index" not in plays.columns:
        return {}

    max_index = int(plays["show_index"].max())

    show_weights: dict[int, float] = {}
    for idx in plays["show_index"].dropna().astype(int).unique():
        if decay_shows == float("inf"):
            show_weights[idx] = 1.0
        else:
            show_weights[idx] = math.exp(-(max_index - idx) / decay_shows)

    songs_in_show: dict[int, set[str]] = {}
    for show_index, group in plays.groupby("show_index"):
        songs_in_show[int(show_index)] = set(group["song_name"].astype(str).unique())

    weighted_presence: dict[str, float] = {}
    all_songs: set[str] = set()
    for songs in songs_in_show.values():
        all_songs.update(songs)

    for song in all_songs:
        wp = 0.0
        for show_idx, songs in songs_in_show.items():
            if song in songs:
                wp += show_weights.get(show_idx, 0.0)
        weighted_presence[song] = wp

    sorted_songs = sorted(all_songs)
    matrix: dict[tuple[str, str], float] = {}
    for i, song_a in enumerate(sorted_songs):
        for song_b in sorted_songs[i:]:
            overlap = 0.0
            for show_idx, songs in songs_in_show.items():
                if song_a in songs and song_b in songs:
                    overlap += show_weights.get(show_idx, 0.0)

            wa = weighted_presence.get(song_a, 0.0)
            wb = weighted_presence.get(song_b, 0.0)
            key = (song_a, song_b)
            matrix_val = overlap / wa if wa > 0 else 0.0
            matrix[key] = matrix_val
            if song_a != song_b:
                reverse_key = (song_b, song_a)
                matrix[reverse_key] = overlap / wb if wb > 0 else 0.0

    return matrix


def _lookup(matrix: dict[tuple[str, str], float], a: str, b: str) -> float:
    return matrix.get((a, b), 0.0)


def compute_cooccurrence_features(
    historical_plays: pd.DataFrame,
    *,
    recently_played_songs: list[str],
    candidate_song_names: list[str] | None = None,
    decay_shows: float = _DEFAULT_DECAY_SHOWS,
) -> pd.DataFrame:
    """Compute per-song co-occurrence features.

    Parameters
    ----------
    historical_plays
        Pre-filtered plays (already before reference_date).
    recently_played_songs
        Songs played in the exclusion window — the set of songs whose
        affinity with each candidate is measured.
    candidate_song_names
        Optional subset of songs to compute features for.  When ``None``,
        features are computed for all songs in *historical_plays*.
    decay_shows
        Exponential decay half-life in shows for the co-occurrence matrix.
        Passed through to :func:`build_cooccurrence_matrix`.

    Returns
    -------
    pd.DataFrame
        Columns ``["song_name", *COOCCURRENCE_FEATURES]``.
    """
    empty = pd.DataFrame(columns=["song_name"] + COOCCURRENCE_FEATURES)

    if historical_plays.empty or not recently_played_songs:
        if candidate_song_names:
            empty["song_name"] = candidate_song_names
        elif not historical_plays.empty:
            empty["song_name"] = sorted(historical_plays["song_name"].unique())
        for col in COOCCURRENCE_FEATURES:
            empty[col] = 0.0
        return empty

    matrix = build_cooccurrence_matrix(historical_plays, decay_shows=decay_shows)
    if not matrix:
        if candidate_song_names:
            empty["song_name"] = candidate_song_names
        else:
            empty["song_name"] = sorted(
                historical_plays["song_name"].astype(str).unique()
            )
        for col in COOCCURRENCE_FEATURES:
            empty[col] = 0.0
        return empty

    recent_set = set(recently_played_songs)
    last_played = recently_played_songs[-1] if recently_played_songs else None

    all_songs: list[str]
    if candidate_song_names is not None:
        all_songs = list(candidate_song_names)
    else:
        all_songs = sorted(historical_plays["song_name"].astype(str).unique())

    affinity_scores: dict[str, float] = {}
    records: list[dict[str, Any]] = []
    for song in all_songs:
        co_values = [_lookup(matrix, song, r) for r in recent_set if r != song]
        if not co_values:
            co_values = [0.0]

        avg_co = float(np.mean(co_values))
        max_co = float(np.max(co_values))
        n_strong = sum(1 for v in co_values if v > 0.5)
        last_co = (
            _lookup(matrix, song, last_played)
            if last_played and last_played != song
            else 0.0
        )

        affinity_scores[song] = avg_co
        records.append(
            {
                "song_name": song,
                "avg_cooccurrence_with_recent": avg_co,
                "max_cooccurrence_with_recent": max_co,
                "n_strong_pairs_recent": float(n_strong),
                "cooccurrence_with_last_played": last_co,
                "pair_affinity_rank": 0.0,
            }
        )

    if records:
        sorted_songs = sorted(affinity_scores, key=affinity_scores.get, reverse=True)
        rank_map = {song: float(rank) for rank, song in enumerate(sorted_songs)}
        for rec in records:
            rec["pair_affinity_rank"] = rank_map.get(rec["song_name"], 0.0)

    return pd.DataFrame(records)
