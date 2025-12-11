from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.web.data import fetch_per_show_accuracy
from jambandnerd.web.theme import CHART_FOCUS_COLOR, CHART_SECONDARY_COLOR

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


def prepare_chart_data(accuracy_df: pd.DataFrame, k: int) -> pd.DataFrame:
    """Transform the accuracy data into a long-form DataFrame for charting."""
    recall_cols = [c for c in ["k10_recall", "k25_recall", "k50_recall"] if c in accuracy_df.columns]
    if not recall_cols:
        return pd.DataFrame()

    base_df = accuracy_df.sort_values("show_date", ascending=False).reset_index(drop=True)
    base_df["show_num"] = range(1, len(base_df) + 1)
    ks = [10, 25, 50]
    long_rows = []
    for idx, row in base_df.iterrows():
        for kk in ks:
            rc = f"k{kk}_recall"
            mc = f"k{kk}_matches"
            if rc in base_df.columns:
                long_rows.append({
                    "show_num": idx + 1,
                    "show_date": row.get("show_date"),
                    "venue_name": row.get("venue_name"),
                    "k": kk,
                    "recall": row.get(rc),
                    "matches": row.get(mc) if mc in base_df.columns else None,
                    "is_focus": kk == k,
                })
    
    if not long_rows:
        return pd.DataFrame()

    long_df = pd.DataFrame(long_rows)
    if "show_date" in long_df.columns:
        long_df["show_date_display"] = pd.to_datetime(long_df["show_date"]).dt.strftime("%Y-%m-%d")
    
    return long_df

def create_accuracy_chart(long_df: pd.DataFrame, k: int) -> alt.Chart:
    """Create the historical accuracy chart using Altair."""
    return (
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
                alt.value(CHART_FOCUS_COLOR),
                alt.value(CHART_SECONDARY_COLOR),
            ),
            opacity=alt.condition(
                "datum.is_focus == true", alt.value(1.0), alt.value(0.35)
            ),
            tooltip=[
                alt.Tooltip("show_date_display:N", title="Show Date"),
                alt.Tooltip("venue_name:N", title="Venue"),
                alt.Tooltip("k:N", title="K"),
                alt.Tooltip("recall:Q", title="Recall", format=".1%"),
                alt.Tooltip("matches:Q", title="Matches"),
            ],
        )
        .interactive()
        .properties(background="transparent", height=360)
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#374151",
            titleColor="#111827",
            gridColor="#E5E7EB",
            tickColor="#E5E7EB",
        )
    )

def display_summary_metrics(accuracy_df: pd.DataFrame):
    """Display the summary metrics for recall at different K values."""
    def fmt(val: float | None) -> str:
        return f"{val:.1%}" if val is not None else "N/A"

    vals = {}
    for k in [10, 25, 50]:
        col = f"k{k}_recall"
        vals[k] = accuracy_df[col].mean() if col in accuracy_df.columns else None

    st.markdown(
        f"""
        <div class="jbn-metric-chips">
            <div class="jbn-metric-chip jbn-metric-chip--10">
                <div class="jbn-metric-chip__label" style="text-align:center;">Recall @ Top 10</div>
                <div class="jbn-metric-chip__value" style="text-align:center;">{fmt(vals[10])}</div>
            </div>
            <div class="jbn-metric-chip jbn-metric-chip--25">
                <div class="jbn-metric-chip__label" style="text-align:center;">Recall @ Top 25</div>
                <div class="jbn-metric-chip__value" style="text-align:center;">{fmt(vals[25])}</div>
            </div>
            <div class="jbn-metric-chip jbn-metric-chip--50">
                <div class="jbn-metric-chip__label" style="text-align:center;">Recall @ Top 50</div>
                <div class="jbn-metric-chip__value" style="text-align:center;">{fmt(vals[50])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def display_historical_accuracy(client: Client, band: str, model: str, k: int):
    """Display the historical accuracy section and the model explanation."""
    model_display_name = MODEL_CONFIG.get(model, {}).get("display_name", model.title())
    st.markdown(
        f"<h3 style='text-align:center; margin-bottom:0.4rem;'>Historical Accuracy — {model_display_name}</h3>",
        unsafe_allow_html=True,
    )

    with st.spinner("Loading accuracy..."):
        accuracy_df = fetch_per_show_accuracy(client, band, model)

    if not accuracy_df.empty:
        num_shows = len(accuracy_df)
        min_date = pd.to_datetime(accuracy_df["show_date"].min()).strftime("%m/%d/%Y")
        max_date = pd.to_datetime(accuracy_df["show_date"].max()).strftime("%m/%d/%Y")

        display_summary_metrics(accuracy_df)
        st.markdown(
            f"<div style='text-align:center; color: var(--text-muted); margin: 6px 0 10px;'>Metrics based on the last {num_shows} completed shows ({min_date} to {max_date}).</div>",
            unsafe_allow_html=True,
        )

        long_df = prepare_chart_data(accuracy_df, k)
        if not long_df.empty:
            chart = create_accuracy_chart(long_df, k)
            st.altair_chart(chart, use_container_width=True)
            st.markdown(
                f"<div style='font-size:0.9em; color: var(--text-muted); text-align:center; margin-top:8px;'>Use the sidebar to change the focus K. Other Ks are shown in grey.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.warning(f"No accuracy data available for K={k}.")
    else:
        st.warning(
            "No per-show accuracy data found. Please run the backtesting scripts."
        )
