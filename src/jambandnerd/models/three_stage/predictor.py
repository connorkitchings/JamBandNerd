"""3-Stage setlist forecasting predictor.

Stage 1: Any PredictionModel producing (song_name, probability) pairs (availability).
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


def _prediction_attrs(pred: Any) -> tuple[str, float]:
    return getattr(pred, "song_name", ""), getattr(pred, "probability", 0.0)


class ThreeStagePredictor(PredictionModel):
    """3-Stage setlist forecasting: availability model + transition matrix + beam search.

    The stage-1 model can be any PredictionModel subclass. For bands with a fast
    vectorized predictor (e.g. BillyFastPredictor), pass it via ``stage1_class``.
    Otherwise BandGbmPredictor is used as the default.
    """

    MODEL_VERSION = "three_stage_v1"

    def __init__(
        self,
        band: str,
        stage1_class: Type[PredictionModel] | None = None,
        beam_width: int = _DEFAULT_BEAM_WIDTH,
        setlist_window: int = _AVG_SETLIST_WINDOW,
        persist_artifacts: bool = False,
        **stage1_kwargs: Any,
    ) -> None:
        self.band = band
        self.beam_width = beam_width
        self.setlist_window = setlist_window
        self.persist_artifacts = persist_artifacts
        if stage1_class is not None:
            self._stage1 = stage1_class(
                band=band,
                persist_artifacts=persist_artifacts,
                **stage1_kwargs,
            )
        else:
            self._stage1 = BandGbmPredictor(
                band=band,
                persist_artifacts=persist_artifacts,
                **stage1_kwargs,
            )
        self._transition_matrix: Optional[TransitionMatrix] = None

    def train(self, data: ModelData) -> None:
        self._stage1.train(data)

        plays = data.historical_plays
        required = {"show_id", "set_number", "song_position", "song_name"}
        available = set(plays.columns)

        if required.issubset(available):
            self._transition_matrix = TransitionMatrix().build(plays)
        else:
            self._transition_matrix = None

    def predict(self, model_data: ModelData, top_k: int = 50) -> List[DealPrediction]:
        raw_predictions = self._stage1.predict(model_data, top_k=top_k)
        if not raw_predictions:
            return []

        if self._transition_matrix is None or self._transition_matrix.n_pairs == 0:
            return [
                self._wrap_as_deal(p) for p in raw_predictions[:top_k]
            ]

        stage1_probs = dict(_prediction_attrs(p) for p in raw_predictions)
        candidate_songs = list(stage1_probs.keys())

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

        pred_by_song: dict[str, Any] = {p.song_name: p for p in raw_predictions}
        ranked: List[DealPrediction] = []
        for song in result.ranked_songs[:top_k]:
            if song in pred_by_song:
                base = pred_by_song[song]
                beam_score = result.song_scores.get(
                    song, getattr(base, "probability", 0.0)
                )
                ranked.append(self._wrap_as_deal(base, probability=beam_score))

        if len(ranked) < top_k:
            ranked_set = {p.song_name for p in ranked}
            for p in raw_predictions:
                if getattr(p, "song_name", "") not in ranked_set:
                    ranked.append(self._wrap_as_deal(p))
                    if len(ranked) >= top_k:
                        break

        return ranked

    @staticmethod
    def _wrap_as_deal(pred: Any, probability: float | None = None) -> DealPrediction:
        return DealPrediction(
            song_name=getattr(pred, "song_name", ""),
            probability=float(probability if probability is not None else getattr(pred, "probability", 0.0)),
            current_gap=getattr(pred, "current_gap", getattr(pred, "gap_shows", 0)),
            plays_past_year=getattr(pred, "plays_past_year", 0),
            recent_plays_50=getattr(pred, "recent_plays_50", 0),
            LTP=getattr(pred, "LTP", None),
        )

    def calculate_accuracy(
        self,
        predictions: list[Any],
        actual_songs: list[str],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {}
