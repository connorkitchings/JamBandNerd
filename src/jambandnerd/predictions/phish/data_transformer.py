"""
Phish data transformation utilities for prediction models.

This module handles transforming raw Phish data from the data_collection API
into the format required by the band-agnostic prediction models.
"""

from typing import Any

import pandas as pd

from jambandnerd.data_collection.phish import loaders


def prepare_data_for_ckplus_model() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    """
    Load and transform Phish data for the CK+ prediction model.

    Returns:
        Tuple of DataFrames: (song_data, show_data, venue_data, setlist_data, transition_data)
    """
    # Load raw data from Phish API
    data = loaders.load_phish_data()
    song_data = data["song_data"]
    show_data = data["show_data"]
    venue_data = data["venue_data"]
    setlist_data = data["setlist_data"]
    transition_data = data["transition_data"]

    # Transform data to match model expectations
    # Rename Phish columns to match model expectations
    song_data = song_data.rename(columns={"songid": "song_id"})
    show_data = show_data.rename(columns={"showid": "show_id", "showdate": "show_date"})
    setlist_data = setlist_data.rename(
        columns={"songid": "song_id", "showid": "show_id"}
    )

    # Add band column for multi-band support
    show_data["band"] = "phish"

    return song_data, show_data, venue_data, setlist_data, transition_data


def prepare_data_for_notebook_model() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    """
    Load and transform Phish data for the Notebook prediction model.

    Returns:
        Tuple of DataFrames: (song_data, show_data, venue_data, setlist_data, transition_data)
    """
    # Load raw data from Phish API
    data = loaders.load_phish_data()
    song_data = data["song_data"]
    show_data = data["show_data"]
    venue_data = data["venue_data"]
    setlist_data = data["setlist_data"]
    transition_data = data["transition_data"]

    # Transform data to match model expectations
    # Rename Phish columns to match model expectations
    song_data = song_data.rename(columns={"songid": "song_id"})
    show_data = show_data.rename(columns={"showid": "show_id", "showdate": "show_date"})
    setlist_data = setlist_data.rename(
        columns={"songid": "song_id", "showid": "show_id"}
    )

    # Add band column for multi-band support
    show_data["band"] = "phish"

    return song_data, show_data, venue_data, setlist_data, transition_data


def get_band_config() -> dict[str, Any]:
    """
    Get Phish-specific configuration for prediction models.

    Returns:
        dict containing band-specific configuration parameters
    """
    return {
        "band_name": "phish",
        "supabase_table_ckplus": "predictions_ckplus",
        "supabase_table_notebook": "predictions_notebook",
        "gap_threshold": 75,  # Filter out predictions with current_gap > 75
        "top_predictions": 100,  # Save top 100 predictions
        "recent_shows_filter": 3,  # Exclude songs played in last 3 shows
    }
