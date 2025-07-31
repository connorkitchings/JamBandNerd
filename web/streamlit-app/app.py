"""Streamlit app to publish band song prediction data from the predictions folders within each band folder in 3 - Data.

Features:
- Dynamic band selection
- Loads and displays prediction CSVs for each band
- Responsive, modern UI

Author: GPT-4
"""

import streamlit as st
from constants import BAND_DISPLAY_NAMES
from data_loader import (
    format_dataframe,
    get_column_config,
    load_predictions_from_supabase,
)
from ui_components import display_disclaimer, display_method_explanation


def main() -> None:
    """Main application function."""
    # Configure the app
    st.set_page_config(page_title="Jam Band Nerd", page_icon="🎶", layout="wide")

    # Custom CSS for better color scheme
    st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stSelectbox > div > div {
        background-color: #262730;
        color: #fafafa;
    }
    .stDataFrame {
        background-color: #262730;
    }
    h1 {
        color: #fafafa;
        text-align: center;
        padding: 1rem 0;
    }
    h3 {
        color: #fafafa;
        text-align: center;
    }
    .stMarkdown {
        color: #fafafa;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        "<h1 style='text-align: center;'>Jam Band Nerd</h1>", unsafe_allow_html=True
    )

    # --- BAND AND MODEL SELECTION ---
    # Only allow Goose, Phish, and WSP (Widespread Panic) for selection
    allowed_bands = ["Phish", "Goose", "WSP"]
    band_display_map = {BAND_DISPLAY_NAMES.get(b, b.replace("'s", "")): b for b in allowed_bands}
    band_display_names = sorted(band_display_map.keys())  # Sort alphabetically
    selected_display = st.sidebar.selectbox("Select Band", band_display_names)
    band = band_display_map[selected_display]

    # Show 'CK+', and 'Notebook' prediction models
    model_options = ["CK+", "Notebook"]
    file_label = st.sidebar.selectbox("Select Prediction Method", model_options)

    # Display method explanation
    display_method_explanation(file_label)

    # --- Prediction Data Loading ---
    try:
        df = load_predictions_from_supabase(band, file_label)
        # Data is already limited to 50 rows and properly sorted in the data loader
    except Exception as e:
        st.error(f"Error loading prediction data from Supabase: {str(e)}")
        df = None

    if df is not None and not df.empty:
        # Get column configuration and format dataframe
        display_label, expected_columns, display_columns = get_column_config(
            file_label, band
        )
        df = format_dataframe(df, expected_columns, display_columns)

        # Display header with band and method
        st.markdown(
            f"<h3 style='text-align: center;'>{BAND_DISPLAY_NAMES.get(band, band)} — {display_label}</h3>",
            unsafe_allow_html=True,
        )

        # Display the dataframe
        st.dataframe(df, use_container_width=True, height=1000)

        # Display disclaimer
        display_disclaimer()
    else:
        st.info("No data to display.")


# Run the main application
if __name__ == "__main__":
    main()
