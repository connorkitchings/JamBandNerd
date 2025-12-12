from __future__ import annotations

import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.web.components.common import (
    build_prediction_lookup,
    clean_song_name_for_display,
    compute_summary,
    format_show_header,
    get_prior_song_history,
    render_hero,
    render_setlist,
    render_summary_cards,
)
from jambandnerd.web.data import (
    fetch_available_prediction_dates,
    fetch_predictions_for_date,
    fetch_setlist_for_date,
)

MODEL_DISPLAY = {"notebook": "Notebook", "ckplus": "CK+"}


def display_historical_explorer(client: Client, band: str, model: str) -> None:
    """Display the historical prediction explorer."""
    st.markdown(
        "<h3 style='text-align: center;'>Historical Prediction Explorer</h3>",
        unsafe_allow_html=True,
    )

    # 1. Date Selection
    with st.spinner("Loading available shows..."):
        available_dates = fetch_available_prediction_dates(client, band, model)

    if not available_dates:
        st.warning(f"No prediction history available for {band}.")
        return

    # Use session state to persist selection if possible, or just default to 0
    # For now, simple selectbox
    selected_date = st.selectbox("Select a Show", available_dates)

    if not selected_date:
        return

    # 2. Fetch Data
    with st.spinner(f"Loading data for {selected_date}..."):
        # Fetch setlist
        setlist_df, show_details = fetch_setlist_for_date(client, band, selected_date)

        # Fetch predictions
        predictions_df, prediction_meta = fetch_predictions_for_date(
            client, band, model, str(selected_date)
        )

    if setlist_df.empty or show_details is None:
        st.warning(f"No setlist found for {band} on {selected_date}.")
        return

    # 3. Process Data
    header_text = format_show_header(show_details)

    # Prediction Lookup (Rank)
    # We filter for display logic similar to last_show if needed,
    # but build_prediction_lookup handles the rank mapping.
    # Note: last_show filters predictions_df[predictions_df["current_gap"] > 3] for display purposes
    # We should probably replicate that consistency.
    predictions_df_display = predictions_df.copy()
    if not predictions_df_display.empty and "current_gap" in predictions_df_display.columns:
        try:
            predictions_df_display = predictions_df_display[
                predictions_df_display["current_gap"] > 3
            ]
        except Exception:
            pass
    
    # Re-rank for display if we filtered
    if "rank" in predictions_df_display.columns:
        predictions_df_display = predictions_df_display.reset_index(drop=True)
        predictions_df_display["rank"] = predictions_df_display.index + 1

    prediction_ranks = build_prediction_lookup(predictions_df_display, band)

    # Gap Lookup (Bustouts) - Needs FULL predictions
    prediction_gaps = {}
    if not predictions_df.empty and "current_gap" in predictions_df.columns:
        for _, row in predictions_df.iterrows():
            name = clean_song_name_for_display(
                str(row.get("song_name", "")), band
            ).lower()
            if not name:
                continue
            gap_val = row.get("current_gap")
            try:
                gap = float(gap_val)
            except Exception:
                continue
            prediction_gaps[name] = gap

    # Prior History for Debuts
    prior_history = get_prior_song_history(client, band, selected_date)

    # Stats
    stats = compute_summary(
        setlist_df, prediction_ranks, prediction_gaps, prior_history, band
    )

    # Metadata
    prediction_meta = prediction_meta or {}
    predicted_at_raw = prediction_meta.get("created_at") or prediction_meta.get("inserted_at")
    predicted_at = (
        pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
    )
    predicted_at_str = (
        predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"
    )
    
    model_display = MODEL_DISPLAY.get(model, model.title())
    
    # Render
    render_hero(header_text, model_display, predicted_at_str, "N/A (Historical)")
    render_summary_cards(stats)
    
    if predictions_df.empty:
        st.info("No predictions found for this show (it might predate our prediction tracking).")
    
    render_setlist(
        setlist_df,
        prediction_ranks,
        prediction_gaps,
        band,
        debuts={name.lower() for name in stats["debuts"]},
        bustouts={name.lower() for name in stats["bustouts"]},
    )