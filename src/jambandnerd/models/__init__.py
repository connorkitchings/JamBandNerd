"""Prediction models package for setlist prediction.

Provides abstract base classes and concrete implementations for different
prediction algorithms, along with accuracy calculation utilities.

Supported models:
- notebook: Rotation-based predictor using past-year frequency analysis
- deal: Logistic regression predictor with feature engineering

Core components:
- base: Abstract PredictionModel interface
- accuracy: Per-show and aggregate accuracy calculation utilities
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .accuracy import TopKMetrics, aggregate_metrics, compute_per_show_metrics
    from .base import PredictionModel, PredictionResult
    from .deal.model import DealPredictor
    from .notebook.model import NotebookPredictor, RankedPrediction

__all__ = [
    "PredictionModel",
    "PredictionResult",
    "TopKMetrics",
    "compute_per_show_metrics",
    "aggregate_metrics",
    "NotebookPredictor",
    "RankedPrediction",
    "DealPredictor",
    "base",
    "accuracy",
    "notebook",
    "deal",
]
