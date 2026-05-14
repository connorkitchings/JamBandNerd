"""Database-related configuration."""

from __future__ import annotations

from typing import Final

from jambandnerd.models.metadata import MODEL_METADATA

# Tables suffix for raw data
RAW_TABLE_SUFFIX: Final[str] = "_raw"

# Compatibility maps derived from the canonical model registry metadata.
PREDICTION_TABLES: Final[dict[str, str]] = {
    metadata.slug: metadata.prediction_table for metadata in MODEL_METADATA
}

# Derived per-song prediction projection table
PREDICTION_SONGS_TABLE: Final[str] = "prediction_songs"

# Canonical historical scored-run table for backtest lineage
HISTORICAL_PREDICTION_RUNS_TABLE: Final[str] = "historical_prediction_runs"

# Single-model-per-band Phase A tables
SETLIST_PREDICTIONS_TABLE: Final[str] = "setlist_predictions"
SETLIST_PREDICTION_SONGS_TABLE: Final[str] = "setlist_prediction_songs"
SETLIST_RESULTS_TABLE: Final[str] = "setlist_results"
SETLIST_ACCURACY_TABLE: Final[str] = "setlist_accuracy"

# Product-facing live next-show prediction tables
NEXT_SHOW_PREDICTION_RUNS_TABLE: Final[str] = "next_show_prediction_runs"
NEXT_SHOW_PREDICTION_SONGS_TABLE: Final[str] = "next_show_prediction_songs"

# Product-facing retained completed-show prediction and metric tables
COMPLETED_SHOW_PREDICTION_RUNS_TABLE: Final[str] = "completed_show_prediction_runs"
COMPLETED_SHOW_ACCURACY_TABLE: Final[str] = "completed_show_accuracy"
