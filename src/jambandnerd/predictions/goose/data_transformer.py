"""
Goose data transformation utilities for prediction models.

This module handles transforming raw Goose data from the data_collection API
into the format required by the band-agnostic prediction models.
"""

from typing import Any

import pandas as pd

from jambandnerd.data_collection.goose import loaders


def prepare_data_for_ckplus_model() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and transform Goose data for the CK+ prediction model.

    Returns:
        Tuple of DataFrames: (song_data, show_data, venue_data, setlist_data, transition_data)
    """
    # Load raw data from Goose API
    song_data, show_data, venue_data, setlist_data, transition_data, _ = loaders.load_goose_data()

    # Add band identifier
    show_data["band"] = "Goose"

    # Transform data to match model expectations
    # (Add any Goose-specific transformations here)

    return song_data, show_data, venue_data, setlist_data, transition_data


def prepare_data_for_notebook_model() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and transform Goose data for the Notebook prediction model.

    Returns:
        Tuple of DataFrames: (song_data, show_data, venue_data, setlist_data, transition_data)
    """
    # Load raw data from Goose API
    song_data, show_data, venue_data, setlist_data, transition_data, _ = loaders.load_goose_data()

    # Add band identifier
    show_data["band"] = "Goose"

    # Transform data to match model expectations
    # (Add any Goose-specific transformations here)

    return song_data, show_data, venue_data, setlist_data, transition_data


def get_band_config() -> dict[str, Any]:
    """
    Get Goose-specific configuration for prediction models.

    Returns:
        Dict containing band-specific configuration parameters
    """
    return {
        "band_name": "goose",
        "supabase_table_ckplus": "predictions_ckplus",
        "supabase_table_notebook": "predictions_notebook",
        "gap_threshold_ckplus": 50,  # Higher threshold for all-time data
        "gap_threshold_notebook": 15,  # Lower threshold for 1-year time filter
        "top_predictions": 100,  # Save top 100 predictions
        "recent_shows_filter": 3,  # Exclude songs played in last 3 shows
    }
