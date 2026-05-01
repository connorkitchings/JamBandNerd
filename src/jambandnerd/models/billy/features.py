"""Billy Strings-specific feature engineering for Phase B setlist prediction.

Adapts the Goose Phase B feature set for Billy's dataset. All 10 Goose run/tour/
recency features apply directly. One Billy-specific feature is added: is_cover,
which flags songs with a known original artist (covers vs. Billy originals).

All aggregations operate strictly on historical_plays filtered to shows before the
prediction reference_date. No data from the target setlist enters any aggregate.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List

import numpy as np
import pandas as pd

from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)

BILLY_EXTRA_FEATURES: list[str] = [
    "month_play_rate",
    "show_position_in_run",
    "tour_position",
    "plays_past_10",
    "plays_past_25",
    "diff_25_to_50",
    "same_venue_run_prior_played",
    "same_venue_run_prior_play_count",
    "same_venue_run_prior_play_share",
    "same_venue_run_position",
    "is_cover",
]


def _run_position(
    show_dates: List[date], target_show_date: date, gap_days: int = 1
) -> int:
    """Night number of target_show_date within its consecutive run (1-indexed)."""
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


def _tour_position(
    show_dates: List[date], target_show_date: date, tour_gap_days: int = 14
) -> int:
    """Show index of target_show_date within the current touring stretch (1-indexed)."""
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


def compute_billy_song_features(
    historical_plays: pd.DataFrame,
    *,
    target_show_date: date,
    target_show_context: dict[str, Any] | pd.Series | None = None,
    songs_lookup: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compute Billy-specific per-song features from pre-filtered historical plays.

    Returns a DataFrame indexed by song_name with BILLY_EXTRA_FEATURES columns.
    All columns default to 0.0 for songs without the relevant data.

    songs_lookup maps song_name -> is_cover (1.0 = cover, 0.0 = original/unknown).
    If None, is_cover defaults to 0.0 for all songs.
    """
    if historical_plays.empty:
        return pd.DataFrame(columns=["song_name"] + BILLY_EXTRA_FEATURES)

    plays = historical_plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce").dt.date

    # Sort by show_index once for fast window slicing below.
    plays = plays.sort_values("show_index").reset_index(drop=True)
    show_idx_arr = plays["show_index"].to_numpy()

    show_dates: List[date] = sorted(plays["show_date"].dropna().unique().tolist())
    show_pos = _run_position(show_dates, target_show_date, gap_days=1)
    tour_pos = _tour_position(show_dates, target_show_date, tour_gap_days=14)
    reference_index = int(show_idx_arr[-1]) + 1 if len(show_idx_arr) else 1
    historical_show_indices = set(show_idx_arr.tolist())

    target_month = target_show_date.month
    plays["_month"] = pd.to_datetime(
        plays["show_date"].astype(str), errors="coerce"
    ).dt.month

    total_plays = plays.groupby("song_name")["show_index"].nunique().rename("_total")
    month_plays = (
        plays[plays["_month"] == target_month]
        .groupby("song_name")["show_index"]
        .nunique()
        .rename("_month_plays")
    )

    feats = pd.DataFrame(total_plays).join(month_plays, how="left").fillna(0)
    feats["month_play_rate"] = feats["_month_plays"] / feats["_total"].clip(lower=1)
    feats["show_position_in_run"] = float(show_pos)
    feats["tour_position"] = float(tour_pos)

    for window in (10, 25, 50):
        window_start = reference_index - window
        window_show_count = max(
            1,
            sum(
                window_start <= si < reference_index
                for si in historical_show_indices
            ),
        )
        # Use searchsorted for O(log n) window slice instead of boolean mask.
        w_cutoff = int(np.searchsorted(show_idx_arr, window_start, side="left"))
        window_plays = (
            plays.iloc[w_cutoff:]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename(f"_plays_past_{window}")
        )
        feats = feats.join(window_plays, how="left").fillna(0)
        if window in (10, 25):
            feats[f"plays_past_{window}"] = feats[f"_plays_past_{window}"]
        feats[f"_pct_shows_{window}"] = feats[f"_plays_past_{window}"] / window_show_count

    feats["diff_25_to_50"] = feats["_pct_shows_25"] - feats["_pct_shows_50"]

    normalized_target_context = normalize_target_show_context(target_show_context)
    if normalized_venue_key(normalized_target_context):
        same_run_indices = same_venue_run_show_indices(plays, normalized_target_context)
    else:
        same_run_indices = []

    if same_run_indices:
        same_run_plays = (
            plays[plays["show_index"].isin(same_run_indices)]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename("_same_run_prior_play_count")
        )
        feats = feats.join(same_run_plays, how="left").fillna(0)
        feats["same_venue_run_prior_play_count"] = feats["_same_run_prior_play_count"]
        feats["same_venue_run_prior_played"] = (
            feats["same_venue_run_prior_play_count"] > 0
        ).astype(float)
        feats["same_venue_run_prior_play_share"] = (
            feats["same_venue_run_prior_play_count"] / len(same_run_indices)
        )
        feats["same_venue_run_position"] = float(len(same_run_indices) + 1)
    else:
        feats["same_venue_run_prior_played"] = 0.0
        feats["same_venue_run_prior_play_count"] = 0.0
        feats["same_venue_run_prior_play_share"] = 0.0
        feats["same_venue_run_position"] = (
            1.0 if normalized_venue_key(normalized_target_context) else 0.0
        )

    non_cover_cols = [c for c in BILLY_EXTRA_FEATURES if c != "is_cover"]
    result = feats[non_cover_cols].reset_index()
    result.columns = ["song_name"] + non_cover_cols

    result["is_cover"] = (
        result["song_name"].map(songs_lookup).fillna(0.0)
        if songs_lookup
        else 0.0
    )

    return result


