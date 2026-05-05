"""Phish-specific experiment sweep configs.

These sweeps treat ``PhishFastPredictorV2`` as the current incumbent and test
small, isolated changes before any registry promotion.  Run with:

``uv run python scripts/run_experiment.py --band phish --sweep feature_sweep``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from jambandnerd.models.experiment import ExperimentConfig
from jambandnerd.models.phish.fast_predictor import (
    PHISH_FAST_V2_FEATURE_COLS,
    PhishFastPredictorV2,
    _window_plays,
    _window_plays_by_days,
)
from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)

PHISH_HP_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="hp_minleaf10",
        description="min_data_in_leaf=10 (stronger regularization around V2)",
        param_overrides={"min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="hp_minleaf20",
        description="min_data_in_leaf=20 (heavier regularization around V2)",
        param_overrides={"min_data_in_leaf": 20},
    ),
    ExperimentConfig(
        slug="hp_leaves15",
        description="num_leaves=15 (lower capacity, reduce overfit risk)",
        param_overrides={"num_leaves": 15},
    ),
    ExperimentConfig(
        slug="hp_lr003_r700",
        description="learning_rate=0.03, rounds=700 (slower V2 variant)",
        param_overrides={"learning_rate": 0.03},
        round_overrides=700,
    ),
]


class PhishFastPlusPlaysPastYear(PhishFastPredictorV2):
    """Add Notebook's trailing-year play count as a direct feature."""

    MODEL_VERSION = "phish_fast_gbm_v2_feat_plays_past_year"
    _FEATURE_COLS: list[str] = [
        *PHISH_FAST_V2_FEATURE_COLS,
        "plays_past_year",
    ]

    def _extra_training_row_features(
        self,
        *,
        eligible_songs: pd.Index,
        j: int,
        target_date: Any,
        gap_e: pd.Series,
        career_pct: pd.Series,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
        target_show_index: int,
    ) -> dict:
        extra = super()._extra_training_row_features(
            eligible_songs=eligible_songs,
            j=j,
            target_date=target_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_index=target_show_index,
        )
        ref_col = j - 1
        extra["plays_past_year"] = (
            _window_plays_by_days(
                plays,
                cache["presence"],
                ref_col,
                365,
                cache["col_dates"],
            )
            .loc[eligible_songs]
            .values
        )
        return extra

    def _extra_predict_features(
        self,
        *,
        eligible_songs: pd.Index,
        n_shows: int,
        ref_date: pd.Timestamp,
        gap_e: pd.Series,
        career_pct: pd.Series,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
        target_show_context: Any,
    ) -> dict:
        extra = super()._extra_predict_features(
            eligible_songs=eligible_songs,
            n_shows=n_shows,
            ref_date=ref_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
        )
        ref_col = n_shows - 1
        extra["plays_past_year"] = (
            _window_plays_by_days(
                plays,
                cache["presence"],
                ref_col,
                365,
                cache["col_dates"],
            )
            .loc[eligible_songs]
            .values
        )
        return extra


