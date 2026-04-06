"""Model-specific configuration constants."""

from __future__ import annotations

from typing import Final

from jambandnerd.models.metadata import MODEL_METADATA

# Top-K values for accuracy evaluation
TOP_K_VALUES: Final[list[int]] = [10, 25, 50]

# Default number of recent shows to exclude songs from predictions
EXCLUSION_WINDOW_DEFAULT: Final[int] = 3

# Band-specific exclusion windows (overrides default)
BAND_EXCLUSION_WINDOWS: Final[dict[str, int]] = {
    "um": 4,  # UM uses 4-show exclusion window instead of default 3
}

# Minimum number of plays required for a song to be considered by CK+ model
MIN_PLAYS_THRESHOLD_DEFAULT: Final[int] = 5

# Alpha parameter for CK+ model (weight for gap ratio vs z-score)
CKPLUS_ALPHA_DEFAULT: Final[float] = 0.7

# Retirement gap thresholds by band (shows without a play before considered "retired")
RETIREMENT_GAPS: Final[dict[str, int]] = {
    "goose": 100,  # Smaller gap for a band with more regular rotation
    "eggy": 120,  # Smaller catalog but still rotating regularly
    "phish": 150,  # Larger gap for a band with deeper catalog
    "wsp": 150,  # Similar to Phish
    "billy": 150,
    "um": 150,
    "default": 250,  # Safe fallback for other bands
}

# Compatibility maps derived from the canonical model registry metadata.
MODEL_VERSIONS: Final[dict[str, str]] = {
    metadata.slug: metadata.version for metadata in MODEL_METADATA
}

ENABLED_MODELS: Final[list[str]] = [
    metadata.slug for metadata in MODEL_METADATA if metadata.enabled_for_web
]

# Deal model-specific configuration
DEAL_MIN_PLAYS_THRESHOLD: Final[int] = 5
DEAL_RETIREMENT_GAP: Final[dict[str, int]] = {
    "goose": 100,
    "phish": 150,
    "wsp": 150,
    "billy": 150,
    "um": 150,
    "eggy": 120,
    "default": 150,
}

# Deal model hyperparameters
DEAL_MIN_TRAINING_SHOWS: Final[int] = 25
DEAL_TRAINING_WINDOW_SHOWS: Final[int] = 75
DEAL_LEARNING_RATE: Final[float] = 0.05
DEAL_EPOCHS: Final[int] = 400
DEAL_L2_REGULARIZATION: Final[float] = 0.01

# Deal retraining interval (days)
DEAL_RETRAIN_INTERVAL_DAYS: Final[int] = 7
