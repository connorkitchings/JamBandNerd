from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union

import altair as alt
import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.db.connection import get_supabase_client

# --- Configuration ---

EXCLUDED_SHOW_DATES = {"2025-08-13"}

BAND_CONFIG = {
    "goose": {
        "display_name": "Goose",
        "shows_table": "goose_shows_raw",
    },
    "phish": {
        "display_name": "Phish",
        "shows_table": "phish_shows_raw",
    },
    "wsp": {
        "display_name": "Widespread Panic",
        "shows_table": "wsp_shows_raw",
    },
}

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

# (Logos removed for a cleaner header)

# --- Data Fetching ---


@st.cache_data(ttl=60)
def fetch_predictions(
    _db_client: Client, band: str, model: str
) -> tuple[pd.DataFrame, str | None, dict]:
    """Fetch the latest predictions for a given band from the unified table."""
    try:
        table_name = f"predictions_{model}"
        query = _db_client.table(table_name).select("*").eq("band", band)
        for d in EXCLUDED_SHOW_DATES:
            query = query.neq("reference_date", d)
        latest_response = query.order("reference_date", desc=True).limit(1).execute()
        if not latest_response.data:
            return pd.DataFrame(), None, {}

        row = latest_response.data[0]
        reference_date = row.get("reference_date")
        predictions_json = row.get("predictions")

        if isinstance(predictions_json, str):
            predictions_parsed = json.loads(predictions_json)
        else:
            predictions_parsed = predictions_json or []

        df = pd.DataFrame(predictions_parsed)
        if "last_played_date" in df.columns and "LTP" not in df.columns:
            df.rename(columns={"last_played_date": "LTP"}, inplace=True)

        return df, reference_date, row
    except Exception as e:
        st.error(f"Failed to fetch predictions: {e}")
        return pd.DataFrame(), None, {}


@st.cache_data(ttl=60)
def fetch_per_show_accuracy(
    _db_client: Client, band: str, model: str, limit: int = 100
) -> pd.DataFrame:
    """Fetch the last N per-show accuracy records for charting."""
    try:
        model_version = f"{model}_v1"
        response = (
            _db_client.table("accuracy_per_show")
            .select("*")
            .eq("band", band)
            .eq("model_version", model_version)
            .order("show_date", desc=True)
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch per-show accuracy: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_show_details_by_date(
    _db_client: Client, reference_date: str | None, band: str
) -> dict | None:
    """Fetch venue details for the given reference show date."""
    if not reference_date or band not in BAND_CONFIG:
        return None
    try:
        primary_table = BAND_CONFIG[band]["shows_table"]
        candidate_tables = [primary_table]
        # Fallback table names commonly used for Phish
        if band == "phish":
            for alt in ["phish_raw_shows", "phish_shows"]:
                if alt not in candidate_tables:
                    candidate_tables.append(alt)

        for tbl in candidate_tables:
            # Try show_date first
            try:
                resp = (
                    _db_client.table(tbl)
                    .select("*")
                    .eq("show_date", reference_date)
                    .limit(1)
                    .execute()
                )
                if resp.data:
                    return resp.data[0]
            except Exception:
                pass

            # Then try showdate (Phish schema)
            try:
                resp = (
                    _db_client.table(tbl)
                    .select("*")
                    .eq("showdate", reference_date)
                    .limit(1)
                    .execute()
                )
                if resp.data:
                    return resp.data[0]
            except Exception:
                pass
        return None
    except Exception:
        return None


@st.cache_data
def fetch_last_collection_time(_db_client: Client, band: str) -> str | None:
    """Fetch the most recent collection run timestamp."""
    try:
        resp = (
            _db_client.table("collection_runs")
            .select("created_at")
            .eq("band", band)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0].get("created_at") if resp.data else None
    except Exception:
        return None


# --- UI Components ---


def display_sidebar() -> tuple[str, str, int]:
    """Render the sidebar and return selected options."""
    st.sidebar.title("JamBandNerd")

    band_display_names = [config["display_name"] for config in BAND_CONFIG.values()]
    selected_band_display = st.sidebar.selectbox("Select a Band", band_display_names)
    selected_band_slug = next(
        slug
        for slug, config in BAND_CONFIG.items()
        if config["display_name"] == selected_band_display
    )

    model_display_names = [config["display_name"] for config in MODEL_CONFIG.values()]
    selected_model_display = st.sidebar.selectbox("Select a Model", model_display_names)
    selected_model_slug = next(
        slug
        for slug, config in MODEL_CONFIG.items()
        if config["display_name"] == selected_model_display
    )

    # Compact model explanation with tooltip-like hint
    st.sidebar.caption(f"{selected_model_display}: {MODEL_CONFIG[selected_model_slug]['explanation']}")

    k_options = [10, 25, 50]
    selected_k = st.sidebar.selectbox(
        "K for Accuracy (Top-K)",
        k_options,
        index=2,
        help="Number of top-ranked songs considered for the recall metric.",
    )
    st.sidebar.caption(
        "Top-K: Of the songs actually played, the fraction that appear in the Top-K predictions."
    )

    return selected_band_slug, selected_model_slug, selected_k


def format_predictions_df(df: pd.DataFrame, model: str) -> pd.DataFrame:
    """Format the prediction dataframe for display."""
    if df.empty or model not in MODEL_CONFIG:
        return pd.DataFrame()

    config = MODEL_CONFIG[model]
    cols_to_display = [col for col in config["columns"] if col in df.columns]
    display_df = df[cols_to_display]
    return display_df.rename(columns=config["columns"])


def display_predictions(client: Client, band: str, model: str):
    """Display the main predictions view."""
    with st.spinner("Loading predictions..."):
        predictions_df, ref_date, meta = fetch_predictions(client, band, model)

    model_display_name = MODEL_CONFIG.get(model, {}).get("display_name", model.title())

    # Header without band logo; compact metadata

    if not predictions_df.empty:
        show_details = fetch_show_details_by_date(client, ref_date, band=band)
        date_str = pd.to_datetime(ref_date).strftime("%m/%d/%Y") if ref_date else ""
        venue_bits = []
        if show_details:
            venue = show_details.get("venue_name") or show_details.get("venue")
            city = show_details.get("venue_city") or show_details.get("city")
            state = show_details.get("venue_state") or show_details.get("state")
            if venue:
                venue_bits.append(venue)
            if city and state:
                venue_bits.append(f"{city}, {state}")
        left_header = f"Next Show: {date_str}"
        if venue_bits:
            left_header += f" — {' • '.join(venue_bits)}"
        st.markdown(f"<h4 style='text-align: center;'>{left_header}</h4>", unsafe_allow_html=True)

        st.markdown("---")
        # Always display up to top 50 songs
        display_df = format_predictions_df(predictions_df.head(50), model)
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=700)
        # Caption under table: Model and Predicted timestamp (centered)
        predicted_at_raw = meta.get("predicted_at")
        predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
        predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"
        model_version = meta.get("model_version", "v1")
        st.markdown(
            f"<div style='text-align: center; color: gray;'>Model: {model_display_name} ({model_version}) · Predicted: {predicted_at_str}</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            label="Download CSV",
            data=display_df.to_csv(index=False),
            file_name=f"{band}_{model}_predictions_{ref_date or 'latest'}.csv",
            mime="text/csv",
        )
    else:
        st.warning(
            "No predictions found for the selected model. Please run the prediction scripts first."
        )