class PhishFastPlusNotebookRank(PhishFastPlusPlaysPastYear):
    """Add normalized Notebook-style rank score over the candidate set."""

    MODEL_VERSION = "phish_fast_gbm_v2_feat_notebook_rank"
    _FEATURE_COLS: list[str] = [
        *PhishFastPlusPlaysPastYear._FEATURE_COLS,
        "notebook_rank_score",
    ]

    @staticmethod
    def _notebook_rank_score(
        *,
        eligible_songs: pd.Index,
        plays_past_year: Any,
        gap_e: pd.Series,
    ) -> list[float]:
        frame = pd.DataFrame(
            {
                "song_name": eligible_songs.astype(str),
                "plays_past_year": plays_past_year,
                "gap_shows": gap_e.values,
            }
        )
        ranked = frame.sort_values(
            by=["plays_past_year", "gap_shows", "song_name"],
            ascending=[False, False, True],
        )
        n = len(ranked)
        if n <= 1:
            return [1.0] * n

        scores = {
            str(row["song_name"]): 1.0 - (rank / (n - 1))
            for rank, (_, row) in enumerate(ranked.iterrows())
        }
        return [
            float(scores.get(str(song), 0.0)) for song in eligible_songs.astype(str)
        ]

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        extra["notebook_rank_score"] = self._notebook_rank_score(
            eligible_songs=kwargs["eligible_songs"],
            plays_past_year=extra["plays_past_year"],
            gap_e=kwargs["gap_e"],
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra["notebook_rank_score"] = self._notebook_rank_score(
            eligible_songs=kwargs["eligible_songs"],
            plays_past_year=extra["plays_past_year"],
            gap_e=kwargs["gap_e"],
        )
        return extra


class PhishFastPlusLongRotation(PhishFastPredictorV2):
    """Add longer-window rotation pressure beyond V2's short/medium windows."""

    MODEL_VERSION = "phish_fast_gbm_v2_feat_long_rotation"
    _FEATURE_COLS: list[str] = [
        *PHISH_FAST_V2_FEATURE_COLS,
        "plays_past_100",
        "diff_50_to_100",
        "long_rotation_pressure",
    ]

    def _rotation_features(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        p50: pd.Series,
        gap_e: pd.Series,
        cache: dict,
    ) -> dict[str, Any]:
        p100 = _window_plays(cache["cum"], upper_col, 100).loc[eligible_songs]
        pct50 = p50 / max(1, min(50, upper_col))
        pct100 = p100 / max(1, min(100, upper_col))
        return {
            "plays_past_100": p100.values,
            "diff_50_to_100": (pct50 - pct100).values,
            "long_rotation_pressure": (gap_e * pct100.clip(lower=0.01)).values,
        }

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        extra.update(
            self._rotation_features(
                eligible_songs=kwargs["eligible_songs"],
                upper_col=kwargs["j"],
                p50=kwargs["p50"],
                gap_e=kwargs["gap_e"],
                cache=kwargs["cache"],
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            self._rotation_features(
                eligible_songs=kwargs["eligible_songs"],
                upper_col=kwargs["n_shows"],
                p50=kwargs["p50"],
                gap_e=kwargs["gap_e"],
                cache=kwargs["cache"],
            )
        )
        return extra


class PhishFastPlusVenueRun(PhishFastPredictorV2):
    """Add same-venue run history as per-song candidate features."""

    MODEL_VERSION = "phish_fast_gbm_v2_feat_venue_run"
    _FEATURE_COLS: list[str] = [
        *PHISH_FAST_V2_FEATURE_COLS,
        "same_venue_run_prior_played",
        "same_venue_run_prior_play_count",
        "same_venue_run_prior_play_share",
    ]

    @staticmethod
    def _venue_run_features(
        *,
        eligible_songs: pd.Index,
        plays: pd.DataFrame,
        target_show_context: Any,
    ) -> dict[str, Any]:
        normalized_ctx = normalize_target_show_context(target_show_context)
        if normalized_venue_key(normalized_ctx):
            same_run_indices = same_venue_run_show_indices(plays, normalized_ctx)
        else:
            same_run_indices = []

        if not same_run_indices:
            zeros = pd.Series(0.0, index=eligible_songs)
            return {
                "same_venue_run_prior_played": zeros.values,
                "same_venue_run_prior_play_count": zeros.values,
                "same_venue_run_prior_play_share": zeros.values,
            }

        counts = (
            plays[plays["show_index"].isin(same_run_indices)]
            .groupby("song_name")["show_index"]
            .nunique()
            .reindex(eligible_songs, fill_value=0)
            .astype(float)
        )
        return {
            "same_venue_run_prior_played": (counts > 0).astype(float).values,
            "same_venue_run_prior_play_count": counts.values,
            "same_venue_run_prior_play_share": (counts / len(same_run_indices)).values,
        }

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        target_show_index = kwargs["target_show_index"]
        sub_plays = kwargs["plays"][kwargs["plays"]["show_index"] < target_show_index]
        target_rows = kwargs["plays"][
            kwargs["plays"]["show_index"] == target_show_index
        ]
        target_context = target_rows.iloc[0] if not target_rows.empty else {}
        extra.update(
            self._venue_run_features(
                eligible_songs=kwargs["eligible_songs"],
                plays=sub_plays,
                target_show_context=target_context,
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            self._venue_run_features(
                eligible_songs=kwargs["eligible_songs"],
                plays=kwargs["plays"],
                target_show_context=kwargs["target_show_context"],
            )
        )
        return extra


class PhishFastPlusNotebookRankVenueRun(PhishFastPlusNotebookRank):
    """Stack notebook_rank + venue_run features on top of PhishFast V2."""

    MODEL_VERSION = "phish_fast_gbm_v2_feat_notebook_rank_venue_run"
    _FEATURE_COLS: list[str] = [
        *PhishFastPlusNotebookRank._FEATURE_COLS,
        "same_venue_run_prior_played",
        "same_venue_run_prior_play_count",
        "same_venue_run_prior_play_share",
    ]

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        target_show_index = kwargs["target_show_index"]
        sub_plays = kwargs["plays"][kwargs["plays"]["show_index"] < target_show_index]
        target_rows = kwargs["plays"][
            kwargs["plays"]["show_index"] == target_show_index
        ]
        target_context = target_rows.iloc[0] if not target_rows.empty else {}
        extra.update(
            PhishFastPlusVenueRun._venue_run_features(
                eligible_songs=kwargs["eligible_songs"],
                plays=sub_plays,
                target_show_context=target_context,
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            PhishFastPlusVenueRun._venue_run_features(
                eligible_songs=kwargs["eligible_songs"],
                plays=kwargs["plays"],
                target_show_context=kwargs["target_show_context"],
            )
        )
        return extra


PHISH_FEATURE_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="feat_plays_past_year",
        description="Add plays_past_year, Notebook's main recency signal",
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusPlaysPastYear",
    ),
    ExperimentConfig(
        slug="feat_notebook_rank",
        description="Add normalized Notebook-style rank score",
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRank",
    ),
    ExperimentConfig(
        slug="feat_long_rotation",
        description="Add plays_past_100 and longer-window rotation pressure",
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusLongRotation",
    ),
    ExperimentConfig(
        slug="feat_venue_run",
        description="Add same-venue run prior-play candidate features",
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusVenueRun",
    ),
    ExperimentConfig(
        slug="feat_notebook_rank_venue_run",
        description="Stack notebook_rank + venue_run features",
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
    ),
]


PHISH_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "hp_sweep": PHISH_HP_SWEEP,
    "feature_sweep": PHISH_FEATURE_SWEEP,
}
