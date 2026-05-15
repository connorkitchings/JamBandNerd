"""Directional within-set bigram transition matrix for Stage 2 of the 3-stage pipeline.

Builds a sparse dictionary of conditional probabilities P(B|A) from historical
setlist data, respecting set boundaries (no cross-set or cross-show transitions).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


class TransitionMatrix:
    """Sparse directional bigram transition matrix P(B|A) built from setlists."""

    def __init__(self) -> None:
        self._transitions: Dict[Tuple[str, str], int] = {}
        self._prefix_counts: Dict[str, int] = {}

    @property
    def n_pairs(self) -> int:
        return len(self._transitions)

    def build(self, setlists_df: pd.DataFrame) -> TransitionMatrix:
        required = {"show_id", "set_number", "song_position", "song_name"}
        missing = required - set(setlists_df.columns)
        if missing:
            raise ValueError(f"setlists_df missing required columns: {missing}")

        df = setlists_df.copy()
        df["song_position"] = pd.to_numeric(df["song_position"], errors="coerce")
        df["set_number"] = pd.to_numeric(df["set_number"], errors="coerce")
        df.dropna(subset=["song_position", "set_number", "song_name"], inplace=True)
        df["song_name"] = df["song_name"].astype(str).str.strip()
        df = df.sort_values(["show_id", "set_number", "song_position"])

        df["show_id"] = df["show_id"].astype(str)
        df["set_number"] = df["set_number"].astype(int)
        df["_prev_song"] = df["song_name"].shift(1)
        df["_prev_show"] = df["show_id"].shift(1)
        df["_prev_set"] = df["set_number"].shift(1)

        same_group = (df["show_id"] == df["_prev_show"]) & (
            df["set_number"] == df["_prev_set"]
        )
        pairs = df.loc[same_group & df["_prev_song"].notna()]

        if not pairs.empty:
            pair_counts = pairs.groupby(["_prev_song", "song_name"]).size().to_dict()
            prefix_counts = pairs.groupby("_prev_song").size().to_dict()
            self._transitions.update(pair_counts)
            for song, cnt in prefix_counts.items():
                self._prefix_counts[song] = self._prefix_counts.get(song, 0) + cnt

        return self

    def get_probability(self, song_a: str, song_b: str) -> float | None:
        count = self._transitions.get((song_a, song_b), 0)
        if count == 0:
            return None
        prefix = self._prefix_counts.get(song_a, 0)
        if prefix == 0:
            return None
        return count / prefix

    def get_top_transitions(self, song: str, n: int = 10) -> List[Tuple[str, float]]:
        candidates: List[Tuple[str, float]] = []
        for (a, b), count in self._transitions.items():
            if a == song:
                prob = self.get_probability(a, b)
                if prob is not None:
                    candidates.append((b, prob))
        candidates.sort(key=lambda x: (-x[1], x[0]))
        return candidates[:n]

    def as_nested_dict(self) -> Dict[str, Dict[str, float]]:
        nested: Dict[str, Dict[str, float]] = {}
        for (a, b), count in self._transitions.items():
            prefix = self._prefix_counts.get(a, 0)
            if prefix == 0:
                continue
            prob = count / prefix
            if a not in nested:
                nested[a] = {}
            nested[a][b] = prob
        return nested
