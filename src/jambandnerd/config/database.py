"""Database-related configuration."""

from __future__ import annotations

from typing import Final

# Tables suffix for raw data
RAW_TABLE_SUFFIX: Final[str] = "_raw"

# Unified prediction table names
PREDICTION_TABLES: Final[dict[str, str]] = {
    "notebook": "predictions_notebook",
    "ckplus": "predictions_ckplus",
}

# Derived per-song prediction projection table
PREDICTION_SONGS_TABLE: Final[str] = "prediction_songs"

# Unified accuracy table names
ACCURACY_TABLES: Final[dict[str, str]] = {
    "notebook": "notebook_accuracy",
    "ckplus": "accuracy_ckplus",
    "per_show": "accuracy_per_show",
}
