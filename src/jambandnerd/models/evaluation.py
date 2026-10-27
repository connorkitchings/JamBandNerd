"""Shared evaluation helpers for backtests and model comparisons."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from jambandnerd.transformations.gaps import ModelData, generate_model_data
from jambandnerd.transformations.normalization import sort_normalized_shows


def get_evaluation_reference_date(target_show_date: date) -> date:
    """Return the label stored as ``reference_date`` on historical scoring rows.

    This is a lineage label only (the night before the target show, matching
    the live path's "as of" date). It is NOT the feature cutoff: build features
    with ``build_model_data_for_target`` so the previous night's show is kept.
    """

    return target_show_date - timedelta(days=1)


def build_model_data_for_target(
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    target_show_date: date,
    *,
    band: str,
    target_show_context: pd.Series | dict | None = None,
    exclusion_window: int | None = None,
) -> ModelData:
    """Build features for scoring one historical show.

    ``generate_model_data`` keeps only shows strictly before its reference
    date, so passing the target show's own date includes every earlier show
    (including the previous night) and excludes the target itself. This is the
    single place that defines the historical evaluation cutoff.
    """

    return generate_model_data(
        shows_df,
        sets_df,
        target_show_date,
        exclusion_window=exclusion_window,
        band=band,
        target_show_context=target_show_context,
    )


def list_completed_shows(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return completed shows in canonical historical order.

    Args:
        shows_df: DataFrame containing all shows for a band.
        setlists_df: DataFrame containing raw setlists.

    Returns:
        A sorted DataFrame of shows that have corresponding setlist data.
    """

    song_counts = (
        setlists_df.dropna(subset=["show_id", "song_name"])
        .assign(show_id=lambda df: df["show_id"].astype(str))
        .groupby("show_id")["song_name"]
        .nunique()
    )
    completed_show_ids = set(song_counts[song_counts > 2].index.tolist())
    return sort_normalized_shows(
        shows_df[shows_df["show_id"].astype(str).isin(completed_show_ids)].copy()
    )


def select_target_shows(
    completed_shows: pd.DataFrame,
    *,
    start: str | None = None,
    end: str | None = None,
    shows: int | None = None,
    all_history: bool = False,
) -> pd.DataFrame:
    """Select the target completed-show window for a scoring run.

    Args:
        completed_shows: DataFrame of completed shows.
        start: Optional start date string (YYYY-MM-DD).
        end: Optional end date string (YYYY-MM-DD).
        shows: Optional number of most recent shows to select.
        all_history: If True, select all available shows.

    Returns:
        A DataFrame containing the subset of target shows.
    """

    if completed_shows.empty:
        return completed_shows.copy()

    if all_history:
        return completed_shows.copy()

    if shows and shows > 0:
        return completed_shows.tail(shows).copy()

    start_d = pd.to_datetime(start).date() if start else None
    end_d = pd.to_datetime(end).date() if end else None

    window = completed_shows.copy()
    if start_d is not None:
        window = window[window["show_date"] >= start_d]
    if end_d is not None:
        window = window[window["show_date"] <= end_d]
    return window.copy()
