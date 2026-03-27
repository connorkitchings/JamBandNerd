"""Database-related configuration."""

from __future__ import annotations

from typing import Final

# Tables suffix for raw data
RAW_TABLE_SUFFIX: Final[str] = "_raw"

# Unified prediction table names
PREDICTION_TABLES: Final[dict[str, str]] = {
    "notebook": "predictions_notebook",
    "ckplus": "predictions_ckplus",
    "deal": "predictions_deal",
}

# Derived per-song prediction projection table
PREDICTION_SONGS_TABLE: Final[str] = "prediction_songs"

# Canonical historical scored-run table for backtest lineage
HISTORICAL_PREDICTION_RUNS_TABLE: Final[str] = "historical_prediction_runs"

# Unified accuracy table names
ACCURACY_TABLES: Final[dict[str, str]] = {
    "notebook": "notebook_accuracy",
    "ckplus": "accuracy_ckplus",
    "deal": "accuracy_deal",
    "per_show": "accuracy_per_show",
}
