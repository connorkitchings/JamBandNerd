"""JamBandNerd: A modular data platform for jam band setlist prediction.

Main modules:
- data_collection: band-specific collectors with unified interfaces
- db: database connection, operations, and validation
- integrations: external-service automation and workflow adapters
- models: prediction models and evaluation utilities
- predictions: prediction-facing helpers and contracts
- transformations: feature engineering and data processing
- utils: shared support utilities
"""

__version__ = "0.2.1"

__all__ = [
    "data_collection",
    "db",
    "integrations",
    "models",
    "predictions",
    "transformations",
    "utils",
]
