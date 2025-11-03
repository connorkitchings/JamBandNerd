from __future__ import annotations

from datetime import date
from typing import List, Optional

import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.web.data import fetch_predictions, fetch_show_details_by_date, fetch_um_upcoming_show, fetch_wsp_upcoming_show

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

    if not predictions_df.empty:
        show_details = fetch_show_details_by_date(client, ref_date, band=band)
        show_date_obj: Optional[date] = None

        if ref_date:
            try:
                show_date_obj = pd.to_datetime(ref_date).date()
            except Exception:
                show_date_obj = None

        header_prefix = "Next Show"
        date_str = ""
        venue_bits: List[str] = []

        upcoming_details: Optional[dict] = None
        if band == "um":
            upcoming_details = fetch_um_upcoming_show(client)
        elif band == "wsp":
            upcoming_details = fetch_wsp_upcoming_show(client)

        if upcoming_details:
            start_str = (
                upcoming_details.get("starts_at_local")
                or upcoming_details.get("starts_at")
                or upcoming_details.get("show_date")
            )
            try:
                start_dt = pd.to_datetime(start_str).date() if start_str else None
            except Exception:
                start_dt = None
            if start_dt:
                date_str = start_dt.strftime("%m/%d/%Y")
            venue = upcoming_details.get("venue_name")
            city = upcoming_details.get("city") or upcoming_details.get("venue_city")
            region = upcoming_details.get("region") or upcoming_details.get("venue_state")
            country = upcoming_details.get("country") or upcoming_details.get("venue_country")
            if venue:
                venue_bits.append(venue)
            location_parts = [part for part in [city, region] if part]
            if location_parts:
                venue_bits.append(", ".join(location_parts))
            if country and country not in venue_bits:
                venue_bits.append(country)
        else:
            if show_details:
                venue = show_details.get("venue_name") or show_details.get("venue")
                city = show_details.get("venue_city") or show_details.get("city")
                state = show_details.get("venue_state") or show_details.get("state")
                if venue:
                    venue_bits.append(venue)
                if city and state:
                    venue_bits.append(f"{city}, {state}")
            today = date.today()
            if show_date_obj and show_date_obj < today:
                header_prefix = "Most Recent Show"
            date_str = show_date_obj.strftime("%m/%d/%Y") if show_date_obj else ""

        left_header = f"{header_prefix}: {date_str}" if date_str else header_prefix
        if venue_bits:
            left_header += f" — {" • ".join(venue_bits)}"
        st.markdown(f"<h4 style='text-align: center;'>{left_header}</h4>", unsafe_allow_html=True)

        st.divider()

        display_df = format_predictions_df(predictions_df.head(50), model)

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=900)

        predicted_at_raw = meta.get("predicted_at")
        predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
        predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"
        model_version = meta.get("model_version", "v1")
        st.markdown(
            f"<div style='text-align: center; color: gray;'>Model: {model_display_name} ({model_version}) · Predicted: {predicted_at_str}</div>",
            unsafe_allow_html=True,
        )

    else:
        st.warning(
            "No predictions found for the selected model. Please run the prediction scripts first."
        )
