from __future__ import annotations

import streamlit as st
from supabase import Client

# TODO: These imports and functions will be needed when this feature is fully implemented
# import pandas as pd
# from jambandnerd.web.data import fetch_predictions_for_date, fetch_setlist_for_date
# from jambandnerd.web.components.tabs.last_show import (
#     _clean_song_name_for_display,
#     display_setlist,
#     display_performance_summary,
# )


def display_historical_explorer(client: Client, band: str, model: str):
    """Display the historical prediction explorer."""
    # TODO: This feature is incomplete - missing helper functions from last_show.py
    # Once display_setlist, display_performance_summary, and _clean_song_name_for_display
    # are implemented, uncomment the code below
    st.warning("Historical Explorer feature is under development. Check back soon!")

    # st.markdown(f"<h3 style='text-align: center;'>Historical Prediction Explorer</h3>", unsafe_allow_html=True)
    #
    # # Date input for selecting a historical show
    # # show_date = st.date_input("Select a show date to explore")
    #
    # # if show_date:
    # #     with st.spinner(f"Loading data for {show_date}..."):
    # #         # Fetch predictions for the selected date
    # #         predictions_df = fetch_predictions_for_date(client, band, model, str(show_date))
    # #
    # #         # Fetch the actual setlist for the selected date
    # #         setlist_df, show_details = fetch_setlist_for_date(client, band, str(show_date))
    # #
    # #     if predictions_df.empty:
    # #         st.warning(f"No predictions found for {band} on {show_date}.")
    # #         return
    # #
    # #     if setlist_df.empty:
    # #         st.warning(f"No setlist found for {band} on {show_date}.")
    # #         return
    # #
    # #     st.markdown(f"<h4 style='text-align: center;'>Predictions vs. Actual Setlist</h4>", unsafe_allow_html=True)
    # #
    # #     # Create prediction lookup for highlighting
    # #     prediction_ranks: dict[str, int] = {}
    # #     if not predictions_df.empty and "song_name" in predictions_df.columns:
    # #         use_rank_col = "rank" in predictions_df.columns
    # #         for idx, row in predictions_df.iterrows():
    # #             normalized = _clean_song_name_for_display(str(row["song_name"]), band).lower()
    # #             if not normalized:
    # #                 continue
    # #             rank = int(row["rank"]) if use_rank_col and pd.notna(row["rank"]) else (idx + 1)
    # #             prediction_ranks[normalized] = rank
    # #
    # #     display_setlist(setlist_df, prediction_ranks, band)
    # #     st.divider()
    # #     display_performance_summary(setlist_df, prediction_ranks, band)
