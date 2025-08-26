from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Any

import numpy as np
import pandas as pd

from ..base import PredictionModel
from src.jambandnerd.transformations.gaps import ModelData


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

    def __init__(self, alpha: float = 0.7, min_plays_threshold: int = 5, retired_gap_threshold: int = 250):
        # Validate parameters
        if not 0 <= alpha <= 1:
            raise ValueError(f"alpha must be between 0 and 1, got {alpha}")
        if min_plays_threshold < 1:
            raise ValueError(f"min_plays_threshold must be at least 1, got {min_plays_threshold}")
        if retired_gap_threshold < 1:
            raise ValueError(f"retired_gap_threshold must be at least 1, got {retired_gap_threshold}")
            
        self.alpha = float(alpha)
        self.min_plays_threshold = int(min_plays_threshold)
        self.retired_gap_threshold = int(retired_gap_threshold)

    def _score_row(self, row: pd.Series) -> float:
        """Calculate CK+ score for a single song, with robust error handling."""
        try:
            # Reliability term R
            times_played = int(row.get("times_played", 0) or 0)
            std_gap = float(row.get("std_gap", 0.0) or 0.0)
            
            # Guard against division by zero
            min_thr = max(1, self.min_plays_threshold)
            reliability = min(1.0, times_played / min_thr) * (1.0 / (1.0 + max(0.0, std_gap)))
            
            # Base overdue signal S
            gap_ratio = row.get("gap_ratio", float("nan"))
            gap_z = float(row.get("gap_z_score", 0.0) or 0.0)
            
            s_components = []
            # Only include gap_ratio if it's finite and positive
            if pd.notna(gap_ratio) and np.isfinite(gap_ratio) and gap_ratio > 0:
                s_components.append(self.alpha * float(gap_ratio))
            
            # Include z-score component (clamped to reasonable range)
            gap_z_clamped = max(0.0, min(10.0, gap_z))  # Cap at 10 standard deviations
            s_components.append((1.0 - self.alpha) * gap_z_clamped)
            
            s = sum(s_components)
            score = float(s * reliability)
            
            # Return finite score or 0.0 if non-finite
            return score if np.isfinite(score) else 0.0
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            # Log the error and return 0 score for this song
            print(f"Warning: Error calculating score for song {row.get('song_name', 'unknown')}: {e}")
            return 0.0

    def predict(
        self,
        model_data: ModelData,
        top_k: int = 50,
    ) -> List[CKPlusPrediction]:
        """Predicts songs using the CK+ gap-based methodology."""
        features = model_data.master_feature_set
        if features.empty:
            return []

        # 1. Define 5-Year Window
        last_completed_show_date = features["last_played_date"].max()
        window_start = last_completed_show_date - timedelta(days=5 * 365)

        # 2. Filter candidates
        f = features[features["last_played_date"] >= window_start].copy()
        f = f[f["times_played"] > self.min_plays_threshold]

        # 3. Calculate final features
        f["current_gap"] = model_data.reference_index - f["last_played_index"]
        f["gap_ratio"] = f.apply(
            lambda r: (r["current_gap"] / r["avg_gap"]) if pd.notna(r["avg_gap"]) and r["avg_gap"] > 0 else float("nan"), axis=1
        )
        f["gap_z_score"] = f.apply(
            lambda r: ((r["current_gap"] - r["avg_gap"]) / r["std_gap"]) if (r["std_gap"] and r["std_gap"] > 0) else 0.0, axis=1
        )

        # 4. Apply final exclusions
        f = f[f["current_gap"] > 1]  # Exclude songs played in the very last show
        f = f[f["current_gap"] <= self.retired_gap_threshold]

        if f.empty:
            return []

        # 5. Score and Rank
        f["ckplus_score"] = f.apply(self._score_row, axis=1)
        f = f.sort_values(["ckplus_score", "gap_ratio", "song_name"], ascending=[False, False, True])
        top = f.head(top_k)

        # Format output
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
                    LTP=row["last_played_date"].isoformat(),
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



