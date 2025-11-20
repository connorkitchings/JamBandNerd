from __future__ import annotations

import streamlit as st

from jambandnerd.db.connection import get_supabase_client
from jambandnerd.web.components.sidebar import (
    display_sidebar,
    get_initial_selection_from_url,
    sync_query_params,
)
from jambandnerd.web.components.tabs.compare import display_band_comparison
from jambandnerd.web.components.tabs.last_show import display_last_show_setlist
from jambandnerd.web.components.tabs.performance import display_historical_accuracy
from jambandnerd.web.components.tabs.predictions import display_predictions
from jambandnerd.web.config import ACTIVE_BANDS, BAND_CONFIG, MODEL_CONFIG


def main():
    """Main application entry point."""
    st.set_page_config(page_title="JamBandNerd", layout="wide")
    st.markdown("<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True)

    st.markdown("""
    <style>
        :root {
            --primary-color: #F63366; /* Streamlit's default primary color */
            --success-color: #4CAF50; /* Green for Top 10 */
            --warning-color: #FFD700; /* Gold for Top 25 */
            --info-color: #D3D3D3;    /* Light Grey for Top 50 */
            --background-color: #F0F2F6; /* Light grey for tab background */
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            justify-content: space-around;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: var(--background-color);
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
            color: var(--primary-color); /* Highlight selected tab with primary color */
        }
        button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
            font-size: 1.1rem;
        }
        /* Custom classes for badges */
        .badge-top10 {
            background-color: var(--success-color);
            color: white;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }
        .badge-top25 {
            background-color: var(--warning-color);
            color: black;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }
        .badge-top50 {
            background-color: var(--info-color);
            color: black;
            padding: 2px 4px;
            border-radius: 3px;
        }
    </style>""", unsafe_allow_html=True)

    # Read initial selection from URL with sensible defaults
    defaults = {
        "band": ACTIVE_BANDS[0],
        "model": next(iter(MODEL_CONFIG.keys())),
        "k": 50,
    }
    initial = get_initial_selection_from_url(defaults["band"], defaults["model"], defaults["k"])
    selected_band, selected_model, selected_k = display_sidebar(
        initial_band=initial["band"],
        initial_model=initial["model"],
        initial_k=initial["k"],
    )
    # Keep URL in sync with current selection
    sync_query_params(selected_band, selected_model, selected_k)

    # Display centered band marker just under the title
    band_display_name = BAND_CONFIG.get(selected_band, {}).get("display_name", selected_band.title())
    st.markdown(
        f"<h2 style='text-align: center; color: #666; margin-top: -10px; margin-bottom: 20px;'>{band_display_name}</h2>",
        unsafe_allow_html=True
    )

    try:
        supabase_client = get_supabase_client()

        # Use tabs for a cleaner layout
        tab1, tab2, tab3, tab4 = st.tabs(["Predictions", "Last Show Analysis", "Model Performance", "Compare Bands"])

        with tab1:
            display_predictions(supabase_client, selected_band, selected_model)

        with tab2:
            st.markdown(
                "<h3 style='text-align: center;'>Last Show Setlist</h3>",
                unsafe_allow_html=True,
            )
            display_last_show_setlist(supabase_client, selected_band, selected_model)

        with tab3:
            display_historical_accuracy(
                supabase_client, selected_band, selected_model, selected_k
            )

        with tab4:
            display_band_comparison(supabase_client, selected_model, selected_k)

    except Exception as e:
        st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
