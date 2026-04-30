"""3-Stage setlist forecasting predictor.

Stage 1: GBM with Platt-scaled calibrated probabilities (availability).
Stage 2: Directional within-set bigram transition matrix (sequence momentum).
Stage 3: Beam search sequence optimizer (final ranking).
"""

from __future__ import annotations

from typing import Any, List, Optional, Type

import pandas as pd

from jambandnerd.models.base import PredictionModel
from jambandnerd.models.beam_search import BeamSearchResult, beam_search
from jambandnerd.models.deal.model import DealPrediction
from jambandnerd.models.gbm.predictor import BandGbmPredictor
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.transitions import TransitionMatrix

_AVG_SETLIST_WINDOW = 25
_DEFAULT_BEAM_WIDTH = 5


def _avg_songs_per_show(historical_plays: pd.DataFrame, window: int) -> int:
    if historical_plays.empty:
        return 20
    unique_shows = historical_plays["show_index"].unique()
    recent = sorted(unique_shows)[-window:]
    recent_plays = historical_plays[historical_plays["show_index"].isin(recent)]
    counts = recent_plays.groupby("show_index")["song_name"].nunique()
    return int(counts.mean()) if len(counts) > 0 else 20


class ThreeStagePredictor(PredictionModel):
    """3-Stage setlist forecasting: GBM availability + transition matrix + beam search."""

    MODEL_VERSION = "three_stage_v1"

    def __init__(
        self,
        band: str,
        gbm_class: Type[BandGbmPredictor] = BandGbmPredictor,
        beam_width: int = _DEFAULT_BEAM_WIDTH,
        setlist_window: int = _AVG_SETLIST_WINDOW,
        persist_artifacts: bool = False,
        **gbm_kwargs: Any,
    ) -> None:
        self.band = band
        self.beam_width = beam_width
        self.setlist_window = setlist_window
        self.persist_artifacts = persist_artifacts
        self._gbm = gbm_class(
            band=band,
            persist_artifacts=persist_artifacts,
            **gbm_kwargs,
        )
        self._transition_matrix: Optional[TransitionMatrix] = None

    def train(self, data: ModelData) -> None:
        self._gbm.train(data)

        plays = data.historical_plays
        required = {"show_id", "set_number", "song_position", "song_name"}
        available = set(plays.columns)

        if required.issubset(available):
            self._transition_matrix = TransitionMatrix().build(plays)
        else:
            self._transition_matrix = None

    def predict(self, model_data: ModelData, top_k: int = 50) -> List[DealPrediction]:
        predictions = self._gbm.predict(model_data, top_k=top_k)
        if not predictions:
            return predictions

        if self._transition_matrix is None or self._transition_matrix.n_pairs == 0:
            return predictions

        stage1_probs = {p.song_name: p.probability for p in predictions}
        candidate_songs = [p.song_name for p in predictions]

        seq_length = _avg_songs_per_show(
            model_data.historical_plays, self.setlist_window
        )

        result: BeamSearchResult = beam_search(
            stage1_probs=stage1_probs,
            transition_matrix=self._transition_matrix,
            sequence_length=seq_length,
            beam_width=self.beam_width,
            candidate_songs=candidate_songs,
        )

        pred_by_song = {p.song_name: p for p in predictions}
        ranked: List[DealPrediction] = []
        for song in result.ranked_songs[:top_k]:
            if song in pred_by_song:
                base = pred_by_song[song]
                beam_score = result.song_scores.get(song, base.probability)
                ranked.append(
                    DealPrediction(
                        song_name=base.song_name,
                        probability=float(beam_score),
                        current_gap=base.current_gap,
                        plays_past_year=base.plays_past_year,
                        recent_plays_50=base.recent_plays_50,
                        LTP=base.LTP,
                    )
                )

        if len(ranked) < top_k:
            ranked_set = {p.song_name for p in ranked}
            for p in predictions:
                if p.song_name not in ranked_set:
                    ranked.append(p)
                    if len(ranked) >= top_k:
                        break

        return ranked

    def calculate_accuracy(
        self,
        predictions: list[Any],
        actual_songs: list[str],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {}
