from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List

import pandas as pd

from jambandnerd.config.bands import get_excluded_songs
from jambandnerd.models.base import PredictionModel
from jambandnerd.transformations.gaps import ModelData

logger = logging.getLogger(__name__)

_WINDOW_DAYS = {"1yr": 365, "2yr": 730}
_WINDOW_SHOWS = {"50shows": 50, "100shows": 100}


@dataclass
class AblationPrediction:
    song_name: str
    window_plays: int
    current_gap: int
    last_played_date: str | None


def _count_plays_in_window(
    plays: pd.DataFrame,
    features: pd.DataFrame,
    window_mode: str,
) -> pd.Series:
    if window_mode in _WINDOW_DAYS:
        days = _WINDOW_DAYS[window_mode]
        last_date = features["last_played_date"].max()
        window_start = last_date - timedelta(days=days)
        in_window = plays[plays["show_date"] >= window_start]
    elif window_mode in _WINDOW_SHOWS:
        n = _WINDOW_SHOWS[window_mode]
        recent_show_indices = sorted(plays["show_index"].unique())[-n:]
        in_window = plays[plays["show_index"].isin(recent_show_indices)]
    else:
        raise ValueError(f"Unknown window_mode: {window_mode}")

    return (
        in_window.groupby("song_name")["show_index"]
        .nunique()
        .rename("window_plays")
    )


class NotebookAblationPredictor(PredictionModel):
    MODEL_VERSION = "notebook_ablation"
    _WINDOW_MODE: str = "1yr"

    def __init__(self, band: str | None = None, **kwargs: Any):
        self.band = band

    def predict(
        self,
        model_data: ModelData,
        top_k: int = 50,
    ) -> tuple[List[AblationPrediction], dict]:
        features = model_data.master_feature_set
        plays = model_data.historical_plays
        if features.empty or plays.empty:
            return [], model_data.diagnostics

        window_plays_count = _count_plays_in_window(
            plays, features, self._WINDOW_MODE
        )

        song_candidates = features.merge(
            window_plays_count, on="song_name", how="inner"
        ).copy()

        if song_candidates.empty:
            return [], model_data.diagnostics

        song_candidates["current_gap"] = (
            model_data.reference_index - song_candidates["last_played_index"] - 1
        ).clip(lower=0)

        recently_played_set = set(model_data.recently_played_songs)
        song_candidates = song_candidates[
            ~song_candidates["song_name"].isin(recently_played_set)
        ]

        if song_candidates.empty:
            return [], model_data.diagnostics

        ranked = song_candidates.sort_values(
            by=["window_plays", "current_gap", "song_name"],
            ascending=[False, False, True],
        ).head(top_k)

        excluded_songs = get_excluded_songs(self.band or "")
        if excluded_songs:
            ranked = ranked[
                ~ranked["song_name"].str.lower().str.strip().isin(excluded_songs)
            ]

        result: List[AblationPrediction] = []
        for _, row in ranked.iterrows():
            result.append(
                AblationPrediction(
                    song_name=str(row["song_name"]),
                    window_plays=int(row["window_plays"]),
                    current_gap=int(row["current_gap"]),
                    last_played_date=row["last_played_date"].isoformat(),
                )
            )

        return result, model_data.diagnostics

    def train(self, data, *args, **kwargs) -> None:
        pass

    def calculate_accuracy(
        self, predictions, actual_songs, *args, **kwargs
    ) -> Dict[str, Any]:
        return {}


class Notebook1yrPredictor(NotebookAblationPredictor):
    MODEL_VERSION = "notebook_1yr"
    _WINDOW_MODE = "1yr"


class Notebook2yrPredictor(NotebookAblationPredictor):
    MODEL_VERSION = "notebook_2yr"
    _WINDOW_MODE = "2yr"


class Notebook50Predictor(NotebookAblationPredictor):
    MODEL_VERSION = "notebook_50"
    _WINDOW_MODE = "50shows"


class Notebook100Predictor(NotebookAblationPredictor):
    MODEL_VERSION = "notebook_100"
    _WINDOW_MODE = "100shows"
