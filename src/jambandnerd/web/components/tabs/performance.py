from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.web.data import fetch_per_show_accuracy

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


@st.cache_data
def get_model_explanation(model_slug: str) -> str:
    """Fetches the markdown explanation for a given model."""
    # In a real-world scenario, this would read from the file system.
    # Here, we embed the content directly since we've already read it.
    explanations = {
        "notebook": "# Notebook Model (Frequency-Based)\n\n### Overview\n\nThis model is the baseline predictor, designed to be simple, transparent, and fast. It operates on the core assumption that songs played frequently in the recent past are more likely to be played again soon.\n\n### Logic & Features\n\nGiven a reference show date (the show we are predicting for), the model performs the following steps:\n\n1.  **Define a 1-Year Window**: It looks at all shows that occurred in the 365 days immediately preceding the *last completed show*.\n2.  **Count Plays**: It counts how many times each song was played within that one-year window. This count (`plays_past_year`) is the primary ranking feature.\n3.  **Exclude Recent Songs**: To avoid predicting songs that were just played, it identifies all songs performed in the **last three completed shows** and removes them from the candidate list.\n4.  **Calculate Current Gap**: For each remaining song, it calculates the `current_gap`, which is the number of shows that have passed since the song was last played.\n5.  **Rank and Predict**: Songs are ranked primarily by `plays_past_year` (descending). Any ties are broken by `current_gap` (descending, so songs with a larger gap are ranked higher).\n\nThe result is a list of songs that are both popular in the current rotation and not *too* recent, making them strong candidates for the next show.\n",
        "ckplus": '# CK+ Model (Gap-Based)\n\n### Overview\n\nThe CK+ model is a gap-based statistical predictor that ranks songs by how "overdue" they are to be played. It complements the frequency-based Notebook model by focusing on historical performance gaps rather than recent play counts.\n\n### Logic & Features\n\nThe model\'s core logic is based on analyzing the number of shows that typically pass between two performances of the same song.\n\n1.  **Define a 5-Year Window**: The model uses a five-year historical window to calculate long-term gap statistics for each song.\n2.  **Calculate Gap Statistics**: For each song, it computes:\n    *   `avg_gap`: The average number of shows between plays.\n    *   `std_gap`: The standard deviation of the gaps, measuring how consistent the song\'s rotation is.\n    *   `current_gap`: The number of shows that have passed since the song was last played.\n3.  **Calculate Core Ratios**:\n    *   `gap_ratio`: Calculated as `current_gap / avg_gap`. A ratio greater than 1.0 suggests a song is "overdue."\n    *   `gap_z_score`: Measures how many standard deviations the `current_gap` is from the `avg_gap`. A high positive Z-score indicates a statistically significant gap.\n4.  **Apply Filters**:\n    *   **Minimum Plays**: Songs with very few plays in the 5-year window are excluded.\n    *   **Retirement Heuristic**: Songs with an extremely large `current_gap` are assumed to be "retired" and are excluded. This threshold is configured on a per-band basis.\n5.  **Final Scoring & Ranking**: The final `ckplus_score` is a weighted blend of the `gap_ratio` and the `gap_z_score`, which is then scaled by a "reliability" term. This term gives less weight to songs with very few plays or a high standard deviation (erratic history), preventing them from being ranked too highly.\n',
    }
    return explanations.get(model_slug, "No explanation available for this model.")


