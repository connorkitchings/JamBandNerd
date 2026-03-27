"""Model-specific configuration constants."""

from __future__ import annotations

from typing import Final

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

# Model version identifiers
MODEL_VERSIONS: Final[dict[str, str]] = {
    "notebook": "notebook_v1",
    "ckplus": "ckplus_v1",
    "deal": "deal_v1",
}

# Enabled models for website (deal hidden until approved)
ENABLED_MODELS: Final[list[str]] = ["notebook", "ckplus"]

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
DEAL_MAX_DEPTH: Final[int] = 6
DEAL_ETA: Final[float] = 0.1
DEAL_NROUNDS: Final[int] = 100

# Deal retraining interval (days)
DEAL_RETRAIN_INTERVAL_DAYS: Final[int] = 7
