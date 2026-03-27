"""Database-related configuration."""

from __future__ import annotations

from typing import Final

from src.jambandnerd.models.metadata import MODEL_METADATA

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

# Unified accuracy table names
ACCURACY_TABLES: Final[dict[str, str]] = {
    metadata.slug: metadata.aggregate_accuracy_table
    for metadata in MODEL_METADATA
    if metadata.aggregate_accuracy_table
}
ACCURACY_TABLES["per_show"] = "accuracy_per_show"
