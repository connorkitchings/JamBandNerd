"""Data loading and processing utilities for Jam Band Nerd app."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add the src directory to the Python path to import jambandnerd modules
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from constants import NOTEBOOK_LABELS
from jambandnerd.db.db_utils import get_table_as_dataframe


def load_predictions_from_supabase(band: str, model_type: str) -> pd.DataFrame:
    """Load predictions for a given band and model from Supabase.

    Args:
        band (str): The band's canonical name (e.g., 'Phish').
        model_type (str): The model type ('CK+' or 'Notebook').

    Returns:
        pd.DataFrame: A DataFrame containing the predictions, properly sorted.
    """
    model_suffix = "ckplus" if model_type == "CK+" else "notebook"
    table_name = f"predictions_{model_suffix}"

    try:
        # Load data using the proper database utilities
        df = get_table_as_dataframe(table_name)

        if df.empty:
            st.warning(f"No data found in table '{table_name}' for band '{band}'")
            return pd.DataFrame()

        # Filter for the specific band
        df = df[df['band'].str.lower() == band.lower()].copy()

        if df.empty:
            st.warning(f"No data found for band '{band}' in table '{table_name}'")
            return pd.DataFrame()

        # Apply proper sorting based on model type
        if model_type == 'CK+':
            # Sort CK+ by ckplus_score descending
            df = df.sort_values('ckplus_score', ascending=False)
        elif model_type == 'Notebook':
            # Sort Notebook by times_played_last_year descending, then current_gap descending
            df = df.sort_values(['times_played_last_year', 'current_gap'], ascending=[False, False])

        # Limit to top 50 results
        df = df.head(50)

        return df

    except Exception as e:
        st.error(f"Error loading data from table '{table_name}': {str(e)}")
        return pd.DataFrame()


def format_dataframe(
    df: pd.DataFrame, expected_cols: list[str], display_cols: list[str]
) -> pd.DataFrame:
    """
    Format a dataframe by selecting expected columns and renaming them.

    Args:
        df: pandas DataFrame to format
        expected_cols: List of source column names to select
        display_cols: List of display column names to rename to

    Returns:
        pd.DataFrame: Formatted dataframe with selected and renamed columns
    """
    # Filter to only include columns that exist
    available_cols = [col for col in expected_cols if col in df.columns]
    if not available_cols:
        st.warning("No expected columns found in the data.")
        return df

    # Select and rename columns
    result = df[available_cols].copy()
    result.columns = display_cols[: len(available_cols)]
    result.index = range(1, len(result) + 1)
    result.index.name = "Rank"
    return result


def get_column_config(file_label: str, band: str) -> tuple[str, list[str], list[str]]:
    """
    Get the appropriate column configuration based on prediction method and band.
    Column names are mapped to match the actual Supabase schema.

    Args:
        file_label: String indicating prediction method ("CK+" or "Notebook")
        band: String indicating which band

    Returns:
        tuple: (display_label, expected_columns, display_columns)
    """
    if file_label == "CK+":
        display_label = "CK+"
        expected_columns = [
            "song_name",
            "times_played_total",
            "last_played_date",
            "current_gap",
            "avg_gap",
            "gap_ratio",
            "gap_z_score",
            "ckplus_score",
        ]
        display_columns = [
            "Song",
            "Times Played Overall",
            "LTP Date",
            "Current Gap",
            "Avg Gap",
            "Gap Ratio",
            "Gap Z-Score",
            "CK+ Score",
        ]
    elif file_label == "Notebook":
        display_label = NOTEBOOK_LABELS.get(band, "Notebook")
        # Use unified schema for all bands - matches the actual Supabase table structure
        expected_columns = [
            "song_name",
            "times_played_last_year",
            "last_played_date",
            "current_gap",
            "avg_gap",
            "median_gap",
        ]
        display_columns = [
            "Song",
            "Times Played Last Year",
            "LTP Date",
            "Current Gap",
            "Average Gap",
            "Median Gap",
        ]
    else:
        display_label = file_label
        # Default columns if needed - use unified schema
        expected_columns = [
            "song_name",
            "times_played_last_year",
            "last_played_date",
            "current_gap",
            "avg_gap",
            "median_gap",
        ]
        display_columns = [
            "Song",
            "Times Played Last Year",
            "LTP Date",
            "Current Gap",
            "Average Gap",
            "Median Gap",
        ]

    return display_label, expected_columns, display_columns
