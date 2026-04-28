"""Goose-specific feature engineering for Phase B setlist prediction.

All aggregations operate strictly on historical_plays that are already
filtered to shows before the prediction reference_date. The only
forward-looking inputs are target_show_date and target show venue context,
which are labels for calendar and same-venue-run lookups. No data from the
target setlist enters any aggregate.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List

import pandas as pd

from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)

GOOSE_EXTRA_FEATURES: list[str] = [
    "dow_play_rate",
    "month_play_rate",
    "show_position_in_run",
    "tour_position",
    "plays_past_10",
    "plays_past_25",
    "pct_shows_10",
    "pct_shows_25",
    "diff_25_to_50",
    "same_venue_run_prior_played",
    "same_venue_run_prior_play_count",
    "same_venue_run_prior_play_share",
    "same_venue_run_position",
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
    target_show_context: dict[str, Any] | pd.Series | None = None,
) -> pd.DataFrame:
    """Compute Goose-specific per-song features from pre-filtered historical plays.

    Returns a DataFrame indexed by song_name with GOOSE_EXTRA_FEATURES columns.
    All columns default to 0.0 for songs without the relevant data.
    """
    if historical_plays.empty:
        return pd.DataFrame(columns=["song_name"] + GOOSE_EXTRA_FEATURES)

    plays = historical_plays.copy()
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce").dt.date

    show_dates: List[date] = sorted(plays["show_date"].dropna().unique().tolist())
    show_pos = _run_position(show_dates, target_show_date, gap_days=1)
    tour_pos = _tour_position(show_dates, target_show_date, tour_gap_days=14)
    reference_index = int(plays["show_index"].max()) + 1
    historical_show_indices = set(plays["show_index"].dropna().astype(int).unique())

    target_dow = target_show_date.weekday()
    target_month = target_show_date.month

    plays["_dow"] = pd.to_datetime(plays["show_date"].astype(str)).dt.dayofweek
    plays["_month"] = pd.to_datetime(plays["show_date"].astype(str)).dt.month

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

    for window in (10, 25, 50):
        window_start = reference_index - window
        window_show_count = max(
            1,
            sum(
                show_index >= window_start and show_index < reference_index
                for show_index in historical_show_indices
            ),
        )
        window_plays = (
            plays[plays["show_index"] >= window_start]
            .groupby("song_name")["show_index"]
            .nunique()
            .rename(f"_plays_past_{window}")
        )
        feats = feats.join(window_plays, how="left").fillna(0)
        feats[f"plays_past_{window}"] = feats[f"_plays_past_{window}"]
        feats[f"pct_shows_{window}"] = (
            feats[f"_plays_past_{window}"] / window_show_count
        )

    feats["diff_25_to_50"] = feats["pct_shows_25"] - feats["pct_shows_50"]

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
        feats["same_venue_run_prior_play_share"] = feats[
            "same_venue_run_prior_play_count"
        ] / len(same_run_indices)
        feats["same_venue_run_position"] = float(len(same_run_indices) + 1)
    else:
        feats["same_venue_run_prior_played"] = 0.0
        feats["same_venue_run_prior_play_count"] = 0.0
        feats["same_venue_run_prior_play_share"] = 0.0
        feats["same_venue_run_position"] = (
            1.0 if normalized_venue_key(normalized_target_context) else 0.0
        )

    result = feats[GOOSE_EXTRA_FEATURES].reset_index()
    result.columns = ["song_name"] + GOOSE_EXTRA_FEATURES
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
    for (target_show_index, target_show_date_str), group in training_frame.groupby(
        ["target_show_index", "target_show_date"],
        dropna=False,
    ):
        target_date = pd.Timestamp(target_show_date_str).date()
        prediction_date = target_date - timedelta(days=1)
        sub_plays = plays[plays["show_date"].dt.date <= prediction_date].copy()
        target_context = _target_context_from_training_group(plays, group)
        goose_feats = compute_goose_song_features(
            sub_plays,
            target_show_date=target_date,
            target_show_context=target_context,
        )
        goose_feats["target_show_index"] = target_show_index
        goose_feats["target_show_date"] = target_show_date_str
        goose_rows.append(goose_feats)

    if not goose_rows:
        for col in GOOSE_EXTRA_FEATURES:
            training_frame[col] = 0.0
        return training_frame

    all_goose = pd.concat(goose_rows, ignore_index=True)
    augmented = training_frame.merge(
        all_goose,
        on=["target_show_index", "target_show_date", "song_name"],
        how="left",
    )
    for col in GOOSE_EXTRA_FEATURES:
        if col in augmented.columns:
            augmented[col] = augmented[col].fillna(0.0)
        else:
            augmented[col] = 0.0
    return augmented
