from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from jambandnerd.models.deal.model import DealPrediction
from jambandnerd.transformations.gaps import ModelData

from .fast_predictor import GooseFastPredictor

_ALL_POSSIBLE_FEATURES: list[str] = [
    "current_gap",
    "plays_past_3",
    "plays_past_5",
    "plays_past_10",
    "plays_past_25",
    "plays_past_50",
    "career_play_pct",
    "month_play_rate",
    "diff_25_to_50",
    "show_position_in_run",
    "tour_position",
    "same_venue_run_position",
    "overdue_ratio",
    "avg_ltp_recent",
    "ltp_diff_recent",
    "plays_past_year",
    "plays_past_2yr",
]


def _plays_past_year_array(
    *,
    eligible_songs: pd.Index,
    target_date: Any,
    plays: pd.DataFrame,
    target_show_index: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    if target_date is None:
        zeros = np.zeros(len(eligible_songs), dtype=float)
        return zeros, zeros

    target_timestamp = pd.Timestamp(target_date)
    historical = (
        plays[plays["show_index"] < target_show_index]
        if target_show_index is not None
        else plays
    )

    def _counts(days: int) -> pd.Series:
        window = historical[
            (historical["show_date"] >= target_timestamp - pd.Timedelta(days=days))
            & (historical["show_date"] < target_timestamp)
        ]
        return (
            window.groupby("song_name")["show_index"]
            .nunique()
            .reindex(eligible_songs, fill_value=0)
            .astype(float)
        )

    return _counts(365).to_numpy(dtype=float), _counts(730).to_numpy(dtype=float)


class GooseFastAblationPredictor(GooseFastPredictor):
    MODEL_VERSION = "goose_ablation"

    def __init__(
        self,
        *,
        feature_cols: list[str],
        variant_name: str = "ablation",
        band: str = "goose",
        **kwargs: Any,
    ) -> None:
        super().__init__(band=band, **kwargs)
        self._ablation_feature_cols = feature_cols
        self._ablation_variant_name = variant_name
        self.MODEL_VERSION = f"goose_ablation_{variant_name}"

    @property
    def _FEATURE_COLS(self) -> list[str]:
        return self._ablation_feature_cols

    @_FEATURE_COLS.setter
    def _FEATURE_COLS(self, value: list[str]) -> None:
        pass

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

        if (
            "plays_past_year" in self._ablation_feature_cols
            or "plays_past_2yr" in self._ablation_feature_cols
        ):
            ppl_1yr, ppl_2yr = _plays_past_year_array(
                eligible_songs=eligible_songs,
                target_date=target_date,
                plays=plays,
                target_show_index=target_show_index,
            )
            frame["plays_past_year"] = ppl_1yr
            frame["plays_past_2yr"] = ppl_2yr

        cols = ["song_name"] + [
            c for c in self._ablation_feature_cols if c in frame.columns
        ]
        return frame[cols]

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[DealPrediction]:
        if self._model is None:
            return []

        from jambandnerd.config.bands import get_excluded_songs

        from .fast_predictor import (
            _clean_plays,
            _current_gap_for_prediction,
            _window_plays,
        )

        plays = _clean_plays(model_data.historical_plays)
        if plays.empty:
            return []

        cache = self._cache if self._cache is not None else self._prepare(plays)
        presence = cache["presence"]
        cum = cache["cum"]
        all_songs = presence.index
        n_shows = presence.shape[1]
        ref_col = n_shows - 1
        total_plays = cum.iloc[:, ref_col]
        current_gap = _current_gap_for_prediction(presence)

        recent_set = set(model_data.recently_played_songs)
        eligible_mask = (
            (total_plays >= self.min_plays_threshold)
            & (current_gap >= self.exclusion_window)
            & (current_gap <= self.retired_gap_threshold)
            & (~all_songs.isin(recent_set))
        )
        excluded_songs = get_excluded_songs(self.band)
        if excluded_songs:
            song_index = all_songs.astype(str).str.lower().str.strip()
            eligible_mask &= ~song_index.isin(excluded_songs)
        eligible_songs = all_songs[eligible_mask]
        if len(eligible_songs) == 0:
            return []

        ref_date = pd.Timestamp(model_data.reference_date).date()
        features = self._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=n_shows,
            target_date=ref_date,
            gap_e=current_gap.loc[eligible_songs],
            total_e=total_plays.loc[eligible_songs],
            cache=cache,
            plays=plays,
            target_show_context=model_data.target_show_context,
            target_show_index=None,
        ).set_index("song_name")

        feature_cols = [c for c in self._ablation_feature_cols if c in features.columns]
        scores = self._model.predict(features[feature_cols].values)
        probabilities = 1.0 / (1.0 + np.exp(-scores))
        order = np.argsort(probabilities)[::-1][:top_k]
        last_play_dates = cache["last_play_dates"]
        p50 = _window_plays(cum, n_shows, 50).loc[eligible_songs]

        return [
            DealPrediction(
                song_name=str(eligible_songs[index]),
                probability=float(probabilities[index]),
                current_gap=int(current_gap.loc[eligible_songs[index]]),
                plays_past_year=0,
                recent_plays_50=int(p50.loc[eligible_songs[index]]),
                LTP=(
                    pd.Timestamp(last_play_dates[str(eligible_songs[index])])
                    .date()
                    .isoformat()
                    if str(eligible_songs[index]) in last_play_dates
                    else None
                ),
            )
            for index in order
        ]
