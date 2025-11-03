from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.web.data import fetch_last_show_setlist, fetch_predictions_for_date, fetch_predictions, fetch_last_collection_time

# This is a temporary solution. In the future, this should be moved to a more centralized location.
WSP_ARTIST_MARKERS = {
    "david bromberg band",
    "new riders of the purple sage",
    "j.j. cale",
    "the doors",
}

def _clean_song_name_for_display(name: str, band: str) -> str:
    """Normalize song names for display/highlighting, stripping unwanted artist credits."""
    if not isinstance(name, str):
        return ""
    cleaned = name.rstrip('>').rstrip('*').strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if band == "wsp":
        if lowered in WSP_ARTIST_MARKERS:
            return ""
        for marker in WSP_ARTIST_MARKERS:
            pattern = re.compile(rf"\s*,\s*{re.escape(marker)}\s*$", re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
    cleaned = cleaned.strip()
    if not cleaned:
        return ""
    return cleaned


def display_last_show_setlist(client: Client, band: str, model: str):
    """Display the last show's setlist with prediction highlights."""
    with st.spinner("Loading last show setlist..."):
        setlist_df, show_details = fetch_last_show_setlist(client, band)

    if setlist_df.empty or show_details is None:
        st.warning("No recent setlist data available.")
        return

    # Extract show information
    if band == "phish":
        show_date_key = "show_date"
    elif band == "goose":
        show_date_key = "show_date"  # Goose shows table uses show_date (normalized from showdate)
    else:  # WSP
        show_date_key = "show_date"

    show_date = show_details.get(show_date_key)

    if show_date:
        formatted_date = pd.to_datetime(show_date).strftime("%m/%d/%Y")
    else:
        formatted_date = "Unknown Date"

    # Get venue information
    venue = show_details.get("venue_name") or show_details.get("venue") or show_details.get("venuename")
    if not venue:
        venue = "Unknown Venue"
    city = show_details.get("venue_city") or show_details.get("city") or ""
    state = show_details.get("venue_state") or show_details.get("state") or ""

    # Construct the prominent header
    header_parts = []
    if formatted_date != "Unknown Date":
        header_parts.append(formatted_date)
    if venue != "Unknown Venue":
        header_parts.append(venue)
    if city and state:
        header_parts.append(f"{city}, {state}")
    elif city:
        header_parts.append(city)
    elif state:
        header_parts.append(state)

    prominent_header = " • ".join(header_parts)
    st.markdown(f"<h4 style='text-align: center;'>{prominent_header}</h4>", unsafe_allow_html=True)

    st.divider()

    

    # Fetch collection and prediction times for this specific show date
    collection_time = fetch_last_collection_time(client, band) # This fetches the latest, not necessarily for this show
    # To get prediction time for this show, we need to fetch predictions for this specific date
    _, _, prediction_meta = fetch_predictions(client, band, model) # This fetches latest predictions
    predicted_at_raw = prediction_meta.get("predicted_at")
    predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
    predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"

    

        # Retrieve predictions for this specific show_date if available
    predictions_df_for_show = pd.DataFrame()
    if show_date:
        predictions_df_for_show = fetch_predictions_for_date(client, band, model, str(pd.to_datetime(show_date).date()))

    # Fallback to latest predictions if historical not available
    if predictions_df_for_show.empty:
        latest_df, _, _ = fetch_predictions(client, band, model)
        predictions_df_for_show = latest_df

    # Create prediction lookup for highlighting
    prediction_ranks: dict[str, int] = {}
    if not predictions_df_for_show.empty and 'song_name' in predictions_df_for_show.columns:
        # Prefer explicit 'rank' if present; else use row order
        use_rank_col = 'rank' in predictions_df_for_show.columns
        for idx, row in predictions_df_for_show.iterrows():
            normalized = _clean_song_name_for_display(str(row['song_name']), band).lower()
            if not normalized:
                continue
            rank = int(row['rank']) if use_rank_col and pd.notna(row['rank']) else (idx + 1)
            prediction_ranks[normalized] = rank

    # Group songs by set (handle missing set numbers)
    if 'set_number' not in setlist_df.columns:
        st.warning("Setlist missing 'set_number' column.")
        return

    # For Phish, fill missing set numbers (encores) as 99 for consistent grouping
    if band == "phish":
        setlist_df['set_number'] = setlist_df['set_number'].apply(lambda v: 99 if (v is None or (isinstance(v, float) and pd.isna(v)) or (pd.isna(v))) else v)

    sets = setlist_df.groupby('set_number', dropna=True)

    # Create columns for sets with robust sorting across mixed types
    def _set_order_key(v: Any) -> int:
        s = str(v).strip().upper()
        if s in {"E", "ENCORE", "99"}:
            return 99
        if s in {"0", "SOUNDCHECK"}:
            return 0
        try:
            return int(float(s))
        except Exception:
            return 50

    set_numbers_raw = [k for k in sets.groups.keys()]
    set_numbers = sorted(set_numbers_raw, key=_set_order_key)

    # Handle different numbers of sets dynamically
    if len(set_numbers) == 1:
        cols = [st.container()]
    elif len(set_numbers) == 2:
        cols = st.columns(2)
    elif len(set_numbers) == 3:
        cols = st.columns(3)
    else:
        # For 4+ sets, use 2 columns and stack sets
        cols = st.columns(2)

    for i, set_num in enumerate(set_numbers):
        col_idx = i if len(set_numbers) <= 3 else i % 2
        col = cols[col_idx]

        # Defensive: some schemas use 'position' vs 'song_position'
        set_data = sets.get_group(set_num)
        if 'song_position' in set_data.columns:
            set_data = set_data.sort_values('song_position')
        elif 'position' in set_data.columns:
            set_data = set_data.sort_values('position')

        # Format set header
        set_num_str = str(set_num).upper()
        if set_num_str in {'E', 'ENCORE'} or set_num in (99, '99'):
            set_header = "**Encore**"
        elif set_num_str == '0' or set_num in (0, '0'):
            set_header = "**Soundcheck**"
        else:
            set_header = f"**Set {set_num}**"

        col.markdown(set_header)

        # Display songs with highlights
        song_list = []
        for _, song_row in set_data.iterrows():
            song_name_clean = _clean_song_name_for_display(song_row['song_name'], band)
            if not song_name_clean:
                continue
            lookup_key = song_name_clean.lower()

            # Check if song was predicted
            if lookup_key in prediction_ranks:
                rank = prediction_ranks[lookup_key]
                if rank <= 10:
                    song_display = f'<span class="badge-top10"><strong>{song_name_clean}</strong> (#{rank})</span>'
                elif rank <= 25:
                    song_display = f'<span class="badge-top25"><strong>{song_name_clean}</strong> (#{rank})</span>'
                elif rank <= 50:
                    song_display = f'<span class="badge-top50">{song_name_clean} (#{rank})</span>'
                else:
                    song_display = song_name_clean
            else:
                song_display = song_name_clean

            song_list.append(song_display)

        # Display songs in the set
        songs_html = "<br>".join(song_list)
        col.markdown(songs_html, unsafe_allow_html=True)

    st.divider()

    legend_cols = st.columns(4)

    with legend_cols[0]:

        st.markdown('<span class="badge-top10">Top 10</span>', unsafe_allow_html=True)

    with legend_cols[1]:

        st.markdown('<span class="badge-top25">Top 25</span>', unsafe_allow_html=True)

    with legend_cols[2]:

        st.markdown('<span class="badge-top50">Top 50</span>', unsafe_allow_html=True)

    with legend_cols[3]:

        total_predicted = 0

        total_songs = 0

        for name in setlist_df['song_name']:

            cleaned = _clean_song_name_for_display(name, band)

            if not cleaned:

                continue

            total_songs += 1

            if cleaned.lower() in prediction_ranks:

                total_predicted += 1

        if total_songs == 0:

            st.markdown("**0 songs predicted**")

        else:

            st.markdown(f"**{total_predicted}/{total_songs} songs predicted**")

    # Display collection and prediction times below the setlist
    st.divider()
    col1_meta, col2_meta = st.columns(2)
    with col1_meta:
        if collection_time:
            st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.9em;'>Data Collected: {pd.to_datetime(collection_time).strftime("%Y-%m-%d %H:%M")}</div>", unsafe_allow_html=True)
    with col2_meta:
        if predicted_at_str != "unknown":
            st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.9em;'>Model Predicted: {predicted_at_str}</div>", unsafe_allow_html=True)