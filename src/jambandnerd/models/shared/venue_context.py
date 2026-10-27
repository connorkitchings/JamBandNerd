"""Same-venue-run context shared by training and prediction paths.

Training and prediction must build the target show's venue key from the same
fields (venue, city, state, country); otherwise the ``same_venue_run_position``
feature means different things at fit time and at inference time.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)


def training_target_show_context(
    plays: pd.DataFrame, target_show_index: int
) -> dict[str, Any]:
    """Full venue/location context of a historical target show, from its row."""
    target_rows = plays[plays["show_index"] == target_show_index]
    if target_rows.empty:
        return {}
    return normalize_target_show_context(target_rows.iloc[0])


def same_venue_run_position(
    prior_plays: pd.DataFrame, target_show_context: dict[str, Any] | None
) -> float:
    """1-based position of the target show in its same-venue run (0.0 if unknown).

    ``prior_plays`` must contain only shows before the target.
    """
    normalized = normalize_target_show_context(target_show_context or {})
    if not normalized_venue_key(normalized):
        return 0.0
    return float(len(same_venue_run_show_indices(prior_plays, normalized)) + 1)
