"""Goose-specific feature engineering for Phase B setlist prediction.

Tier A — computed from show_date and song_name only (always available).
Tier B — computed from set_number, song_position, encore (requires gaps.py
          to have those columns plumbed through historical_plays).

All aggregations operate strictly on historical_plays that are already
filtered to shows before the prediction reference_date.  The only
forward-looking input is target_show_date, which is used purely as a
label for day-of-week and calendar-month lookups — no data from that
date enters any aggregate.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pandas as pd

GOOSE_EXTRA_FEATURES: list[str] = [
    # Tier A
    "dow_play_rate",
    "month_play_rate",
    "show_position_in_run",
    "tour_position",
    # Tier B (fall back to 0.0 if set columns absent)
    "set1_play_rate",
    "set2_play_rate",
    "encore_rate",
    "mean_song_position",
]


def _run_position(
    show_dates: List[date], target_show_date: date, gap_days: int = 1
) -> int:
    """Night number of target_show_date within its consecutive run (1-indexed)."""
    if not show_dates:
        return 1
    last = show_dates[-1]
    if (target_show_date - last).days > gap_days:
        return 1  # new run
    night = 2  # target continues from last historical show
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


def compute_goose_song_features(
    historical_plays: pd.DataFrame,
    *,
    target_show_date: date,
) -> pd.DataFrame:
    """Compute Goose-specific per-song features from pre-filtered historical plays.

    Returns a DataFrame indexed by song_name with GOOSE_EXTRA_FEATURES columns.
    All columns default to 0.0 for songs without the relevant data.
    """
    if historical_plays.empty:
        return pd.DataFrame(columns=["song_name"] + GOOSE_EXTRA_FEATURES)

    plays = historical_plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce").dt.date

    # --- Show-level features (constant across all songs) ---
    show_dates: List[date] = sorted(plays["show_date"].dropna().unique().tolist())
    show_pos = _run_position(show_dates, target_show_date, gap_days=1)
    tour_pos = _tour_position(show_dates, target_show_date, tour_gap_days=14)

    target_dow = target_show_date.weekday()
    target_month = target_show_date.month

    plays["_dow"] = pd.to_datetime(plays["show_date"].astype(str)).dt.dayofweek
    plays["_month"] = pd.to_datetime(plays["show_date"].astype(str)).dt.month

    # --- Song-level Tier A aggregates ---
    total_plays = plays.groupby("song_name")["show_index"].nunique().rename("_total")
    dow_plays = (
        plays[plays["_dow"] == target_dow]
        .groupby("song_name")["show_index"]
        .nunique()
        .rename("_dow_plays")
    )
    month_plays = (
        plays[plays["_month"] == target_month]
        .groupby("song_name")["show_index"]
        .nunique()
        .rename("_month_plays")
    )

    feats = (
        pd.DataFrame(total_plays)
        .join(dow_plays, how="left")
        .join(month_plays, how="left")
    )
    feats = feats.fillna(0)
    feats["dow_play_rate"] = feats["_dow_plays"] / feats["_total"].clip(lower=1)
    feats["month_play_rate"] = feats["_month_plays"] / feats["_total"].clip(lower=1)
    feats["show_position_in_run"] = float(show_pos)
    feats["tour_position"] = float(tour_pos)

    # --- Tier B: set-position aggregates ---
    has_set_cols = "set_number" in plays.columns and "encore" in plays.columns
    if has_set_cols:
        set1_plays = (
            plays[plays["set_number"] == 1]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename("_set1")
        )
        set2_plays = (
            plays[plays["set_number"] == 2]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename("_set2")
        )
        encore_plays = (
            plays[plays["encore"].fillna(False).astype(bool)]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename("_encore")
        )
        feats = (
            feats.join(set1_plays, how="left")
            .join(set2_plays, how="left")
            .join(encore_plays, how="left")
        )
        feats = feats.fillna(0)
        feats["set1_play_rate"] = feats["_set1"] / feats["_total"].clip(lower=1)
        feats["set2_play_rate"] = feats["_set2"] / feats["_total"].clip(lower=1)
        feats["encore_rate"] = feats["_encore"] / feats["_total"].clip(lower=1)
    else:
        feats["set1_play_rate"] = 0.0
        feats["set2_play_rate"] = 0.0
        feats["encore_rate"] = 0.0

    has_pos_col = "song_position" in plays.columns
    if has_pos_col:
        mean_pos = (
            plays.groupby("song_name")["song_position"]
            .mean()
            .rename("mean_song_position")
        )
        feats = feats.join(mean_pos, how="left")
        feats["mean_song_position"] = feats["mean_song_position"].fillna(0.0)
    else:
        feats["mean_song_position"] = 0.0

    result = feats[GOOSE_EXTRA_FEATURES].reset_index()
    result.columns = ["song_name"] + GOOSE_EXTRA_FEATURES
    return result


def augment_training_frame(
    training_frame: pd.DataFrame,
    historical_plays: pd.DataFrame,
) -> pd.DataFrame:
    """Merge Goose-specific features into a deal-style training frame.

    training_frame must have target_show_index and target_show_date columns.
    historical_plays is the full model_data.historical_plays; this function
    replicates the per-target-show history truncation used in build_training_frame.
    """
    if training_frame.empty:
        for col in GOOSE_EXTRA_FEATURES:
            training_frame[col] = 0.0
        return training_frame

    plays = historical_plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")

    goose_rows: list[pd.DataFrame] = []
    for target_show_date_str, group in training_frame.groupby("target_show_date"):
        target_date = pd.Timestamp(target_show_date_str).date()
        prediction_date = target_date - timedelta(days=1)
        sub_plays = plays[plays["show_date"].dt.date <= prediction_date].copy()
        goose_feats = compute_goose_song_features(
            sub_plays, target_show_date=target_date
        )
        goose_feats["target_show_date"] = target_show_date_str
        goose_rows.append(goose_feats)

    if not goose_rows:
        for col in GOOSE_EXTRA_FEATURES:
            training_frame[col] = 0.0
        return training_frame

    all_goose = pd.concat(goose_rows, ignore_index=True)
    augmented = training_frame.merge(
        all_goose, on=["target_show_date", "song_name"], how="left"
    )
    for col in GOOSE_EXTRA_FEATURES:
        if col in augmented.columns:
            augmented[col] = augmented[col].fillna(0.0)
        else:
            augmented[col] = 0.0
    return augmented