def display_historical_accuracy(client: Client, band: str, model: str, k: int):
    """Display the historical accuracy section."""
    model_display_name = MODEL_CONFIG.get(model, {}).get("display_name", model.title())
    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align: center;'>Historical Accuracy - {model_display_name}</h3>",
        unsafe_allow_html=True,
    )

    with st.spinner("Loading accuracy..."):
        accuracy_df = fetch_per_show_accuracy(client, band, model)
    if not accuracy_df.empty and "show_date" in accuracy_df.columns:
        accuracy_df = accuracy_df[
            ~accuracy_df["show_date"].astype(str).isin(EXCLUDED_SHOW_DATES)
        ].copy()

    if not accuracy_df.empty:
        num_shows = len(accuracy_df)
        st.markdown(
            f"<p style='text-align: center; color: gray;'>Metrics based on the last {num_shows} completed shows.</p>",
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
        recall_cols = [c for c in ["k10_recall", "k25_recall", "k50_recall"] if c in accuracy_df.columns]
        if recall_cols:
            base_df = accuracy_df.sort_values("show_date", ascending=False).reset_index(drop=True)
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
                                "matches": row.get(mc) if mc in base_df.columns else None,
                                "is_focus": kk == k,
                            }
                        )
            if long_rows:
                long_df = pd.DataFrame(long_rows)
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
                        opacity=alt.condition("datum.is_focus == true", alt.value(1.0), alt.value(0.35)),
                        tooltip=[
                            alt.Tooltip("show_date:T", title="Show Date"),
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


# --- Main App ---


def main():
    """Main application entry point."""
    st.set_page_config(page_title="JamBandNerd", layout="wide")
    st.markdown("<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True)

    selected_band, selected_model, selected_k = display_sidebar()

    try:
        supabase_client = get_supabase_client()
        display_predictions(supabase_client, selected_band, selected_model)
        display_historical_accuracy(
            supabase_client, selected_band, selected_model, selected_k
        )
    except Exception as e:
        st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
