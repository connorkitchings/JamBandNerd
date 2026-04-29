"""Band-agnostic set-position feature engineering.

Computes per-song set-position statistics from historical plays that already
carry ``set_number``, ``song_position``, and ``encore`` columns (populated
by the shared normalization boundary in ``gaps.py``).

All aggregations operate strictly on plays before the prediction
``reference_date``.  When set-position columns are absent or empty the
features default to 0.0 so the module degrades gracefully for bands whose
collectors do not emit position data.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

SET_POSITION_FEATURES: list[str] = [
    "pct_set_1",
    "pct_set_2",
    "pct_encore",
    "typical_position_pct",
    "position_consistency",
    "set_affinity",
]


def _safe_div(n: float, d: float) -> float:
    return n / d if d > 0 else 0.0


def compute_set_position_features(
    historical_plays: pd.DataFrame,
) -> pd.DataFrame:
    """Return per-song set-position features derived from *historical_plays*.

    Parameters
    ----------
    historical_plays
        A DataFrame with at least ``song_name``.  Optionally includes
        ``set_number`` (Int64), ``song_position`` (Int64), and ``encore``
        (bool).  When columns are missing every feature defaults to 0.0.

    Returns
    -------
    pd.DataFrame
        Indexed by ``song_name`` with ``SET_POSITION_FEATURES`` columns.
    """
    if historical_plays.empty:
        return pd.DataFrame(
            columns=["song_name"] + SET_POSITION_FEATURES,
        )

    plays = historical_plays.copy()
    has_set_number = "set_number" in plays.columns
    has_song_position = "song_position" in plays.columns
    has_encore = "encore" in plays.columns

    if has_set_number:
        plays["set_number"] = pd.to_numeric(
            plays["set_number"], errors="coerce"
        ).astype("Float64")
    if has_song_position:
        plays["song_position"] = pd.to_numeric(
            plays["song_position"], errors="coerce"
        ).astype("Float64")
    if has_encore:
        plays["encore"] = plays["encore"].fillna(False).astype(bool)

    records: list[dict[str, Any]] = []

    for song_name, song_plays in plays.groupby("song_name"):
        n_plays = len(song_plays)

        pct_set_1 = 0.0
        pct_set_2 = 0.0
        pct_encore = 0.0
        typical_position_pct = 0.0
        position_consistency = 0.0
        set_affinity = 0.0

        if has_set_number and n_plays > 0:
            sn = song_plays["set_number"].dropna()
            if not sn.empty:
                counts = sn.value_counts()
                pct_set_1 = _safe_div(float(counts.get(1, 0)), n_plays)
                pct_set_2 = _safe_div(float(counts.get(2, 0)), n_plays)
                set_affinity = (
                    pct_set_2 / (pct_set_1 + pct_set_2)
                    if (pct_set_1 + pct_set_2) > 0
                    else 0.0
                )

        if has_encore and n_plays > 0:
            pct_encore = _safe_div(float(song_plays["encore"].sum()), n_plays)

        if has_song_position and n_plays > 0:
            positions = song_plays["song_position"].dropna()
            if not positions.empty:
                shows_in_song = song_plays.dropna(subset=["song_position"])
                if not shows_in_song.empty and "show_index" in shows_in_song.columns:
                    show_sizes = (
                        shows_in_song.groupby("show_index")["song_position"]
                        .max()
                        .to_dict()
                    )
                    normalized: list[float] = []
                    for _, row in shows_in_song.iterrows():
                        max_pos = show_sizes.get(row["show_index"], 1)
                        if max_pos > 1:
                            normalized.append(
                                (float(row["song_position"]) - 1.0) / (max_pos - 1.0)
                            )
                        else:
                            normalized.append(0.5)
                    if normalized:
                        typical_position_pct = float(np.mean(normalized))
                        position_consistency = float(np.std(normalized, ddof=0))

        records.append(
            {
                "song_name": song_name,
                "pct_set_1": pct_set_1,
                "pct_set_2": pct_set_2,
                "pct_encore": pct_encore,
                "typical_position_pct": typical_position_pct,
                "position_consistency": position_consistency,
                "set_affinity": set_affinity,
            }
        )

    return pd.DataFrame(records)
