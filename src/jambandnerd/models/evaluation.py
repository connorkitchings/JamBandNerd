"""Shared evaluation helpers for backtests and model comparisons."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from jambandnerd.transformations.normalization import sort_normalized_shows


def get_evaluation_reference_date(target_show_date: date) -> date:
    """Return the conservative reference date used for historical scoring.

    We always score a historical show from the prior calendar day so same-day
    shows and double-headers cannot leak into the feature set.
    """

    return target_show_date - timedelta(days=1)


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

    completed_show_ids = set(setlists_df["show_id"].dropna().astype(str).tolist())
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
