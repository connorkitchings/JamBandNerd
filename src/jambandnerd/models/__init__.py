"""Prediction models package for setlist prediction.

Provides abstract base classes and concrete implementations for different
prediction algorithms, along with accuracy calculation utilities.

Supported models:
- notebook: Rotation-based predictor using past-year frequency analysis
- ckplus: Gap-based statistical predictor with z-score calculations

Core components:
- base: Abstract PredictionModel interface
- accuracy: Per-show and aggregate accuracy calculation utilities
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import PredictionModel, PredictionResult
    from .accuracy import TopKMetrics, compute_per_show_metrics, aggregate_metrics
    from .notebook.model import NotebookPredictor, RankedPrediction
    from .ckplus.model import CKPlusPredictor, CKPlusPrediction

__all__ = [
    "PredictionModel",
    "PredictionResult",
    "TopKMetrics",
    "compute_per_show_metrics",
    "aggregate_metrics",
    "NotebookPredictor",
    "RankedPrediction", 
    "CKPlusPredictor",
    "CKPlusPrediction",
    "base",
    "accuracy",
    "notebook",
    "ckplus",
]



