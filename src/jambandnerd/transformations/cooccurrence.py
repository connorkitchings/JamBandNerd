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


def _build_cooccurrence_numpy(
    historical_plays: pd.DataFrame,
    *,
    decay_shows: float = _DEFAULT_DECAY_SHOWS,
) -> tuple[np.ndarray, np.ndarray, list[str], dict[str, int]] | None:
    if historical_plays.empty:
        return None
    if "show_index" not in historical_plays.columns:
        return None

    valid = historical_plays.dropna(subset=["show_index"])
    if valid.empty:
        return None

    max_index = int(valid["show_index"].max())

    unique_songs = sorted(valid["song_name"].astype(str).unique())
    song_to_idx = {s: i for i, s in enumerate(unique_songs)}
    n_songs = len(unique_songs)

    unique_shows = sorted(valid["show_index"].astype(int).unique())
    show_to_col = {idx: col for col, idx in enumerate(unique_shows)}
    n_shows = len(unique_shows)

    if decay_shows == float("inf"):
        weights = np.ones(n_shows, dtype=np.float64)
    else:
        weights = np.exp(
            -(max_index - np.array(unique_shows, dtype=np.float64)) / decay_shows
        )

    pairs = valid[["song_name", "show_index"]].drop_duplicates()
    s_idx = pairs["song_name"].astype(str).map(song_to_idx).values.astype(int)
    sh_idx = pairs["show_index"].astype(int).map(show_to_col).values.astype(int)

    presence = np.zeros((n_songs, n_shows), dtype=np.float64)
    presence[s_idx, sh_idx] = 1.0

    weighted_presence = presence @ weights
    weighted_P = presence * weights[np.newaxis, :]
    overlap = weighted_P @ presence.T

    safe_wp = np.where(weighted_presence > 0, weighted_presence, 1.0)
    normalized = overlap / safe_wp[:, np.newaxis]

    return normalized, weighted_presence, unique_songs, song_to_idx


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
    result = _build_cooccurrence_numpy(historical_plays, decay_shows=decay_shows)
    if result is None:
        return {}

    normalized, weighted_presence, unique_songs, _ = result
    n_songs = len(unique_songs)

    matrix: dict[tuple[str, str], float] = {}
    for i in range(n_songs):
        song_a = unique_songs[i]
        for j in range(n_songs):
            song_b = unique_songs[j]
            if weighted_presence[i] <= 0 and weighted_presence[j] <= 0:
                val = 0.0
            elif weighted_presence[i] <= 0:
                val = 0.0
            else:
                val = float(normalized[i, j])
            matrix[(song_a, song_b)] = val

    return matrix


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
    empty_cols = ["song_name"] + COOCCURRENCE_FEATURES

    if historical_plays.empty or not recently_played_songs:
        empty = pd.DataFrame(columns=empty_cols)
        if candidate_song_names:
            empty["song_name"] = candidate_song_names
        elif not historical_plays.empty:
            empty["song_name"] = sorted(historical_plays["song_name"].unique())
        for col in COOCCURRENCE_FEATURES:
            empty[col] = 0.0
        return empty

    all_songs: list[str]
    if candidate_song_names is not None:
        all_songs = list(candidate_song_names)
    else:
        all_songs = sorted(historical_plays["song_name"].astype(str).unique())

    result = _build_cooccurrence_numpy(historical_plays, decay_shows=decay_shows)
    if result is None:
        empty = pd.DataFrame(columns=empty_cols)
        empty["song_name"] = all_songs
        for col in COOCCURRENCE_FEATURES:
            empty[col] = 0.0
        return empty

    normalized, _, unique_songs, song_to_idx = result

    recent_set = set(recently_played_songs)
    last_played = recently_played_songs[-1] if recently_played_songs else None

    recent_in_matrix = [r for r in recent_set if r in song_to_idx]
    if not recent_in_matrix:
        empty = pd.DataFrame(columns=empty_cols)
        empty["song_name"] = all_songs
        for col in COOCCURRENCE_FEATURES:
            empty[col] = 0.0
        return empty

    recent_col_indices = np.array([song_to_idx[r] for r in recent_in_matrix], dtype=int)

    candidate_in_matrix = [s for s in all_songs if s in song_to_idx]
    candidate_not_in_matrix = [s for s in all_songs if s not in song_to_idx]

    records: list[dict[str, Any]] = []

    if candidate_in_matrix:
        cand_row_indices = np.array(
            [song_to_idx[s] for s in candidate_in_matrix], dtype=int
        )
        sub = normalized[np.ix_(cand_row_indices, recent_col_indices)]

        self_mask = cand_row_indices[:, np.newaxis] != recent_col_indices[np.newaxis, :]
        valid_count = self_mask.sum(axis=1).astype(float)
        valid_count = np.where(valid_count == 0, 1.0, valid_count)
        sub_zeroed = np.where(self_mask, sub, 0.0)

        avg_co_arr = sub_zeroed.sum(axis=1) / valid_count
        max_co_arr = np.where(self_mask, sub, -1.0).max(axis=1)
        max_co_arr = np.maximum(max_co_arr, 0.0)
        n_strong_arr = (sub_zeroed > 0.5).sum(axis=1).astype(float)

        if last_played and last_played in song_to_idx:
            last_col = song_to_idx[last_played]
            last_co_arr = normalized[cand_row_indices, last_col].copy()
            for k, s in enumerate(candidate_in_matrix):
                if s == last_played:
                    last_co_arr[k] = 0.0
        else:
            last_co_arr = np.zeros(len(candidate_in_matrix))

        affinity = avg_co_arr.copy()
        sorted_order = np.argsort(-affinity)
        rank = np.empty_like(sorted_order, dtype=float)
        rank[sorted_order] = np.arange(len(sorted_order), dtype=float)

        for k, song in enumerate(candidate_in_matrix):
            records.append(
                {
                    "song_name": song,
                    "avg_cooccurrence_with_recent": float(avg_co_arr[k]),
                    "max_cooccurrence_with_recent": float(max_co_arr[k]),
                    "n_strong_pairs_recent": float(n_strong_arr[k]),
                    "cooccurrence_with_last_played": float(last_co_arr[k]),
                    "pair_affinity_rank": float(rank[k]),
                }
            )

    for song in candidate_not_in_matrix:
        records.append(
            {
                "song_name": song,
                "avg_cooccurrence_with_recent": 0.0,
                "max_cooccurrence_with_recent": 0.0,
                "n_strong_pairs_recent": 0.0,
                "cooccurrence_with_last_played": 0.0,
                "pair_affinity_rank": 0.0,
            }
        )

    return pd.DataFrame(records)
