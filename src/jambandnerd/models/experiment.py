"""Band-agnostic experimentation framework.

Provides a factory for creating experiment predictor subclasses and a
dataclass for collecting per-experiment backtest results. Per-band experiment
configs live in {band}/experiments.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jambandnerd.models.base import PredictionModel


def make_experiment_predictor(
    base_cls: type[PredictionModel],
    *,
    slug_suffix: str,
    param_overrides: dict[str, Any] | None = None,
    round_overrides: int | None = None,
    feature_cols: list[str] | None = None,
) -> type[PredictionModel]:
    """Create an ephemeral predictor subclass for a single experiment.

    ``param_overrides`` keys are merged into the base class's ``_LGB_PARAMS``
    dict.  ``round_overrides`` replaces ``_LGB_ROUNDS``.  ``feature_cols``
    replaces ``_FEATURE_COLS``.  ``MODEL_VERSION`` is set to
    ``{base.MODEL_VERSION}_{slug_suffix}``.

    Returns a new class that can be passed directly to
    ``run_phase_b_backtest(predictor_class=...)``.
    """
    overrides: dict[str, Any] = {}
    overrides["MODEL_VERSION"] = f"{base_cls.MODEL_VERSION}_{slug_suffix}"

    if param_overrides:
        base_params = dict(getattr(base_cls, "_LGB_PARAMS", {}))
        merged = {**base_params, **param_overrides}
        overrides["_LGB_PARAMS"] = merged
    if round_overrides is not None:
        overrides["_LGB_ROUNDS"] = round_overrides
    if feature_cols is not None:
        overrides["_FEATURE_COLS"] = list(feature_cols)

    name = f"{base_cls.__name__}_{slug_suffix}"
    return type(name, (base_cls,), overrides)


@dataclass
class ExperimentConfig:
    """Describes one experiment in a per-band sweep.

    When ``predictor_path`` is set, the class at that dotted path is used
    directly (no ``make_experiment_predictor`` wrapper).  Use this for
    feature experiments that require custom ``_feature_frame_for_target``
    overrides.  Otherwise ``base_predictor_path`` + overrides are used.
    """

    slug: str
    description: str = ""
    base_predictor_path: str = ""
    predictor_path: str = ""
    param_overrides: dict[str, Any] = field(default_factory=dict)
    round_overrides: int | None = None
    feature_cols: list[str] | None = None


@dataclass
class SweepResult:
    """Per-experiment backtest metrics."""

    slug: str
    model_version: str
    dual_score: float
    p10: float
    p25: float
    r50: float
    f1_25: float
    dual_f1_score: float
    n_shows: int
    summary_path: str = ""
    elapsed_s: float = 0.0
