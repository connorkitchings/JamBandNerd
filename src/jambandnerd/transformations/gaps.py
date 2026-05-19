"""Band-agnostic transformations for show indices, gaps, and other model features.

This module provides a centralized, refactored pipeline for computing all features
required by the various prediction models. It ensures that data leakage is prevented
by strictly adhering to a `reference_date` cutoff.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Tuple

import pandas as pd

from .normalization import sort_normalized_shows
from .run_context import normalize_target_show_context

logger = logging.getLogger(__name__)


def _stats_for_song(group: pd.DataFrame) -> pd.Series:
    """Helper function to calculate historical stats for a single song.

    Args:
        group: A pandas DataFrame containing all historical plays for a single song.
               Must contain 'show_index' and 'show_date' columns.

    Returns:
        A pandas Series containing aggregated statistical features (times_played,
        avg_gap, std_gap, etc.) for the song.
    """
    # Use unique show indices to avoid counting reprises/encores as separate plays
    plays_idx = sorted(group["show_index"].unique().tolist())
    gaps = [plays_idx[i] - plays_idx[i - 1] for i in range(1, len(plays_idx))]
    recent_gaps = gaps[-25:] if len(gaps) >= 25 else gaps
    return pd.Series(
        {
            "times_played": len(plays_idx),
            "last_played_index": plays_idx[-1],
            "last_played_date": group["show_date"].max(),
            "avg_gap": pd.Series(gaps).mean() if gaps else float("nan"),
            "recent_avg_gap": (
                pd.Series(recent_gaps).mean() if recent_gaps else float("nan")
            ),
            "std_gap": pd.Series(gaps).std(ddof=0) if gaps else 0.0,
        }
    )


@dataclass
class ModelData:
    """A container for all data required by prediction models."""

    # A DataFrame of all historical plays before the reference date.
    historical_plays: pd.DataFrame

    # A DataFrame of song features aggregated over their entire history.
    master_feature_set: pd.DataFrame

    # The specific date for which predictions are being generated.
    reference_date: date

    # The chronological index of the reference show.
    reference_index: int

    # A list of songs played in the configured recent-show exclusion window.
    recently_played_songs: List[str]

    # Diagnostic metadata.
    diagnostics: Dict[str, Any]

    # Optional target show metadata used by band-specific feature engineering.
    target_show_context: Dict[str, Any] | None = None


def _compute_base_features(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date: date,
    debug: bool = False,
    exclusion_window: int = 3,
) -> Tuple[pd.DataFrame, pd.DataFrame, int, List[str]]:
    """
    First-pass feature engineering.
    """
    if debug:
        logger.debug("--- Debugging _compute_base_features ---")
        logger.debug("Initial shows_df shape: %s", shows_df.shape)
        logger.debug("Initial setlists_df shape: %s", setlists_df.shape)
        logger.debug("Reference date: %s", reference_date)

    # 1. Set absolute cutoff date
    shows = shows_df.copy()
    shows["show_date"] = pd.to_datetime(shows["show_date"], errors="coerce").dt.date
    historical_shows = shows[shows["show_date"] < reference_date].copy()
    if debug:
        logger.debug(
            "Shape after filtering for historical shows: %s", historical_shows.shape
        )

    if historical_shows.empty:
        return pd.DataFrame(), pd.DataFrame(), 0, []

    # 2. Compute stable show index (normalize keys BEFORE building the index map)
    historical_shows = sort_normalized_shows(historical_shows)

    # Deduplicate by date so gaps count unique show-dates, not show-rows.
    # Bands like UM play multiple shows on the same date; counting each row
    # inflates gaps (e.g. 16 rows after a date but only 8 unique dates).
    date_dedup_idx = historical_shows.drop_duplicates(subset=["show_date"]).reset_index(
        drop=True
    )
    date_dedup_idx["show_index"] = date_dedup_idx.index + 1
    date_to_index = dict(zip(date_dedup_idx["show_date"], date_dedup_idx["show_index"]))
    historical_shows["show_index"] = historical_shows["show_date"].map(date_to_index)
    show_idx_map = dict(
        zip(historical_shows["show_id"], historical_shows["show_index"])
    )

    last_historical_index = historical_shows["show_index"].max()
    reference_index = last_historical_index + 1
    if debug:
        logger.debug("Computed reference_index: %s", reference_index)

    # 3. Merge plays — carry optional set-position columns when present
    setlist_cols = ["show_id", "song_name"]
    for _opt in ["set_number", "song_position", "encore"]:
        if _opt in setlists_df.columns:
            setlist_cols.append(_opt)
    plays = setlists_df[setlist_cols].copy()
    if "set_number" in plays.columns:
        plays["set_number"] = pd.to_numeric(
            plays["set_number"], errors="coerce"
        ).astype("Int64")
    if "song_position" in plays.columns:
        plays["song_position"] = pd.to_numeric(
            plays["song_position"], errors="coerce"
        ).astype("Int64")
    if "encore" in plays.columns:
        plays["encore"] = plays["encore"].fillna(False).astype(bool)
    plays["show_id"] = plays["show_id"].astype(str).str.strip()
    map_keys = set(historical_shows["show_id"].unique())

    if debug:
        logger.debug("First 5 show_ids from historical_shows: %s", list(map_keys)[:5])
        logger.debug(
            "First 5 show_ids from setlists_df: %s", plays["show_id"].unique()[:5]
        )

    plays = plays[plays["show_id"].isin(map_keys)]
    if debug:
        logger.debug("Plays shape after filtering to historical shows: %s", plays.shape)

    plays["show_index"] = plays["show_id"].map(show_idx_map)
    show_context_columns = ["show_id", "show_date"]
    for optional_column in ["tour_name", "venue_name", "city", "state", "country"]:
        if optional_column in historical_shows.columns:
            show_context_columns.append(optional_column)

    plays = plays.merge(
        historical_shows[show_context_columns], on="show_id", how="left"
    )
    if debug:
        logger.debug("Plays shape after merging with show_date: %s", plays.shape)
    plays.dropna(subset=["show_index", "song_name"], inplace=True)
    if debug:
        logger.debug("Plays shape after dropping NA: %s", plays.shape)

    # 4. Calculate historical gap stats
    song_features = (
        plays.groupby("song_name")
        .apply(_stats_for_song, include_groups=False)
        .reset_index()
    )
    if debug:
        logger.debug("Shape of master_feature_set: %s", song_features.shape)

    # 5. Identify recently played songs
    last_n_indices = range(
        max(1, last_historical_index - (exclusion_window - 1)),
        last_historical_index + 1,
    )
    recent_plays_mask = plays["show_index"].isin(last_n_indices)
    recently_played = sorted(set(plays.loc[recent_plays_mask, "song_name"].tolist()))
    if debug:
        logger.debug("--- End Debugging ---")

    return plays, song_features, reference_index, recently_played


def generate_model_data(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date: date,
    debug: bool = False,
    exclusion_window: int | None = None,
    band: str | None = None,
    target_show_context: pd.Series | dict[str, Any] | None = None,
) -> ModelData:
    """
    Orchestrates the full feature generation pipeline.
    """
    required_show_columns = {"show_id", "show_date"}
    required_setlist_columns = {"show_id", "song_name"}
    missing_show_columns = sorted(required_show_columns - set(shows_df.columns))
    missing_setlist_columns = sorted(
        required_setlist_columns - set(setlists_df.columns)
    )
    if missing_show_columns or missing_setlist_columns:
        problems = []
        if missing_show_columns:
            problems.append(f"shows missing {missing_show_columns}")
        if missing_setlist_columns:
            problems.append(f"setlists missing {missing_setlist_columns}")
        raise RuntimeError(
            "generate_model_data requires normalized inputs: " + "; ".join(problems)
        )

    # Honor an explicit caller override first. Fall back to the band/default
    # configuration only when the caller does not pass a value.
    if exclusion_window is None:
        from jambandnerd.config import (
            BAND_EXCLUSION_WINDOWS,
            EXCLUSION_WINDOW_DEFAULT,
        )

        exclusion_window = (
            BAND_EXCLUSION_WINDOWS.get(band, EXCLUSION_WINDOW_DEFAULT)
            if band
            else EXCLUSION_WINDOW_DEFAULT
        )

    historical_plays, master_features, ref_index, recent_songs = _compute_base_features(
        shows_df, setlists_df, reference_date, debug, exclusion_window
    )

    diagnostics = {
        "reference_date": reference_date.isoformat(),
        "reference_index": ref_index,
        "total_songs_in_history": len(master_features),
        "recently_played_count": len(recent_songs),
    }
    normalized_target_context = normalize_target_show_context(target_show_context)
    if normalized_target_context:
        diagnostics["target_show_context"] = {
            key: str(value) for key, value in normalized_target_context.items()
        }

    return ModelData(
        historical_plays=historical_plays,
        master_feature_set=master_features,
        reference_date=reference_date,
        reference_index=ref_index,
        recently_played_songs=recent_songs,
        diagnostics=diagnostics,
        target_show_context=normalized_target_context or None,
    )
