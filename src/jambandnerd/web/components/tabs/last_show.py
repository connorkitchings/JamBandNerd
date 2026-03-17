from __future__ import annotations

from typing import Any

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
    fetch_last_collection_time,
    fetch_last_show_setlist,
    fetch_predictions,
    fetch_predictions_for_date,
)

# Temporary in-file configuration until centralized
MODEL_DISPLAY = {"notebook": "Notebook", "ckplus": "CK+"}


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_last_show_data(_client: Client, band: str, model: str) -> dict[str, Any]:
    """Fetch all necessary data for the last show analysis from Supabase."""
    setlist_df, show_details = fetch_last_show_setlist(_client, band)

    if setlist_df.empty or show_details is None:
        return {"setlist": pd.DataFrame(), "show_details": None}

    show_date = show_details.get("show_date")

    predictions_df = pd.DataFrame()
    if show_date:
        predictions_df, _ = fetch_predictions_for_date(
            _client, band, model, str(pd.to_datetime(show_date).date())
        )
    if predictions_df.empty:
        latest_df, _, _ = fetch_predictions(_client, band, model)
        predictions_df = latest_df

    collection_time = fetch_last_collection_time(_client, band)
    _, _, prediction_meta = fetch_predictions(_client, band, model)
    predicted_at_raw = prediction_meta.get("predicted_at")

    return {
        "setlist": setlist_df,
        "show_details": show_details,
        "predictions": predictions_df,
        "collection_time": collection_time,
        "predicted_at": predicted_at_raw,
        "show_date": show_date,
    }


def display_last_show_setlist(client: Client, band: str, model: str) -> None:
    """Display the last show's setlist with prediction highlights and metrics."""
    with st.spinner("Loading last show setlist..."):
        data = get_last_show_data(client, band, model)

    setlist_df = data["setlist"]
    show_details = data["show_details"]

    if setlist_df.empty or show_details is None:
        st.warning("No recent setlist data available.")
        return

    header_text = format_show_header(show_details)
    predictions_df = data["predictions"]
    predictions_df = predictions_df.copy()
    if not predictions_df.empty and "current_gap" in predictions_df.columns:
        try:
            predictions_df = predictions_df[predictions_df["current_gap"] > 3]
        except Exception:
            pass
    if "rank" in predictions_df.columns:
        predictions_df = predictions_df.reset_index(drop=True)
        predictions_df["rank"] = predictions_df.index + 1

    prediction_ranks = build_prediction_lookup(predictions_df, band)

    # Build gap lookup from ORIGINAL predictions (before filtering) for bustout detection
    # We need ALL gaps, not just those with gap > 3, to detect bustouts correctly
    original_predictions = data["predictions"]
    prediction_gaps = {}
    if not original_predictions.empty and "current_gap" in original_predictions.columns:
        for _, row in original_predictions.iterrows():
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

    prior_history = get_prior_song_history(client, band, data.get("show_date"))
    stats = compute_summary(
        setlist_df, prediction_ranks, prediction_gaps, prior_history, band
    )

    predicted_at_raw = data.get("predicted_at")
    predicted_at = (
        pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
    )
    predicted_at_str = (
        predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"
    )
    collection_time = data.get("collection_time")
    collection_str = (
        pd.to_datetime(collection_time).strftime("%Y-%m-%d %H:%M")
        if collection_time
        else "unknown"
    )
    model_display = MODEL_DISPLAY.get(model, model.title())

    render_hero(header_text, model_display, predicted_at_str, collection_str)
    render_summary_cards(stats)
    render_setlist(
        setlist_df,
        prediction_ranks,
        prediction_gaps,
        band,
        debuts={name.lower() for name in stats["debuts"]},
        bustouts={name.lower() for name in stats["bustouts"]},
    )
