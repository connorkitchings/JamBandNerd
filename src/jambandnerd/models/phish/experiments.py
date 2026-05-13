"""Phish-specific experiment sweep configs.

These sweeps treat ``PhishFastPlusNotebookRankVenueRun`` as the current incumbent
and test small, isolated changes before any registry promotion. Run with:

``uv run python scripts/run_experiment.py --band phish --sweep feature_sweep``.
"""

from __future__ import annotations

from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from jambandnerd.models.experiment import ExperimentConfig
from jambandnerd.models.phish.fast_predictor import (
    _LGB_PARAMS,
    _LGB_ROUNDS,
    PHISH_FAST_V2_FEATURE_COLS,
    PhishFastPredictor,
    PhishFastPredictorV2,
    _run_position,
    _tour_position,
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


_FESTIVAL_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "festival",
    "fest",
    "mondegreen",
    "mexico",
    "woodlands",
)
_ATYPICAL_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "acoustic",
    "soundcheck",
    "tiny desk",
    "npr",
)
_SHORT_SHOW_THRESHOLD = 12
_TYPICAL_PHISH_SONG_COUNT = 18.0


def _lower_context_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _context_contains(context: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    text = " ".join(
        _lower_context_text(context.get(key))
        for key in ("tour_name", "venue_name", "city", "state", "country")
    )
    return any(keyword in text for keyword in keywords)


def _prior_show_counts(plays: pd.DataFrame) -> pd.Series:
    if plays.empty:
        return pd.Series(dtype=float)
    return plays.groupby("show_index")["song_name"].nunique().sort_index().astype(float)


def _prior_venue_short_show_rate(
    *,
    plays: pd.DataFrame,
    target_show_context: dict[str, Any],
) -> float:
    venue_key = normalized_venue_key(target_show_context)
    if not venue_key or plays.empty:
        return 0.0

    show_context_columns = [
        column
        for column in ("show_index", "venue_name", "city", "state", "country")
        if column in plays.columns
    ]
    if (
        "show_index" not in show_context_columns
        or "venue_name" not in show_context_columns
    ):
        return 0.0

    show_context = (
        plays[show_context_columns]
        .drop_duplicates("show_index")
        .set_index("show_index")
    )
    matching_show_indices = [
        idx
        for idx, row in show_context.iterrows()
        if normalized_venue_key(row) == venue_key
    ]
    if not matching_show_indices:
        return 0.0

    counts = _prior_show_counts(plays).reindex(matching_show_indices).dropna()
    if counts.empty:
        return 0.0
    return float((counts <= _SHORT_SHOW_THRESHOLD).mean())


def _prior_tour_song_count_ratio(
    *,
    plays: pd.DataFrame,
    target_show_context: dict[str, Any],
) -> float:
    tour_name = _lower_context_text(target_show_context.get("tour_name"))
    if not tour_name or plays.empty or "tour_name" not in plays.columns:
        return 1.0

    show_context = (
        plays[["show_index", "tour_name"]]
        .drop_duplicates("show_index")
        .set_index("show_index")
    )
    matching_show_indices = [
        idx
        for idx, row in show_context.iterrows()
        if _lower_context_text(row.get("tour_name")) == tour_name
    ]
    counts = _prior_show_counts(plays).reindex(matching_show_indices).dropna()
    if counts.empty:
        return 1.0
    return float(np.clip(counts.median() / _TYPICAL_PHISH_SONG_COUNT, 0.25, 1.5))


class PhishFastPlusShowType(PhishFastPlusNotebookRankVenueRun):
    """Add Phish show-type context interactions to the incumbent model.

    The raw show-type indicators are intentionally paired with song-level signals
    so the ranker can change candidate ordering within a target show.
    """

    MODEL_VERSION = "phish_fast_gbm_v2_feat_show_type"
    _FEATURE_COLS: list[str] = [
        *PhishFastPlusNotebookRankVenueRun._FEATURE_COLS,
        "is_not_part_of_tour",
        "is_festival_context",
        "is_atypical_context",
        "prior_venue_short_show_rate",
        "prior_tour_song_count_ratio",
        "show_type_notebook_score",
        "show_type_career_score",
        "show_type_recent_score",
        "short_venue_notebook_score",
        "short_venue_career_score",
    ]

    @staticmethod
    def _show_type_features(
        *,
        eligible_songs: pd.Index,
        plays: pd.DataFrame,
        target_show_context: Any,
        career_pct: pd.Series,
        p50: pd.Series,
        notebook_rank_score: Any,
    ) -> dict[str, Any]:
        context = normalize_target_show_context(target_show_context)
        tour_name = _lower_context_text(context.get("tour_name"))
        is_not_part = float(tour_name == "not part of a tour")
        is_festival = float(_context_contains(context, _FESTIVAL_CONTEXT_KEYWORDS))
        is_atypical = float(_context_contains(context, _ATYPICAL_CONTEXT_KEYWORDS))
        short_venue_rate = _prior_venue_short_show_rate(
            plays=plays,
            target_show_context=context,
        )
        tour_count_ratio = _prior_tour_song_count_ratio(
            plays=plays,
            target_show_context=context,
        )
        context_score = max(
            is_not_part,
            is_festival,
            is_atypical,
            short_venue_rate,
            max(0.0, 1.0 - tour_count_ratio),
        )
        notebook = pd.Series(notebook_rank_score, index=eligible_songs).astype(float)
        recent_pct = p50.astype(float) / max(1.0, float(p50.max() or 1.0))

        zeros_or_const = pd.Series(1.0, index=eligible_songs)
        return {
            "is_not_part_of_tour": (zeros_or_const * is_not_part).values,
            "is_festival_context": (zeros_or_const * is_festival).values,
            "is_atypical_context": (zeros_or_const * is_atypical).values,
            "prior_venue_short_show_rate": (zeros_or_const * short_venue_rate).values,
            "prior_tour_song_count_ratio": (zeros_or_const * tour_count_ratio).values,
            "show_type_notebook_score": (notebook * context_score).values,
            "show_type_career_score": (career_pct * context_score).values,
            "show_type_recent_score": (recent_pct * context_score).values,
            "short_venue_notebook_score": (notebook * short_venue_rate).values,
            "short_venue_career_score": (career_pct * short_venue_rate).values,
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
            self._show_type_features(
                eligible_songs=kwargs["eligible_songs"],
                plays=sub_plays,
                target_show_context=target_context,
                career_pct=kwargs["career_pct"],
                p50=kwargs["p50"],
                notebook_rank_score=extra["notebook_rank_score"],
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            self._show_type_features(
                eligible_songs=kwargs["eligible_songs"],
                plays=kwargs["plays"],
                target_show_context=kwargs["target_show_context"],
                career_pct=kwargs["career_pct"],
                p50=kwargs["p50"],
                notebook_rank_score=extra["notebook_rank_score"],
            )
        )
        return extra


# ── PhishFastPredictorV3 (Cleaned Feature Set) ────────────────────────────────


PHISH_FAST_V3_FEATURE_COLS: list[str] = [
    "gap_shows",
    "plays_past_25",
    "plays_past_50",
    "plays_past_2yr",
    "career_play_pct",
    "tour_position",
    "diff_25_to_50",
    "show_position_in_run",
    "same_venue_run_position",
]


class PhishFastPredictorV3(PhishFastPredictor):
    """PhishFast V3 — cleaned feature set based on diagnostics.

    Removes 5 underperforming features identified in Session 05 diagnostics:
    - plays_past_10 (53.7% zero, negative monotonicity)
    - month_play_rate (zero label correlation)
    - same_venue_run_prior_played (93% zero, zero gain)
    - same_venue_run_prior_play_count (93% zero, zero gain)
    - same_venue_run_prior_play_share (93% zero, zero gain)

    Retains 9 high-value features with strong monotonicity and gain.
    Total: 9 features (down from 14 in incumbent).
    """

    MODEL_VERSION = "phish_fast_gbm_v3"
    _FEATURE_COLS: list[str] = PHISH_FAST_V3_FEATURE_COLS
    _LGB_PARAMS: dict[str, Any] = _LGB_PARAMS
    _LGB_ROUNDS: int = _LGB_ROUNDS
    _EARLY_STOPPING_ROUNDS: int | None = None

    def __init__(
        self,
        band: str = "phish",
        **kwargs: Any,
    ) -> None:
        if band != "phish":
            raise ValueError("PhishFastPredictorV3 only supports band='phish'.")
        self.band = band
        self._model: lgb.Booster | None = None
        self.best_iteration: int | None = None
        self._cache: dict | None = None
        self.diagnostic_feature_columns = list(PHISH_FAST_V3_FEATURE_COLS)

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
        col_dates = cache["col_dates"]
        col_venues = cache["col_venues"]

        prior_dates = [d for d in col_dates[:j] if d is not None]
        if target_date is None:
            tour_pos = 1.0
            run_pos = 1.0
        else:
            tour_pos = float(_tour_position(prior_dates, target_date, tour_gap_days=14))
            run_pos = float(_run_position(prior_dates, target_date, gap_days=1))

        pct25 = p25 / max(1, min(25, j))
        pct50 = p50 / max(1, min(50, j))
        diff = (pct25 - pct50).values

        target_venue = col_venues[j] if j < len(col_venues) else None
        if target_venue:
            target_context = normalize_target_show_context({"venue_name": target_venue})
            if normalized_venue_key(target_context):
                sub_plays = plays[plays["show_index"] < target_show_index]
                same_run_indices = same_venue_run_show_indices(
                    sub_plays, target_context
                )
                same_run_position = float(len(same_run_indices) + 1)
            else:
                same_run_position = 0.0
        else:
            same_run_position = 0.0

        return {
            "tour_position": tour_pos,
            "diff_25_to_50": diff,
            "show_position_in_run": run_pos,
            "same_venue_run_position": same_run_position,
        }

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
        col_dates = cache["col_dates"]
        prior_dates = [d for d in col_dates if d is not None]
        tour_pos = float(_tour_position(prior_dates, ref_date.date(), tour_gap_days=14))
        run_pos = float(_run_position(prior_dates, ref_date.date(), gap_days=1))

        pct25 = p25 / max(1, min(25, n_shows))
        pct50 = p50 / max(1, min(50, n_shows))
        diff = (pct25 - pct50).values

        normalized_ctx = normalize_target_show_context(target_show_context or {})
        if normalized_venue_key(normalized_ctx):
            same_run_indices = same_venue_run_show_indices(plays, normalized_ctx)
            same_run_position = float(len(same_run_indices) + 1)
        else:
            same_run_position = 0.0

        return {
            "tour_position": tour_pos,
            "diff_25_to_50": diff,
            "show_position_in_run": run_pos,
            "same_venue_run_position": same_run_position,
        }


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


PHISH_COMBO_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="combo_stack_leaves15",
        description="num_leaves=15 on stacked feature model",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"num_leaves": 15},
    ),
    ExperimentConfig(
        slug="combo_stack_minleaf10",
        description="min_data_in_leaf=10 on stacked feature model",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_stack_minleaf20",
        description="min_data_in_leaf=20 on stacked feature model",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"min_data_in_leaf": 20},
    ),
    ExperimentConfig(
        slug="combo_stack_leaves15_minleaf10",
        description="num_leaves=15 + min_data_in_leaf=10",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"num_leaves": 15, "min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_stack_leaves15_minleaf20",
        description="num_leaves=15 + min_data_in_leaf=20",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"num_leaves": 15, "min_data_in_leaf": 20},
    ),
    ExperimentConfig(
        slug="combo_stack_lr003_r700",
        description="learning_rate=0.03, rounds=700 on stacked feature model",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"learning_rate": 0.03},
        round_overrides=700,
    ),
    ExperimentConfig(
        slug="combo_stack_leaves15_lr003_r700",
        description="num_leaves=15 + lr=0.03, rounds=700",
        base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun",
        param_overrides={"num_leaves": 15, "learning_rate": 0.03},
        round_overrides=700,
    ),
]


PHISH_SHOW_TYPE_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="feat_show_type",
        description=(
            "Add Phish show-type metadata and prior song-count interaction "
            "features to incumbent stacked model"
        ),
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusShowType",
    ),
]


PHISH_CLEANUP_ABLATION_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="cleanup_v3_dead_features",
        description=(
            "Remove previously diagnosed weak Phish features: plays_past_10, "
            "month_play_rate, and sparse same-venue prior-play count/share flags"
        ),
        predictor_path="jambandnerd.models.phish.experiments.PhishFastPredictorV3",
    ),
]


PHISH_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "hp_sweep": PHISH_HP_SWEEP,
    "feature_sweep": PHISH_FEATURE_SWEEP,
    "combo_sweep": PHISH_COMBO_SWEEP,
    "show_type_sweep": PHISH_SHOW_TYPE_SWEEP,
    "cleanup_ablation": PHISH_CLEANUP_ABLATION_SWEEP,
}
