"""Database-related configuration."""

from __future__ import annotations

from typing import Final

# Tables suffix for raw data
RAW_TABLE_SUFFIX: Final[str] = "_raw"

# Single-model-per-band tables
SETLIST_PREDICTIONS_TABLE: Final[str] = "setlist_predictions"
SETLIST_PREDICTION_SONGS_TABLE: Final[str] = "setlist_prediction_songs"
SETLIST_RESULTS_TABLE: Final[str] = "setlist_results"
SETLIST_ACCURACY_TABLE: Final[str] = "setlist_accuracy"
