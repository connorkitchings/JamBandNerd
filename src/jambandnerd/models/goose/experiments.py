"""Goose-specific experiment sweep configs.

Each list defines a sweep of experiments that can be run via
``scripts/run_experiment.py --band goose --sweep hp_sweep``.  The base
predictor for all HP experiments is GooseFastPredictor (15 features,
full-history training).  Feature experiments use explicit subclasses
defined in this module.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from jambandnerd.models.experiment import ExperimentConfig
from jambandnerd.models.goose.ablation import _plays_past_year_array
from jambandnerd.models.goose.fast_predictor import (
    GOOSE_FAST_FEATURE_COLS,
    GooseFastPredictor,
)

# ── HP (hyperparameter) sweep ────────────────────────────────────────────────

GOOSE_HP_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="hp_leaves63_r400",
        description="num_leaves=63, rounds=400 (moderate capacity increase)",
        param_overrides={"num_leaves": 63},
        round_overrides=400,
    ),
    ExperimentConfig(
        slug="hp_leaves127_r400",
        description="num_leaves=127, rounds=400 (aggressive capacity increase)",
        param_overrides={"num_leaves": 127},
        round_overrides=400,
    ),
    ExperimentConfig(
        slug="hp_r400",
        description="rounds=400 only (isolate effect of more boosting rounds)",
        round_overrides=400,
    ),
    ExperimentConfig(
        slug="hp_lr010",
        description="learning_rate=0.10 (higher learning rate)",
        param_overrides={"learning_rate": 0.10},
    ),
    ExperimentConfig(
        slug="hp_lr002_r800",
        description="learning_rate=0.02, rounds=800 (slow burn, more rounds)",
        param_overrides={"learning_rate": 0.02},
        round_overrides=800,
    ),
    ExperimentConfig(
        slug="hp_minleaf10",
        description="min_data_in_leaf=10 (stronger regularization)",
        param_overrides={"min_data_in_leaf": 10},
    ),
]

# ── Feature experiment classes ────────────────────────────────────────────────
#
# Each class extends GooseFastPredictor and overrides
# _feature_frame_for_target to add one or more features.  The experiment
# runner imports them via ExperimentConfig.predictor_path.


class GooseFastPlusPlaysPastYear(GooseFastPredictor):
    """A: Add plays_past_year (distinct shows in trailing 365 days)."""

    MODEL_VERSION = "goose_fast_gbm_v1_feat_ppa"
    _FEATURE_COLS: list[str] = [
        *GOOSE_FAST_FEATURE_COLS,
        "plays_past_year",
    ]

    def _feature_frame_for_target(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        gap_e: pd.Series,
        total_e: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> pd.DataFrame:
        frame = super()._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            target_date=target_date,
            gap_e=gap_e,
            total_e=total_e,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
            target_show_index=target_show_index,
        )
        ppl_1yr, _ = _plays_past_year_array(
            eligible_songs=eligible_songs,
            target_date=target_date,
            plays=plays,
            target_show_index=target_show_index,
        )
        frame["plays_past_year"] = ppl_1yr
        return frame


class GooseFastPlusNotebookRank(GooseFastPlusPlaysPastYear):
    """B: Add notebook_rank_score (Normalized Notebook-style ranking)."""

    MODEL_VERSION = "goose_fast_gbm_v1_feat_nb_rank"
    _FEATURE_COLS: list[str] = [
        *GooseFastPlusPlaysPastYear._FEATURE_COLS,
        "notebook_rank_score",
    ]

    def _feature_frame_for_target(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        gap_e: pd.Series,
        total_e: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> pd.DataFrame:
        frame = super()._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            target_date=target_date,
            gap_e=gap_e,
            total_e=total_e,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
            target_show_index=target_show_index,
        )
        ranked = frame.sort_values(
            by=["plays_past_year", "current_gap", "song_name"],
            ascending=[False, False, True],
        )
        n = len(ranked)
        if n <= 1:
            frame["notebook_rank_score"] = 1.0
        else:
            rank_scores = {
                str(row["song_name"]): 1.0 - (rank / (n - 1))
                for rank, (_, row) in enumerate(ranked.iterrows())
            }
            frame["notebook_rank_score"] = (
                frame["song_name"]
                .astype(str)
                .map(rank_scores)
                .fillna(0.0)
                .to_numpy(dtype=float)
            )
        return frame


class GooseFastPlusTourFatigue(GooseFastPlusNotebookRank):
    """C: Add tour_fatigue and run_pressure interaction features."""

    MODEL_VERSION = "goose_fast_gbm_v1_feat_tour_fatigue"
    _FEATURE_COLS: list[str] = [
        *GooseFastPlusNotebookRank._FEATURE_COLS,
        "tour_fatigue",
        "run_pressure",
    ]

    def _feature_frame_for_target(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        gap_e: pd.Series,
        total_e: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> pd.DataFrame:
        frame = super()._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            target_date=target_date,
            gap_e=gap_e,
            total_e=total_e,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
            target_show_index=target_show_index,
        )
        frame["tour_fatigue"] = frame["tour_position"] * frame["career_play_pct"]
        frame["run_pressure"] = frame["show_position_in_run"] * frame["avg_ltp_recent"]
        return frame


# ── Feature experiment sweep ─────────────────────────────────────────────────

GOOSE_FEATURE_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="feat_plays_past_year",
        description="Add plays_past_year (Notebook's primary feature) to 15-feature set",
        predictor_path="jambandnerd.models.goose.experiments.GooseFastPlusPlaysPastYear",
    ),
    ExperimentConfig(
        slug="feat_notebook_rank",
        description="Add notebook_rank_score (full Notebook ranking as a feature)",
        predictor_path="jambandnerd.models.goose.experiments.GooseFastPlusNotebookRank",
    ),
    ExperimentConfig(
        slug="feat_tour_fatigue",
        description="Add tour_fatigue and run_pressure interaction features",
        predictor_path="jambandnerd.models.goose.experiments.GooseFastPlusTourFatigue",
    ),
]

# ── Full sweep index ─────────────────────────────────────────────────────────

GOOSE_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "hp_sweep": GOOSE_HP_SWEEP,
    "feature_sweep": GOOSE_FEATURE_SWEEP,
}
