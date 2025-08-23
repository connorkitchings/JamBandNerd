from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd

from ..base import PredictionModel
from .features import compute_gap_features


@dataclass
class CKPlusPrediction:
    song_name: str
    times_played: int
    current_gap: int
    avg_gap: float
    gap_ratio: float
    gap_z_score: float
    ckplus_score: float
    LTP: str | None


class CKPlusPredictor(PredictionModel):
    """Gap-based CK+ predictor per docs/models/ckplus.md."""

    def __init__(self, alpha: float = 0.7, min_plays_threshold: int = 3, retired_gap_threshold: int = 200):
        self.alpha = float(alpha)
        self.min_plays_threshold = int(min_plays_threshold)
        self.retired_gap_threshold = int(retired_gap_threshold)

    def _score_row(self, row: pd.Series) -> float:
        # Reliability term R
        times_played = int(row.get("times_played", 0) or 0)
        std_gap = float(row.get("std_gap", 0.0) or 0.0)
        min_thr = max(1, self.min_plays_threshold)
        reliability = min(1.0, times_played / min_thr) * (1.0 / (1.0 + max(0.0, std_gap)))
        # Base overdue signal S
        gap_ratio = float(row.get("gap_ratio", float("nan")))
        gap_z = float(row.get("gap_z_score", 0.0) or 0.0)
        s_components = []
        if pd.notna(gap_ratio) and gap_ratio > 0:
            s_components.append(self.alpha * gap_ratio)
        s_components.append((1.0 - self.alpha) * max(0.0, gap_z))
        s = sum(s_components)
        return float(s * reliability)

    def predict(
        self,
        shows_df: pd.DataFrame,
        setlists_df: pd.DataFrame,
        top_k: int = 50,
        reference_show_date: date | None = None,
    ) -> List[CKPlusPrediction]:
        if reference_show_date is None:
            raise ValueError("reference_show_date is required for CK+ prediction")

        agg = compute_gap_features(shows_df, setlists_df, reference_show_date)
        features = agg.features
        if features.empty:
            return []

        # Filters
        f = features.copy()
        f = f[f["times_played"] > 0]  # Loosen filter for bands with deep catalogs
        f = f[f["current_gap"] > 1]   # exclude recently played
        f = f[f["current_gap"] <= self.retired_gap_threshold]

        if f.empty:
            return []

        # Score
        f["ckplus_score"] = f.apply(self._score_row, axis=1)

        # Rank
        f = f.sort_values(["ckplus_score", "gap_ratio", "song_name"], ascending=[False, False, True])
        top = f.head(top_k)

        results: List[CKPlusPrediction] = []
        for _, row in top.iterrows():
            results.append(
                CKPlusPrediction(
                    song_name=str(row["song_name"]),
                    times_played=int(row["times_played"]),
                    current_gap=int(row["current_gap"]),
                    avg_gap=float(row.get("avg_gap") if pd.notna(row.get("avg_gap")) else 0.0),
                    gap_ratio=float(row.get("gap_ratio") if pd.notna(row.get("gap_ratio")) else 0.0),
                    gap_z_score=float(row.get("gap_z_score") if pd.notna(row.get("gap_z_score")) else 0.0),
                    ckplus_score=float(row.get("ckplus_score") if pd.notna(row.get("ckplus_score")) else 0.0),
                    LTP=row.get("LTP"),
                )
            )
        return results

    def train(self, data, *args, **kwargs) -> None:
        """Placeholder for train method."""
        print("CKPlusPredictor does not require explicit training.")
        pass

    def calculate_accuracy(self, predictions, actual_songs, *args, **kwargs) -> Dict[str, Any]:
        """Placeholder for calculate_accuracy method."""
        print("Accuracy calculation not implemented for this model.")
        return {}