def display_historical_accuracy(client: Client, band: str, model: str, k: int):
    """Display the historical accuracy section and the model explanation."""
    model_display_name = MODEL_CONFIG.get(model, {}).get("display_name", model.title())
    st.divider()
    st.markdown(
        f"<h3 style='text-align: center;'>Historical Accuracy - {model_display_name}</h3>",
        unsafe_allow_html=True,
    )

    with st.spinner("Loading accuracy..."):
        accuracy_df = fetch_per_show_accuracy(client, band, model)

    if not accuracy_df.empty:
        num_shows = len(accuracy_df)

        # --- Add Date Range Context ---
        min_date = pd.to_datetime(accuracy_df["show_date"].min()).strftime("%Y-%m-%d")
        max_date = pd.to_datetime(accuracy_df["show_date"].max()).strftime("%Y-%m-%d")

        st.markdown(
            f"<p style='text-align: center; color: gray;'>Metrics based on the last {num_shows} completed shows (from {min_date} to {max_date}).</p>",
            unsafe_allow_html=True,
        )

        # Aggregate metrics for all K values
        ks = [10, 25, 50]
        cols_recall = st.columns(len(ks))
        for i, val in enumerate(ks):
            recall_col = f"k{val}_recall"
            avg_recall = (
                accuracy_df[recall_col].mean()
                if recall_col in accuracy_df.columns
                else None
            )
            cols_recall[i].metric(
                f"Recall @ Top {val}",
                f"{avg_recall:.1%}" if avg_recall is not None else "N/A",
            )

        # Chart for all Ks, highlight selected K and grey out others
        recall_cols = [
            c
            for c in ["k10_recall", "k25_recall", "k50_recall"]
            if c in accuracy_df.columns
        ]
        if recall_cols:
            base_df = accuracy_df.sort_values("show_date", ascending=False).reset_index(
                drop=True
            )
            base_df["show_num"] = range(1, len(base_df) + 1)
            ks = [10, 25, 50]
            long_rows = []
            for idx, row in base_df.iterrows():
                for kk in ks:
                    rc = f"k{kk}_recall"
                    mc = f"k{kk}_matches"
                    if rc in base_df.columns:
                        long_rows.append(
                            {
                                "show_num": idx + 1,
                                "show_date": row.get("show_date"),
                                "k": kk,
                                "recall": row.get(rc),
                                "matches": row.get(mc)
                                if mc in base_df.columns
                                else None,
                                "is_focus": kk == k,
                            }
                        )
            if long_rows:
                long_df = pd.DataFrame(long_rows)
                # Convert show_date to string format to avoid timezone-related off-by-one issues
                # The :T temporal type causes Altair to apply timezone conversion
                if "show_date" in long_df.columns:
                    long_df["show_date_display"] = pd.to_datetime(
                        long_df["show_date"]
                    ).dt.strftime("%Y-%m-%d")
                line = (
                    alt.Chart(long_df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(
                            "show_num:Q",
                            title="Show # (Most Recent First)",
                            scale=alt.Scale(reverse=True),
                        ),
                        y=alt.Y(
                            "recall:Q",
                            title=f"Recall @ Top {k}",
                            scale=alt.Scale(domain=[0, 1]),
                            axis=alt.Axis(format="%"),
                        ),
                        detail="k:N",
                        color=alt.condition(
                            "datum.is_focus == true",
                            alt.value("#1f77b4"),
                            alt.value("#CCCCCC"),
                        ),
                        opacity=alt.condition(
                            "datum.is_focus == true", alt.value(1.0), alt.value(0.35)
                        ),
                        tooltip=[
                            alt.Tooltip("show_date_display:N", title="Show Date"),
                            alt.Tooltip("k:N", title="K"),
                            alt.Tooltip("recall:Q", title="Recall", format=".1%"),
                            alt.Tooltip("matches:Q", title="Matches"),
                        ],
                    )
                    .interactive()
                )
                st.altair_chart(line, use_container_width=True)
                st.markdown(
                    "<div style='font-size:0.9em; color: gray; text-align:center; margin-top:8px;'>Use the sidebar to change the focus K. Other Ks are shown in grey.</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.warning(f"No accuracy data available for K={k}.")
    else:
        st.warning(
            "No per-show accuracy data found. Please run the backtesting scripts."
        )

    # --- Display Model Explanation ---
    st.divider()
    st.markdown(
        f"<h3 style='text-align: center;'>How This Model Works - {model_display_name}</h3>",
        unsafe_allow_html=True,
    )
    explanation_content = get_model_explanation(model)
    st.markdown(explanation_content, unsafe_allow_html=True)
