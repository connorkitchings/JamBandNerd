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

        prev_song: str | None = None
        prev_show_id: str | None = None
        prev_set_number: int | None = None

        for _, row in df.iterrows():
            show_id = str(row["show_id"])
            set_number = int(row["set_number"])
            song = str(row["song_name"])

            if (
                prev_song is not None
                and show_id == prev_show_id
                and set_number == prev_set_number
            ):
                key = (prev_song, song)
                self._transitions[key] = self._transitions.get(key, 0) + 1
                self._prefix_counts[prev_song] = (
                    self._prefix_counts.get(prev_song, 0) + 1
                )

            prev_song = song
            prev_show_id = show_id
            prev_set_number = set_number

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
