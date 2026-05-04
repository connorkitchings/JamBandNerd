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
        Columns ``["song_name", *SET_POSITION_FEATURES]``.
    """
    if historical_plays.empty:
        return pd.DataFrame(
            columns=["song_name"] + SET_POSITION_FEATURES,
        )

    plays = historical_plays
    has_set_number = "set_number" in plays.columns
    has_song_position = "song_position" in plays.columns
    has_encore = "encore" in plays.columns

    n_plays = plays.groupby("song_name").size().rename("n_plays")
    result = n_plays.reset_index()[["song_name"]].copy()
    result["n_plays"] = n_plays.values

    if has_set_number:
        sn = plays[["song_name", "set_number"]].copy()
        sn["set_number"] = pd.to_numeric(
            sn["set_number"], errors="coerce"
        ).astype("Float64")
        sn = sn.dropna(subset=["set_number"])
        if not sn.empty:
            counts = (
                sn.groupby(["song_name", "set_number"])
                .size()
                .unstack(fill_value=0)
            )
            result = result.merge(counts, on="song_name", how="left")
            s1 = result.get(1, pd.Series(0, index=result.index)).fillna(0)
            s2 = result.get(2, pd.Series(0, index=result.index)).fillna(0)
            result["pct_set_1"] = s1.values / result["n_plays"].values
            result["pct_set_2"] = s2.values / result["n_plays"].values
            denom = result["pct_set_1"] + result["pct_set_2"]
            result["set_affinity"] = np.where(
                denom > 0, result["pct_set_2"] / denom, 0.0
            )
        else:
            result["pct_set_1"] = 0.0
            result["pct_set_2"] = 0.0
            result["set_affinity"] = 0.0
    else:
        result["pct_set_1"] = 0.0
        result["pct_set_2"] = 0.0
        result["set_affinity"] = 0.0

    if has_encore:
        encore_mean = (
            plays.fillna({"encore": False})
            .groupby("song_name")["encore"]
            .mean()
            .rename("pct_encore")
        )
        result = result.merge(encore_mean, on="song_name", how="left")
        result["pct_encore"] = result["pct_encore"].fillna(0.0)
    else:
        result["pct_encore"] = 0.0

    if has_song_position:
        pos = plays[["song_name", "show_index", "song_position"]].copy()
        pos["song_position"] = pd.to_numeric(
            pos["song_position"], errors="coerce"
        ).astype("Float64")
        pos = pos.dropna(subset=["song_position"])
        if not pos.empty and "show_index" in pos.columns:
            show_max = (
                pos.groupby("show_index")["song_position"]
                .max()
                .rename("max_pos")
            )
            pos = pos.merge(show_max, on="show_index", how="left")
            pos["norm_pos"] = np.where(
                pos["max_pos"] > 1,
                (pos["song_position"] - 1) / (pos["max_pos"] - 1),
                0.5,
            )
            pos_stats = pos.groupby("song_name")["norm_pos"].agg(
                typical_position_pct="mean",
                position_consistency=lambda x: x.std(ddof=0),
            )
            result = result.merge(pos_stats, on="song_name", how="left")
            result["typical_position_pct"] = result[
                "typical_position_pct"
            ].fillna(0.0)
            result["position_consistency"] = result[
                "position_consistency"
            ].fillna(0.0)
        else:
            result["typical_position_pct"] = 0.0
            result["position_consistency"] = 0.0
    else:
        result["typical_position_pct"] = 0.0
        result["position_consistency"] = 0.0

    return result[["song_name"] + SET_POSITION_FEATURES]
