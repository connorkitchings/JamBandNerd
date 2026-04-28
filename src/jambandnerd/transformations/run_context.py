"""Show-run context helpers for prediction features."""

from __future__ import annotations

from typing import Any

import pandas as pd

TARGET_SHOW_CONTEXT_KEYS: tuple[str, ...] = (
    "show_id",
    "show_date",
    "venue_name",
    "city",
    "state",
    "country",
)


def normalize_target_show_context(
    row: pd.Series | dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the prediction-safe target show context keys from a row."""
    if row is None:
        return {}

    context: dict[str, Any] = {}
    for key in TARGET_SHOW_CONTEXT_KEYS:
        if isinstance(row, pd.Series):
            value = row.get(key)
        else:
            value = row.get(key)
        if pd.isna(value):
            value = None
        if value is not None:
            context[key] = value
    return context


def normalized_venue_key(row: pd.Series | dict[str, Any] | None) -> str:
    """Build a stable venue key from available venue and location context."""
    if row is None:
        return ""

    parts: list[str] = []
    for key in ("venue_name", "city", "state", "country"):
        value = row.get(key) if isinstance(row, dict) else row.get(key)
        if value is None or pd.isna(value):
            continue
        text = str(value).strip().lower()
        if text:
            parts.append(text)
    return "|".join(parts)


def same_venue_run_show_indices(
    historical_plays: pd.DataFrame,
    target_show_context: dict[str, Any] | None,
) -> list[int]:
    """Return prior show indices in the current same-venue run.

    The run is sequence-based, not date-based: a same-venue show counts if it is
    directly adjacent to the target in completed-show order, or if exactly one
    other completed show sits between same-venue appearances. The chain stops
    once more than one intervening non-matching venue show appears.
    """
    target_key = normalized_venue_key(target_show_context)
    if not target_key or historical_plays.empty:
        return []

    required = {"show_index", "venue_name"}
    if not required.issubset(historical_plays.columns):
        return []

    show_context_columns = [
        column
        for column in ("show_index", "venue_name", "city", "state", "country")
        if column in historical_plays.columns
    ]
    shows = (
        historical_plays[show_context_columns]
        .dropna(subset=["show_index"])
        .drop_duplicates(subset=["show_index"])
        .sort_values("show_index", ascending=False)
    )
    if shows.empty:
        return []

    run_indices: list[int] = []
    intervening_non_matches = 0
    for _, row in shows.iterrows():
        if normalized_venue_key(row) == target_key:
            run_indices.append(int(row["show_index"]))
            intervening_non_matches = 0
            continue

        intervening_non_matches += 1
        if intervening_non_matches > 1:
            break

    return run_indices
