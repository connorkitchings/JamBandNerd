from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List

from src.jambandnerd.models.base import PredictionModel
from src.jambandnerd.transformations.gaps import ModelData


@dataclass
class RankedPrediction:
    song_name: str
    plays_past_year: int
    current_gap: int
    last_played_date: str | None


class NotebookPredictor(PredictionModel):
    """Baseline notebook predictor using past-year features."""

    def __init__(self, band: str | None = None):
        self.band = band

    def predict(
        self,
        model_data: ModelData,
        top_k: int = 50,
    ) -> tuple[List[RankedPrediction], dict]:
        """
        Ranks songs primarily by plays in the past year, excluding songs
        played in the last 3 shows, and uses current gap as a tie-breaker.
        """
        features = model_data.master_feature_set
        plays = model_data.historical_plays
        if features.empty or plays.empty:
            return [], model_data.diagnostics

        # 1. Define 1-Year Window
        last_completed_show_date = features["last_played_date"].max()
        window_start = last_completed_show_date - timedelta(days=365)

        # 2. Calculate correct plays_past_year using the historical plays
        # Count unique shows per song to avoid counting reprises/encores as separate plays
        plays_in_window = plays[plays["show_date"] >= window_start]
        # Use nunique on show_index (or show_id) to count distinct shows where the song was played
        plays_past_year_count = (
            plays_in_window.groupby("song_name")["show_index"]
            .nunique()
            .rename("plays_past_year")
        )

        # 3. Filter candidates to songs played in the window
        song_candidates = features.merge(
            plays_past_year_count, on="song_name", how="inner"
        ).copy()

        if song_candidates.empty:
            return [], model_data.diagnostics

        # 4. Calculate current_gap
        song_candidates["current_gap"] = (
            model_data.reference_index - song_candidates["last_played_index"]
        )

        # 5. Exclude recently played songs (from last N shows based on exclusion window)
        recently_played_set = set(model_data.recently_played_songs)
        song_candidates = song_candidates[
            ~song_candidates["song_name"].isin(recently_played_set)
        ]

        if song_candidates.empty:
            return [], model_data.diagnostics

        # 6. Rank and Predict
        ranked = song_candidates.sort_values(
            by=["plays_past_year", "current_gap", "song_name"],
            ascending=[False, False, True],
        ).head(top_k)

        if self.band == "wsp":
            ranked = ranked[
                ~ranked["song_name"].str.lower().str.strip().isin(["jam", "drums"])
            ]

        # Format output
        result: List[RankedPrediction] = []
        for _, row in ranked.iterrows():
            result.append(
                RankedPrediction(
                    song_name=str(row["song_name"]),
                    plays_past_year=int(row["plays_past_year"]),
                    current_gap=int(row["current_gap"]),
                    last_played_date=row["last_played_date"].isoformat(),
                )
            )

        return result, model_data.diagnostics

    def train(self, data, *args, **kwargs) -> None:
        """Placeholder for train method."""
        print("NotebookModel does not require explicit training.")
        pass

    def calculate_accuracy(
        self, predictions, actual_songs, *args, **kwargs
    ) -> Dict[str, Any]:
        """Placeholder for calculate_accuracy method."""
        print("Accuracy calculation not implemented for this model.")
        return {}
