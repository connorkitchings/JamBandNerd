"""JamBandNerd: A modular data science platform for jam band setlist prediction.

This package provides comprehensive data collection, transformation, modeling, and
web interface capabilities for analyzing and predicting jam band setlists.

Main modules:
- data_collection: Band-specific data collectors with unified interfaces
- db: Database connection, operations, and validation
- models: Prediction models (Notebook, CK+) with accuracy tracking
- transformations: Feature engineering and data processing
- web: Streamlit web interface for predictions and analytics
"""

__version__ = "0.1.0"

__all__ = [
    "data_collection",
    "db",
    "models",
    "predictions",
    "transformations",
    "utils",
    "web",
]



