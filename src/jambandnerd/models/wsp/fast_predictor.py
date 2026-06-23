"""Widespread Panic fast predictor — based on PhishFastPredictorV2 architecture.

V2: Adds long-rotation features (plays_past_100, diff_50_to_100,
long_rotation_pressure) and HP tuning (lr=0.03, rounds=700) on top of
the PhishFast V2 16-feature set.  LightGBM rank_xendcg with early stopping.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from jambandnerd.config.bands import get_excluded_songs
from jambandnerd.models.billy.fast_predictor import _gap_percentile_arr
from jambandnerd.models.phish.fast_predictor import (
    _LGB_PARAMS,
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

_WSP_CANDIDATE_RECENT_SHOWS = 150
_WSP_CANDIDATE_TOP_CAREER = 100

_WSP_V2_LGB_PARAMS: dict[str, Any] = {
    **_LGB_PARAMS,
    "learning_rate": 0.03,
}


class WSPFastPredictor(PhishFastPredictorV2):
    """Widespread Panic LightGBM predictor — V2.

    19 features: 16 PhishFast V2 features + plays_past_100,
    diff_50_to_100, long_rotation_pressure.  HP-tuned with lr=0.03,
    rounds=700.  Early stopping (25 rounds, 20% validation split).

    V1 (16 feats, lr=0.05, rounds=500): dual=0.434
    V2 (19 feats, lr=0.03, rounds=700): dual=0.448 (+0.014)
    """

    MODEL_VERSION = "wsp_fast_gbm_v2"

    _FEATURE_COLS: list[str] = [
        *PHISH_FAST_V2_FEATURE_COLS,
        "plays_past_100",
        "diff_50_to_100",
        "long_rotation_pressure",
    ]

    _LGB_PARAMS: dict[str, Any] = _WSP_V2_LGB_PARAMS
    _LGB_ROUNDS: int = 700

    def __init__(self, band: str = "wsp", **kwargs: Any) -> None:
        if band != "wsp":
            raise ValueError("WSPFastPredictor only supports band='wsp'.")
        self.band = band
        self._model = None
        self.best_iteration = None
        self._cache = None
        self.diagnostic_feature_columns = list(self._FEATURE_COLS)

    def _candidate_recent_shows(self) -> int:
        return _WSP_CANDIDATE_RECENT_SHOWS

    def _candidate_top_career(self) -> int:
        return _WSP_CANDIDATE_TOP_CAREER

    def _eligible_mask_filter(
        self,
        candidates: pd.Index,
        eligible_mask: pd.Series,
    ) -> pd.Series:
        """Drop WSP noise songs (Drums, Jam, artist collisions) from candidates.

        WSP setlists include structural markers ("Drums", "Jam") and billed
        co-performers ("David Bromberg Band", etc.) that are not predictable
        songs. Filtering them at the eligibility mask — before the top-K
        slice — keeps them out of training rows and predictions while
        preserving top_k depth (the next-ranked real song backfills in).
        Mirrors the Goose predictor's exclusion pattern.
        """
        excluded_songs = get_excluded_songs(self.band)
        if not excluded_songs:
            return eligible_mask
        song_index = candidates.astype(str).str.lower().str.strip()
        return eligible_mask & ~song_index.isin(excluded_songs)

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


# ── Candidate sweep experiment subclasses ──────────────────────────────────────


class WSPFastCandidateRecent100(WSPFastPredictor):
    """Candidate pruning: recent=100 (narrower recent window)."""

    MODEL_VERSION = "wsp_fast_gbm_v2_cand_recent100"

    def _candidate_recent_shows(self) -> int:
        return 100


class WSPFastCandidateRecent200(WSPFastPredictor):
    """Candidate pruning: recent=200 (wider recent window)."""

    MODEL_VERSION = "wsp_fast_gbm_v2_cand_recent200"

    def _candidate_recent_shows(self) -> int:
        return 200


class WSPFastCandidateRecent250(WSPFastPredictor):
    """Candidate pruning: recent=250 (widest recent window)."""

    MODEL_VERSION = "wsp_fast_gbm_v2_cand_recent250"

    def _candidate_recent_shows(self) -> int:
        return 250


class WSPFastCandidateCareer50(WSPFastPredictor):
    """Candidate pruning: career=50 (narrower career cap)."""

    MODEL_VERSION = "wsp_fast_gbm_v2_cand_career50"

    def _candidate_top_career(self) -> int:
        return 50


class WSPFastCandidateCareer150(WSPFastPredictor):
    """Candidate pruning: career=150 (wider career cap)."""

    MODEL_VERSION = "wsp_fast_gbm_v2_cand_career150"

    def _candidate_top_career(self) -> int:
        return 150


# ── Feature experiment subclasses ──────────────────────────────────────────────


class WSPFastPlaysPastYear(WSPFastPredictor):
    """Add plays_past_year (distinct shows in trailing 365 days)."""

    MODEL_VERSION = "wsp_fast_gbm_v2_feat_plays_past_year"
    _FEATURE_COLS: list[str] = [
        *WSPFastPredictor._FEATURE_COLS,
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


class WSPFastNotebookRank(WSPFastPlaysPastYear):
    """Add normalized Notebook-style rank score over the candidate set.

    Sorts by (plays_past_year DESC, gap_shows DESC, song_name ASC) and
    converts the rank to a normalized score in [0, 1].
    """

    MODEL_VERSION = "wsp_fast_gbm_v2_feat_notebook_rank"
    _FEATURE_COLS: list[str] = [
        *WSPFastPlaysPastYear._FEATURE_COLS,
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


class WSPFastVenueRun(WSPFastPredictor):
    """Add same-venue run prior-play candidate features.

    Adds same_venue_run_prior_played/count/share for each candidate song.
    """

    MODEL_VERSION = "wsp_fast_gbm_v2_feat_venue_run"
    _FEATURE_COLS: list[str] = [
        *WSPFastPredictor._FEATURE_COLS,
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


def _gap_vs_median_arr(
    eligible_songs: pd.Index,
    gap_e: pd.Series,
    gap_dist: dict[str, np.ndarray],
) -> np.ndarray:
    result = np.zeros(len(eligible_songs), dtype=float)
    for i, (s, g) in enumerate(zip(eligible_songs, gap_e.values)):
        dist = gap_dist.get(str(s), np.array([]))
        if len(dist) >= 2:
            result[i] = g / max(1.0, float(np.median(dist)))
        else:
            result[i] = 1.0
    return result


class WSPFastGapDecoupled(WSPFastPredictor):
    """Add gap_percentile and gap_vs_median to decouple gap from rotation strength.

    21 features: 19 V2 features + gap_percentile + gap_vs_median.
    Keeps coupled features (overdue_ratio, long_rotation_pressure).
    """

    MODEL_VERSION = "wsp_fast_gbm_v2_gap_decoupled"
    _FEATURE_COLS: list[str] = [
        *WSPFastPredictor._FEATURE_COLS,
        "gap_percentile",
        "gap_vs_median",
    ]

    def _gap_decoupled_features(
        self, eligible_songs: pd.Index, gap_e: pd.Series, cache: dict
    ) -> dict[str, Any]:
        gap_dist = cache["gap_dist"]
        return {
            "gap_percentile": _gap_percentile_arr(eligible_songs, gap_e, gap_dist),
            "gap_vs_median": _gap_vs_median_arr(eligible_songs, gap_e, gap_dist),
        }

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        extra.update(
            self._gap_decoupled_features(
                kwargs["eligible_songs"], kwargs["gap_e"], kwargs["cache"]
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            self._gap_decoupled_features(
                kwargs["eligible_songs"], kwargs["gap_e"], kwargs["cache"]
            )
        )
        return extra


class WSPFastGapDecoupledClean(WSPFastPredictor):
    """Replace coupled gap features with decoupled versions.

    19 features: removes overdue_ratio and long_rotation_pressure,
    adds gap_percentile and gap_vs_median.
    """

    MODEL_VERSION = "wsp_fast_gbm_v2_gap_decoupled_clean"
    _FEATURE_COLS: list[str] = [
        f
        for f in WSPFastPredictor._FEATURE_COLS
        if f not in ("overdue_ratio", "long_rotation_pressure")
    ] + ["gap_percentile", "gap_vs_median"]

    def _gap_decoupled_features(
        self, eligible_songs: pd.Index, gap_e: pd.Series, cache: dict
    ) -> dict[str, Any]:
        gap_dist = cache["gap_dist"]
        return {
            "gap_percentile": _gap_percentile_arr(eligible_songs, gap_e, gap_dist),
            "gap_vs_median": _gap_vs_median_arr(eligible_songs, gap_e, gap_dist),
        }

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        extra.update(
            self._gap_decoupled_features(
                kwargs["eligible_songs"], kwargs["gap_e"], kwargs["cache"]
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            self._gap_decoupled_features(
                kwargs["eligible_songs"], kwargs["gap_e"], kwargs["cache"]
            )
        )
        return extra
