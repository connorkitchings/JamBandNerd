"""Umphrey's McGee fast predictor — based on PhishFastPredictorV2 architecture.

Identical feature set and training approach to PhishFast V2 (16 features,
LightGBM rank_xendcg with early stopping).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from jambandnerd.models.phish.fast_predictor import (
    _LGB_PARAMS,
    PHISH_FAST_V2_FEATURE_COLS,
    PhishFastPredictorV2,
    _window_plays,
)
from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)


class UMFastPredictor(PhishFastPredictorV2):
    """Umphrey's McGee LightGBM predictor using PhishFast V2 architecture.

    16 features: gap, recency windows, career rate, month rate, tour/run
    context, short-window recency, rotation analytics. With early stopping.
    """

    MODEL_VERSION = "um_fast_gbm_v1"

    def __init__(self, band: str = "um", **kwargs: Any) -> None:
        if band != "um":
            raise ValueError("UMFastPredictor only supports band='um'.")
        self.band = band
        self._model = None
        self.best_iteration = None
        self._cache = None
        self.diagnostic_feature_columns = list(PhishFastPredictorV2._FEATURE_COLS)


_UM_V2_LGB_PARAMS: dict[str, Any] = {
    **_LGB_PARAMS,
    "num_leaves": 15,
    "learning_rate": 0.07,
    "reg_lambda": 0.1,
}


class UMFastPredictorV2(UMFastPredictor):
    """UMFast V2 — HP-tuned: leaves=15, lr=0.07, lambda=0.1.

    Combo sweep winner: dual=0.343 (+0.020 vs V1). Lower capacity + L2
    regularization + slightly faster learning rate.
    """

    MODEL_VERSION = "um_fast_gbm_v2"
    _LGB_PARAMS: dict[str, Any] = _UM_V2_LGB_PARAMS


class UMFastPredictorV2Window200(UMFastPredictorV2):
    """UMFast V2 features with 200-show training window (2x the V2 cap)."""

    MODEL_VERSION = "um_fast_gbm_v2_window200"

    def _training_window(self) -> int:
        return 200


class UMFastPredictorV2Window300(UMFastPredictorV2):
    """UMFast V2 features with 300-show training window."""

    MODEL_VERSION = "um_fast_gbm_v2_window300"

    def _training_window(self) -> int:
        return 300


class UMFastPredictorV2FullHistory(UMFastPredictorV2):
    """UMFast V2 features with full-history training (no 100-show cap)."""

    MODEL_VERSION = "um_fast_gbm_v2_full_history"

    def _training_window(self) -> int:
        return 99999


class UMFastPredictorV2NotebookRank(UMFastPredictorV2):
    """UMFast V2 features + notebook_rank_score (Notebook-style heuristic rank).

    Sorts eligible songs by (plays_past_50 DESC, gap_shows DESC, song_name ASC)
    and converts the rank to a normalized score in [0, 1].
    Gave Goose +0.006, Phish +0.014, hurt Billy (-0.074).
    """

    MODEL_VERSION = "um_fast_gbm_v2_notebook_rank"
    _FEATURE_COLS: list[str] = [*PHISH_FAST_V2_FEATURE_COLS, "notebook_rank_score"]

    @staticmethod
    def _notebook_rank_score(
        *,
        eligible_songs: pd.Index,
        plays_past_50: Any,
        gap_e: pd.Series,
    ) -> list[float]:
        frame = pd.DataFrame(
            {
                "song_name": eligible_songs.astype(str).values,
                "plays_past_50": pd.Series(plays_past_50).values,
                "gap_shows": gap_e.values,
            }
        )
        ranked = frame.sort_values(
            by=["plays_past_50", "gap_shows", "song_name"],
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
            plays_past_50=kwargs["p50"],
            gap_e=kwargs["gap_e"],
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra["notebook_rank_score"] = self._notebook_rank_score(
            eligible_songs=kwargs["eligible_songs"],
            plays_past_50=kwargs["p50"],
            gap_e=kwargs["gap_e"],
        )
        return extra


class UMFastPredictorV2VenueRun(UMFastPredictorV2):
    """UMFast V2 features + per-song venue run history.

    Adds same_venue_run_prior_played/count/share for each candidate song.
    UM plays many multi-night runs, so venue-run context may be especially
    valuable for predicting which songs appear in which shows of a run.
    """

    MODEL_VERSION = "um_fast_gbm_v2_venue_run"
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


class UMFastPredictorV2LongRotation(UMFastPredictorV2):
    """UMFast V2 features + longer-window rotation pressure.

    Adds plays_past_100, diff_50_to_100, long_rotation_pressure.
    """

    MODEL_VERSION = "um_fast_gbm_v2_long_rotation"
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
