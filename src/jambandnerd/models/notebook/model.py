from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Any, Optional

import pandas as pd

from src.jambandnerd.models.base import PredictionModel
from src.jambandnerd.transformations.gaps import aggregate_past_year_for_notebook


@dataclass
class RankedPrediction:
    song_name: str
    plays_past_year: int
    current_gap: int
    last_played_date: str | None


class NotebookPredictor(PredictionModel):
    """Baseline notebook predictor using past-year features.

    Ranks songs primarily by plays in the past year, excluding songs
    played in the last 3 shows, and uses current gap as a tie-breaker.
    """

    def predict(
        self,
        shows_df: pd.DataFrame,
        setlists_df: pd.DataFrame,
        top_k: int = 25,
        reference_show_date: date | None = None,
    ) -> List[RankedPrediction]:
        if reference_show_date is None:
            raise ValueError("reference_show_date is required for prediction")
        agg = aggregate_past_year_for_notebook(
            shows_df=shows_df,
            setlists_df=setlists_df,
            reference_show_date=reference_show_date,
        )
        features = agg.features
        if features.empty:
            return []
        top = features.head(top_k)
        result: List[RankedPrediction] = []
        for _, row in top.iterrows():
            result.append(
                RankedPrediction(
                    song_name=str(row["song_name"]),
                    plays_past_year=int(row["plays_past_year"]),
                    current_gap=int(row["current_gap"]),
                    last_played_date=row.get("last_played_date"),
                )
            )
        return result

    def train(self, data, *args, **kwargs) -> None:
        """Placeholder for train method."""
        print("NotebookModel does not require explicit training.")
        pass

    def calculate_accuracy(self, predictions, actual_songs, *args, **kwargs) -> Dict[str, Any]:
        """Placeholder for calculate_accuracy method."""
        print("Accuracy calculation not implemented for this model.")
        return {}


