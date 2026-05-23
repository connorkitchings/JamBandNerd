"""Shared matrix-based feature engineering for fast predictors.

Provides presence-matrix construction, gap computation, cumulative-sum
window features, month-specific aggregates, and precomputed per-song
distributions.  All functions are pure and band-agnostic; band-specific
variations are handled through parameters.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

EMPTY_ARR: np.ndarray = np.array([], dtype=float)

DEFAULT_LGB_PARAMS: dict[str, Any] = {
    "objective": "rank_xendcg",
    "metric": "ndcg",
    "eval_at": [10, 25, 50],
    "num_leaves": 31,
    "learning_rate": 0.05,
    "min_data_in_leaf": 5,
    "verbose": -1,
    "seed": 42,
}
DEFAULT_LGB_ROUNDS = 200


def clean_plays(
    plays: pd.DataFrame,
    *,
    extra_context_cols: tuple[str, ...] = (),
    coerce_set_types: bool = False,
) -> pd.DataFrame:
    base_columns = ["song_name", "show_index", "show_date"]
    context_columns = [
        column
        for column in ("tour_name", "venue_name", "city", "state", "country")
        if column in plays.columns
    ] + [column for column in extra_context_cols if column in plays.columns]
    set_columns = [
        column
        for column in ("set_number", "song_position", "encore")
        if column in plays.columns
    ]
    df = plays[base_columns + context_columns + set_columns].copy()
    df = df.dropna(subset=["song_name", "show_index", "show_date"])
    df["show_date"] = pd.to_datetime(df["show_date"], errors="coerce")
    df["show_index"] = pd.to_numeric(df["show_index"], errors="coerce")
    if coerce_set_types:
        if "set_number" in df.columns:
            df["set_number"] = pd.to_numeric(df["set_number"], errors="coerce").astype(
                "Int64"
            )
        if "song_position" in df.columns:
            df["song_position"] = pd.to_numeric(
                df["song_position"], errors="coerce"
            ).astype("Int64")
        if "encore" in df.columns:
            df["encore"] = df["encore"].fillna(False).astype(bool)
    df = df.dropna(subset=["show_date", "show_index"])
    df["show_index"] = df["show_index"].astype(int)
    return df.reset_index(drop=True)


def build_presence(plays: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    pres = (
        plays.groupby(["song_name", "show_index"])
        .size()
        .gt(0)
        .unstack(fill_value=False)
    )
    show_cols = pres.columns.to_numpy(dtype=np.int64)
    return pres, show_cols


def build_gap_matrix(
    presence: pd.DataFrame,
    *,
    zero_based: bool = False,
) -> pd.DataFrame:
    n_shows = presence.shape[1]
    col_pos = np.arange(n_shows, dtype=float)

    play_col = np.where(presence.values, col_pos[np.newaxis, :], np.nan)
    df = pd.DataFrame(play_col, index=presence.index, columns=presence.columns)

    last_play = df.ffill(axis=1)
    last_play_before = last_play.shift(1, axis=1)

    offset = 1.0 if zero_based else 0.0
    gap_arr = col_pos[np.newaxis, :] - last_play_before.values - offset
    gap_arr = np.where(np.isnan(last_play_before.values), float(n_shows), gap_arr)
    if zero_based:
        gap_arr = np.clip(gap_arr, 0.0, None)
    return pd.DataFrame(gap_arr, index=presence.index, columns=presence.columns)


def window_plays(cum: pd.DataFrame, upper_col: int, window: int) -> pd.Series:
    end = upper_col - 1
    if end < 0:
        return pd.Series(0.0, index=cum.index)
    end = min(end, cum.shape[1] - 1)
    start = max(0, upper_col - window)
    if start == 0:
        return cum.iloc[:, end].astype(float)
    return (cum.iloc[:, end] - cum.iloc[:, start - 1]).astype(float)


def window_plays_by_days(
    plays: pd.DataFrame,
    presence: pd.DataFrame,
    ref_col: int,
    days: int,
    col_dates: list,
) -> pd.Series:
    if ref_col < 0 or not col_dates:
        return pd.Series(0.0, index=presence.index)

    ref_date = col_dates[ref_col]
    if ref_date is None:
        return pd.Series(0.0, index=presence.index)

    cutoff_date = ref_date - pd.Timedelta(days=days)
    valid_cols = [
        i
        for i, d in enumerate(col_dates[: ref_col + 1])
        if d is not None and d >= cutoff_date
    ]

    if not valid_cols:
        return pd.Series(0.0, index=presence.index)

    return presence.iloc[:, valid_cols].sum(axis=1).astype(float)


def build_month_cums(
    plays: pd.DataFrame,
    presence: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    all_songs = presence.index
    cols = presence.columns
    month_cums: dict[int, pd.DataFrame] = {}
    for m in range(1, 13):
        mp = (
            plays[plays["_month"] == m]
            .groupby(["song_name", "show_index"])
            .size()
            .unstack(fill_value=0)
            .reindex(index=all_songs, columns=cols, fill_value=0)
            .astype(float)
        )
        month_cums[m] = mp.cumsum(axis=1)
    return month_cums


def precompute_gap_distributions(
    presence: pd.DataFrame,
) -> dict[str, np.ndarray]:
    arr = presence.values.astype(bool)
    result: dict[str, np.ndarray] = {}
    for i, song in enumerate(presence.index):
        play_cols = np.where(arr[i])[0]
        if len(play_cols) >= 2:
            result[str(song)] = np.sort(np.diff(play_cols).astype(float))
        else:
            result[str(song)] = EMPTY_ARR
    return result


def precompute_first_play_col(presence: pd.DataFrame) -> dict[str, int]:
    arr = presence.values.astype(bool)
    result: dict[str, int] = {}
    for i, song in enumerate(presence.index):
        play_cols = np.where(arr[i])[0]
        result[str(song)] = int(play_cols[0]) if len(play_cols) > 0 else 0
    return result


def precompute_avg_days_between_plays(
    presence: pd.DataFrame, col_dates: list
) -> dict[str, float]:
    arr = presence.values.astype(bool)
    result: dict[str, float] = {}
    for i, song in enumerate(presence.index):
        play_cols = np.where(arr[i])[0]
        if len(play_cols) >= 2:
            dates = [
                col_dates[c]
                for c in play_cols
                if c < len(col_dates) and col_dates[c] is not None
            ]
            if len(dates) >= 2:
                diffs = [(dates[k + 1] - dates[k]).days for k in range(len(dates) - 1)]
                result[str(song)] = float(np.mean(diffs))
            else:
                result[str(song)] = 0.0
        else:
            result[str(song)] = 0.0
    return result


def run_position_continuous(
    show_dates: list[date], target_show_date: date, gap_days: int = 1
) -> int:
    if not show_dates:
        return 1
    last = show_dates[-1]
    if (target_show_date - last).days > gap_days:
        return 1
    night = 2
    for i in range(len(show_dates) - 1, 0, -1):
        if (show_dates[i] - show_dates[i - 1]).days <= gap_days:
            night += 1
        else:
            break
    return night


def tour_position_continuous(
    show_dates: list[date], target_show_date: date, tour_gap_days: int = 14
) -> int:
    if not show_dates:
        return 1
    all_dates = list(show_dates) + [target_show_date]
    pos = 1
    for i in range(len(all_dates) - 1, 0, -1):
        gap = (all_dates[i] - all_dates[i - 1]).days
        if gap >= tour_gap_days:
            break
        pos += 1
    return pos
