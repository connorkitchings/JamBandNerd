"""Goose feature-distillation predictor.

Lean logistic model that accepts named feature families at init so we can
isolate which families beat Notebook and which degrade ranking quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jambandnerd.models.deal.model import DealPredictor
from jambandnerd.transformations.cooccurrence import (
    COOCCURRENCE_FEATURES as _COOCCURRENCE_FEATURES,
)
from jambandnerd.transformations.set_position import (
    SET_POSITION_FEATURES as _SET_POSITION_FEATURES,
)

_FAMILY_NOTEBOOK: list[str] = ["current_gap", "plays_past_year"]

_FAMILY_GAP: list[str] = [
    "avg_ltp",
    "recent_avg_ltp",
    "overdue_metric",
    "gap_z_score",
]

_FAMILY_RECENCY: list[str] = [
    "plays_past_2yr",
    "pct_shows_6mo",
    "pct_shows_1yr",
    "diff_6mo_to_1yr",
]

_FAMILY_VENUE: list[str] = [
    "n_shows_same_venue",
    "n_shows_same_state",
]

_FAMILY_DEBUT: list[str] = [
    "debut_age_shows",
    "career_play_pct",
    "novelty_rank",
]

_FAMILY_SET_POSITION: list[str] = list(_SET_POSITION_FEATURES)

_FAMILY_COOCCURRENCE: list[str] = list(_COOCCURRENCE_FEATURES)

_FAMILY_GOOSE_EXTRAS: list[str] = [
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
]

_FAMILIES: dict[str, list[str]] = {
    "notebook": _FAMILY_NOTEBOOK,
    "gap": _FAMILY_GAP,
    "recency": _FAMILY_RECENCY,
    "venue": _FAMILY_VENUE,
    "debut": _FAMILY_DEBUT,
    "set_position": _FAMILY_SET_POSITION,
    "cooccurrence": _FAMILY_COOCCURRENCE,
    "goose_extras": _FAMILY_GOOSE_EXTRAS,
}


def _build_feature_columns(
    families: tuple[str, ...],
) -> list[str]:
    """Compose a deterministic feature column list from named families."""
    seen: set[str] = set()
    columns: list[str] = []
    for family in families:
        if family not in _FAMILIES:
            raise ValueError(
                f"Unknown feature family: {family}. "
                f"Available: {sorted(_FAMILIES)}"
            )
        for col in _FAMILIES[family]:
            if col not in seen:
                seen.add(col)
                columns.append(col)
    return columns


class GooseDistilledPredictor(DealPredictor):
    """Goose feature-distillation logistic predictor.

    Accepts a tuple of feature family names at init.  Only the columns from
    those families enter the logistic model — the Deal compute path still
    materialises the full feature set under the hood so backtest times are
    similar, but the model itself is constrained to the specified families.

    Families are additive and applied in the order given.
    """

    MODEL_DIR = Path("models/goose/distilled")
    _SELECTED_FAMILIES: tuple[str, ...] = ("notebook",)

    def __init__(
        self,
        band: str = "goose",
        *,
        families: tuple[str, ...] | None = None,
        **kwargs: Any,
    ) -> None:
        if band != "goose":
            raise ValueError("GooseDistilledPredictor only supports band='goose'.")

        resolved = tuple(families) if families is not None else self._SELECTED_FAMILIES
        if not resolved:
            raise ValueError("At least one feature family is required.")

        feature_columns = _build_feature_columns(resolved)

        defaults: dict[str, Any] = {
            "min_plays_threshold": 3,
            "retired_gap_threshold": 90,
            "training_window_shows": 60,
            "min_training_shows": 20,
            "positive_weight_cap": 2.0,
            "feature_columns": feature_columns,
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)

        self._selected_families = resolved

    @property
    def selected_families(self) -> tuple[str, ...]:
        return self._selected_families

    @property
    def MODEL_VERSION(self) -> str:  # type: ignore[override]
        return f"goose_distilled_{'_'.join(self._selected_families)}"

    def _get_model_path(self, band: str) -> Path:
        return self.MODEL_DIR / f"{band}_{self.MODEL_VERSION}.json"


# ── Convenience subclasses for backtest screening ────────────────────────────
# Each variant uses a fixed _SELECTED_FAMILIES so the backtest script can
# instantiate it without passing --predictor-kwargs.


class GooseDistilledNotebookPredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = ("notebook",)


class GooseDistilledNotebookGapPredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = ("notebook", "gap")


class GooseDistilledNotebookGapRecencyPredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = ("notebook", "gap", "recency")


class GooseDistilledNotebookGapRecencyDebutPredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = (
        "notebook",
        "gap",
        "recency",
        "debut",
    )


class GooseDistilledFullBasePredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = (
        "notebook",
        "gap",
        "recency",
        "debut",
        "set_position",
        "venue",
    )


class GooseDistilledNoVenuePredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = (
        "notebook",
        "gap",
        "recency",
        "debut",
        "set_position",
    )


class GooseDistilledFullBaseCoocPredictor(GooseDistilledPredictor):
    _SELECTED_FAMILIES: tuple[str, ...] = (
        "notebook",
        "gap",
        "recency",
        "debut",
        "set_position",
        "venue",
        "cooccurrence",
    )
