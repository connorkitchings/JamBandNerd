"""Notebook prediction model package.

Implements a rotation-based predictor that focuses on songs most frequently
played in the last year, excluding recently played songs. Provides gap
analysis and frequency-based ranking.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import NotebookPredictor, RankedPrediction

__all__ = [
    "NotebookPredictor",
    "RankedPrediction",
    "model",
]