def _target_context_from_training_group(
    historical_plays: pd.DataFrame,
    group: pd.DataFrame,
) -> dict[str, Any]:
    """Build target show context for a training row group without song labels."""
    if historical_plays.empty or group.empty:
        return {}

    target_rows = pd.DataFrame()
    target_show_index = group["target_show_index"].iloc[0]
    if pd.notna(target_show_index):
        target_rows = historical_plays[
            historical_plays["show_index"].astype(int) == int(target_show_index)
        ]

    if target_rows.empty:
        target_show_date = pd.to_datetime(
            group["target_show_date"].iloc[0], errors="coerce"
        )
        if pd.notna(target_show_date):
            target_rows = historical_plays[
                pd.to_datetime(historical_plays["show_date"], errors="coerce").dt.date
                == target_show_date.date()
            ]

    if target_rows.empty:
        return {}

    return normalize_target_show_context(target_rows.iloc[0])


def augment_training_frame(
    training_frame: pd.DataFrame,
    historical_plays: pd.DataFrame,
    *,
    songs_lookup: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Merge Billy-specific features into a deal-style training frame.

    training_frame must have target_show_index and target_show_date columns.
    historical_plays is the full model_data.historical_plays; this function
    replicates the per-target-show history truncation used in build_training_frame.

    Uses a presence matrix + cumulative sum to compute all recency window features
    in O(n_songs) per target show instead of O(n_rows × groupby_overhead).
    """
    if training_frame.empty:
        for col in BILLY_EXTRA_FEATURES:
            training_frame[col] = 0.0
        return training_frame

    plays = historical_plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")
    plays = plays.sort_values("show_index").reset_index(drop=True)
    plays["_month"] = plays["show_date"].dt.month

    # ── Presence matrix: (n_songs) × (n_show_indices) ────────────────────────
    # Build once; cumsum enables O(log n) window queries instead of per-show groupby.
    presence = (
        plays.groupby(["song_name", "show_index"])
        .size()
        .unstack(fill_value=0)
        .astype(float)
    )
    all_songs: pd.Index = presence.index
    show_cols_idx: pd.Index = presence.columns          # pandas Index (for reindex)
    show_cols: np.ndarray = show_cols_idx.to_numpy(dtype=np.int64)  # for searchsorted
    cum_total: pd.DataFrame = presence.cumsum(axis=1)

    # Month-specific cumulative sums (12 matrices, all pre-computed once).
    month_cums: dict[int, pd.DataFrame] = {}
    for m in range(1, 13):
        mp = (
            plays[plays["_month"] == m]
            .groupby(["song_name", "show_index"])
            .size()
            .unstack(fill_value=0)
            .reindex(index=all_songs, columns=show_cols_idx, fill_value=0)
            .astype(float)
        )
        month_cums[m] = mp.cumsum(axis=1)

    def _cum_window(cum: pd.DataFrame, a: int, b: int) -> pd.Series:
        """Per-song play count in show_index range [a, b)."""
        b_pos = int(np.searchsorted(show_cols, b, side="left")) - 1
        if b_pos < 0:
            return pd.Series(0.0, index=all_songs, dtype=float)
        a_pos = int(np.searchsorted(show_cols, a, side="left"))
        if a_pos > b_pos:
            return pd.Series(0.0, index=all_songs, dtype=float)
        if a_pos == 0:
            return cum.iloc[:, b_pos].astype(float)
        return (cum.iloc[:, b_pos] - cum.iloc[:, a_pos - 1]).astype(float)

    def _show_count_in_window(a: int, b: int) -> int:
        return max(1, int(np.sum((show_cols >= a) & (show_cols < b))))

    show_idx_arr_full = plays["show_index"].to_numpy()

    billy_rows: list[pd.DataFrame] = []
    for (target_show_index, target_show_date_str), group in training_frame.groupby(
        ["target_show_index", "target_show_date"],
        dropna=False,
    ):
        if pd.isna(target_show_index):
            continue
        target_idx = int(target_show_index)
        target_date = pd.Timestamp(target_show_date_str).date()
        target_month = target_date.month

        # reference_index = max historical show_index + 1 (mirrors compute_billy_song_features).
        before_target = show_cols[show_cols < target_idx]
        ref_idx = int(before_target[-1]) + 1 if len(before_target) else 1

        # Sub-plays slice needed for scalar features and same-venue-run lookup.
        cutoff = int(np.searchsorted(show_idx_arr_full, target_idx, side="left"))
        sub_plays = plays.iloc[:cutoff]

        # Scalar features: identical for all songs in this target show.
        sub_show_dates: List[date] = sorted(
            sub_plays["show_date"].dropna().dt.date.unique().tolist()
        )
        show_pos = _run_position(sub_show_dates, target_date, gap_days=1)
        tour_pos = _tour_position(sub_show_dates, target_date, tour_gap_days=14)

        # Vectorized recency window features.
        total_before = _cum_window(cum_total, 0, target_idx)
        month_before = _cum_window(month_cums[target_month], 0, target_idx)
        w10 = _cum_window(cum_total, ref_idx - 10, ref_idx)
        w25 = _cum_window(cum_total, ref_idx - 25, ref_idx)
        w50 = _cum_window(cum_total, ref_idx - 50, ref_idx)
        sc25 = _show_count_in_window(ref_idx - 25, ref_idx)
        sc50 = _show_count_in_window(ref_idx - 50, ref_idx)
        pct25 = w25 / sc25
        pct50 = w50 / sc50

        # Same-venue-run features: context-dependent, per-show computation.
        target_context = _target_context_from_training_group(historical_plays, group)
        normalized_ctx = normalize_target_show_context(target_context)
        if normalized_venue_key(normalized_ctx):
            same_run_indices = same_venue_run_show_indices(sub_plays, normalized_ctx)
        else:
            same_run_indices = []

        if same_run_indices:
            same_run_counts = (
                sub_plays[sub_plays["show_index"].isin(same_run_indices)]
                .groupby("song_name")["show_index"]
                .nunique()
                .reindex(all_songs, fill_value=0)
                .astype(float)
            )
            svrp_played = (same_run_counts > 0).astype(float)
            svrp_count = same_run_counts
            svrp_share = same_run_counts / len(same_run_indices)
            svrp_position = float(len(same_run_indices) + 1)
        else:
            zeros = pd.Series(0.0, index=all_songs)
            svrp_played = zeros
            svrp_count = zeros
            svrp_share = zeros
            svrp_position = 1.0 if normalized_venue_key(normalized_ctx) else 0.0

        is_cover_vals = (
            all_songs.map(songs_lookup).fillna(0.0).astype(float).values
            if songs_lookup
            else 0.0
        )

        df = pd.DataFrame({
            "song_name": all_songs.to_numpy(),
            "month_play_rate": (month_before / total_before.clip(lower=1)).values,
            "show_position_in_run": float(show_pos),
            "tour_position": float(tour_pos),
            "plays_past_10": w10.values,
            "plays_past_25": w25.values,
            "diff_25_to_50": (pct25 - pct50).values,
            "same_venue_run_prior_played": svrp_played.values,
            "same_venue_run_prior_play_count": svrp_count.values,
            "same_venue_run_prior_play_share": svrp_share.values,
            "same_venue_run_position": svrp_position,
            "is_cover": is_cover_vals,
        })
        df["target_show_index"] = target_show_index
        df["target_show_date"] = target_show_date_str
        billy_rows.append(df)

    if not billy_rows:
        for col in BILLY_EXTRA_FEATURES:
            training_frame[col] = 0.0
        return training_frame

    all_billy = pd.concat(billy_rows, ignore_index=True)
    augmented = training_frame.merge(
        all_billy,
        on=["target_show_index", "target_show_date", "song_name"],
        how="left",
    )
    for col in BILLY_EXTRA_FEATURES:
        if col in augmented.columns:
            augmented[col] = augmented[col].fillna(0.0)
        else:
            augmented[col] = 0.0
    return augmented
