from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.config import STREAMLIT_CACHE_TTL

# This is a temporary solution. In the future, this should be moved to a more centralized location.
MODEL_CONFIG = {
    "notebook": {
        "display_name": "Notebook",
        "explanation": "Focuses on songs most frequently played in the last year, excluding those played in the last three shows. It surfaces in-rotation songs and provides last played date and current gap context.",
        "columns": {
            "rank": "Rank",
            "song_name": "Song",
            "plays_past_year": "Plays in Last Year",
            "LTP": "Last Played",
            "current_gap": "Current Gap",
        },
    },
    "ckplus": {
        "display_name": "CK+",
        "explanation": "Gap-based statistical predictor that ranks songs by how overdue they are, using historical show-to-show gaps, recency, and reliability scaling. It emphasizes songs likely to return given typical gaps.",
        "columns": {
            "rank": "Rank",
            "song_name": "Song",
            "LTP": "Last Played",
            "current_gap": "Current Gap",
            "avg_gap": "Avg Gap",
            "gap_ratio": "Gap Ratio",
            "gap_z_score": "Gap Z-Score",
            "ckplus_score": "CK+ Score",
        },
    },
}


def display_band_leaderboard(client: Client, model: str, k: int):
    """Display a comparison of model accuracy across all bands."""
    st.markdown(
        f"<h3 style='text-align: center;'>{MODEL_CONFIG[model]['display_name']} Model: Top-{k} Accuracy Leaderboard</h3>",
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=STREAMLIT_CACHE_TTL)
    def fetch_all_bands_accuracy(_db_client: Client, model: str) -> pd.DataFrame:
        try:
            model_version = f"{model}_v1"
            response = (
                _db_client.table("accuracy_per_show")
                .select("band, show_date, k10_recall, k25_recall, k50_recall")
                .eq("model_version", model_version)
                .execute()
            )
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to fetch accuracy data for all bands: {e}")
            return pd.DataFrame()

    with st.spinner("Loading band leaderboard..."):
        accuracy_df = fetch_all_bands_accuracy(client, model)

    if not accuracy_df.empty:
        recall_col = f"k{k}_recall"
        if recall_col not in accuracy_df.columns:
            st.warning(f"Recall data for K={k} not available.")
            return

        # Calculate average recall and number of shows per band
        avg_recall_by_band = (
            accuracy_df.groupby("band")
            .agg(avg_recall=(recall_col, "mean"), num_shows=("show_date", "nunique"))
            .reset_index()
        )
        avg_recall_by_band = avg_recall_by_band.sort_values(
            by="avg_recall", ascending=False
        )

        chart = (
            alt.Chart(avg_recall_by_band)
            .mark_bar()
            .encode(
                x=alt.X("band:N", title="Band", sort="-y"),
                y=alt.Y(
                    "avg_recall:Q",
                    title=f"Average Recall @ Top {k}",
                    axis=alt.Axis(format=".0%"),
                ),
                color=alt.Color("band:N", legend=None),
                tooltip=[
                    alt.Tooltip("band:N", title="Band"),
                    alt.Tooltip("avg_recall:Q", title="Avg. Recall", format=".1%"),
                    alt.Tooltip("num_shows:Q", title="# of Shows"),
                ],
            )
            .properties(title=f"Average Top-{k} Recall by Band")
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No accuracy data available to compare bands.")
