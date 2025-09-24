from __future__ import annotations

import json
from datetime import date
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
        
        # Apply exclusions - filter out empty/invalid strings to avoid database query errors
        valid_excluded_dates = {d for d in EXCLUDED_SHOW_DATES if d and d.strip()}
        for d in valid_excluded_dates:
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
def fetch_predictions_for_date(
    _db_client: Client, band: str, model: str, reference_date: str
) -> pd.DataFrame:
    """Fetch predictions for a specific band/model/reference_date from unified table."""
    try:
        table_name = f"predictions_{model}"
        query = (
            _db_client.table(table_name)
            .select("*")
            .eq("band", band)
            .eq("reference_date", reference_date)
            .limit(1)
        )
        resp = query.execute()
        if not resp.data:
            return pd.DataFrame()
        row = resp.data[0]
        predictions_json = row.get("predictions")
        if isinstance(predictions_json, str):
            predictions_parsed = json.loads(predictions_json)
        else:
            predictions_parsed = predictions_json or []
        df = pd.DataFrame(predictions_parsed)
        # Normalize columns for consistent downstream use
        if "last_played_date" in df.columns and "LTP" not in df.columns:
            df.rename(columns={"last_played_date": "LTP"}, inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_per_show_accuracy(
    _db_client: Client, band: str, model: str, limit: int = 100
) -> pd.DataFrame:
    """
    Fetch the last N per-show accuracy records for charting, applying backend exclusions.
    """
    try:
        model_version = f"{model}_v1"
        
        # Use simple query without complex filtering to avoid date parsing errors
        query = (
            _db_client.table("accuracy_per_show")
            .select("*")
            .eq("band", band)
            .eq("model_version", model_version)
        )

        # Execute the query without date filtering first
        response = query.execute()
        
        if not response.data:
            return pd.DataFrame()
            
        # Process and filter the data in Python instead of at database level
        df = pd.DataFrame(response.data)
        
        if 'show_date' in df.columns and not df.empty:
            original_count = len(df)
            
            # Remove rows with invalid show_date values
            df = df.dropna(subset=['show_date'])
            df = df[df['show_date'].astype(str).str.strip() != '']
            
            # Apply exclusions in Python
            valid_excluded_dates = {d for d in EXCLUDED_SHOW_DATES if d and d.strip()}
            if valid_excluded_dates:
                df = df[~df['show_date'].isin(valid_excluded_dates)]
            
            # Convert show_date to datetime for proper sorting
            df['_show_date_dt'] = pd.to_datetime(df['show_date'], errors='coerce')
            df = df.dropna(subset=['_show_date_dt'])  # Remove any that couldn't be parsed
            
            # Sort and limit in Python
            df = df.sort_values('_show_date_dt', ascending=False).head(limit)
            
            # Remove the temporary column
            df = df.drop(columns=['_show_date_dt'])
            
            if len(df) < original_count:
                filtered_count = original_count - len(df)
                # Only show warning for debugging, not in production
                # st.info(f"Processed {original_count} records, showing {len(df)} valid records")
        
        return df
        
    except Exception as e:
        st.error(f"Failed to fetch per-show accuracy: {e}")
        # For debugging - show the specific error and parameters
        import traceback
        st.error(f"Error details: band={band}, model={model}, model_version={model}_v1")
        st.error(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_last_show_setlist(
    _db_client: Client, band: str
) -> tuple[pd.DataFrame, dict | None]:
    """Fetch the most recent completed show's setlist for the given band."""
    if band not in BAND_CONFIG:
        return pd.DataFrame(), None
    
    try:
        # Get the most recent completed show with setlist data
        setlist_table = f"{band}_setlists_raw"
        shows_table = f"{band}_shows_raw"
        
        # Get the most recent show that has setlist data by joining shows and setlists
        id_col = "api_show_id" if band == "phish" else "show_id"
        
        # Get the most recent show that has setlist data by joining shows and setlists
        today_iso = date.today().isoformat()
        recent_shows_resp = (
            _db_client.table(shows_table)
            .select(f"{id_col}, show_date")
            .lt("show_date", today_iso)
            .order("show_date", desc=True)
            .limit(50)
            .execute()
        )
        if not recent_shows_resp.data:
            return pd.DataFrame(), None
        
        recent_shows = recent_shows_resp.data
        recent_ids = [str(r.get(id_col)) for r in recent_shows if r.get(id_col) is not None]
        if not recent_ids:
            return pd.DataFrame(), None
            
        setlist_ids_resp = (
            _db_client.table(setlist_table)
            .select(id_col)
            .in_(id_col, recent_ids)
            .execute()
        )
        setlist_ids = {str(r.get(id_col)) for r in (setlist_ids_resp.data or []) if r.get(id_col) is not None}
        
        candidates = [r for r in recent_shows if str(r.get(id_col)) in setlist_ids]
        if not candidates:
            return pd.DataFrame(), None
            
        candidates_sorted = sorted(candidates, key=lambda x: str(x.get("show_date", "")), reverse=True)
        most_recent_show_id = str(candidates_sorted[0].get(id_col))
        most_recent_show_date = candidates_sorted[0].get("show_date")
        
        if not most_recent_show_id:
            return pd.DataFrame(), None
        else:
            # For WSP, intersect recent shows with setlists on show_id
            recent_shows_resp = (
                _db_client.table(shows_table)
                .select("show_id, show_date")
                .order("show_date", desc=True)
                .limit(50)
                .execute()
            )
            if not recent_shows_resp.data:
                return pd.DataFrame(), None
            recent_shows = recent_shows_resp.data
            recent_ids = [str(r.get("show_id")) for r in recent_shows if r.get("show_id") is not None]
            if not recent_ids:
                return pd.DataFrame(), None
            setlist_ids_resp = (
                _db_client.table(setlist_table)
                .select("show_id")
                .in_("show_id", recent_ids)
                .execute()
            )
            setlist_ids = {str(r.get("show_id")) for r in (setlist_ids_resp.data or []) if r.get("show_id") is not None}
            candidates = [r for r in recent_shows if str(r.get("show_id")) in setlist_ids]
            if not candidates:
                return pd.DataFrame(), None
            candidates_sorted = sorted(candidates, key=lambda x: str(x.get("show_date", "")), reverse=True)
            most_recent_show_id = str(candidates_sorted[0].get("show_id"))
            most_recent_show_date = candidates_sorted[0].get("show_date")
            if not most_recent_show_id:
                return pd.DataFrame(), None
        
        # Get full setlist for this show
        setlist_data = (
            _db_client.table(setlist_table)
            .select("set_number, song_position, song_name")
            .eq(id_col, most_recent_show_id)
            .order("set_number")
            .order("song_position")
            .execute()
        )
        setlist_df = pd.DataFrame(setlist_data.data)

        # Get show details
        show_details = None
        show_query = (
            _db_client.table(shows_table)
            .select("*")
            .eq(id_col, most_recent_show_id)
            .limit(1)
            .execute()
        )
        
        if show_query.data:
            show_details = show_query.data[0]
            
        return setlist_df, show_details
        
    except Exception as e:
        st.error(f"Failed to fetch last show setlist: {e}")
        return pd.DataFrame(), None


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


def get_initial_selection_from_url(default_band: str, default_model: str, default_k: int) -> dict:
    try:
        qp = dict(st.query_params)
    except Exception:
        qp = st.experimental_get_query_params()
    band_val = qp.get("band", [default_band])[0] if isinstance(qp.get("band"), list) else qp.get("band", default_band)
    model_val = qp.get("model", [default_model])[0] if isinstance(qp.get("model"), list) else qp.get("model", default_model)
    try:
        k_raw = qp.get("k", [str(default_k)])[0] if isinstance(qp.get("k"), list) else qp.get("k", str(default_k))
        k_val = int(k_raw)
    except Exception:
        k_val = default_k
    return {"band": band_val, "model": model_val, "k": k_val}


def sync_query_params(band: str, model: str, k: int) -> None:
    try:
        st.query_params.update(band=band, model=model, k=str(k))
    except Exception:
        st.experimental_set_query_params(band=band, model=model, k=str(k))


@st.cache_resource
def supabase_client_cached() -> Client:
    return get_supabase_client()


def display_sidebar(initial_band: Optional[str] = None, initial_model: Optional[str] = None, initial_k: Optional[int] = None) -> tuple[str, str, int]:
    """Render the sidebar and return selected options."""
    st.sidebar.title("JamBandNerd")

    band_display_names = [config["display_name"] for config in BAND_CONFIG.values()]
    if initial_band in BAND_CONFIG:
        initial_band_display = BAND_CONFIG[initial_band]["display_name"]  # type: ignore[index]
    else:
        initial_band_display = band_display_names[0]
    try:
        band_index = band_display_names.index(initial_band_display)
    except ValueError:
        band_index = 0
    selected_band_display = st.sidebar.selectbox("Select a Band", band_display_names, index=band_index)
    selected_band_slug = next(
        slug
        for slug, config in BAND_CONFIG.items()
        if config["display_name"] == selected_band_display
    )

    model_display_names = [config["display_name"] for config in MODEL_CONFIG.values()]
    if initial_model in MODEL_CONFIG:
        initial_model_display = MODEL_CONFIG[initial_model]["display_name"]  # type: ignore[index]
    else:
        initial_model_display = model_display_names[0]
    try:
        model_index = model_display_names.index(initial_model_display)
    except ValueError:
        model_index = 0
    selected_model_display = st.sidebar.selectbox("Select a Model", model_display_names, index=model_index)
    selected_model_slug = next(
        slug
        for slug, config in MODEL_CONFIG.items()
        if config["display_name"] == selected_model_display
    )

    # Compact model explanation with tooltip-like hint
    st.sidebar.caption(f"{selected_model_display}: {MODEL_CONFIG[selected_model_slug]['explanation']}")

    k_options = [10, 25, 50]
    if initial_k in k_options:
        k_index = k_options.index(initial_k)  # type: ignore[arg-type]
    else:
        k_index = 2
    selected_k = st.sidebar.selectbox(
        "K for Accuracy (Top-K)",
        k_options,
        index=k_index,
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


@st.cache_data
def get_model_explanation(model_slug: str) -> str:
    """Fetches the markdown explanation for a given model."""
    # In a real-world scenario, this would read from the file system.
    # Here, we embed the content directly since we've already read it.
    explanations = {
        "notebook": """# Notebook Model (Frequency-Based)

### Overview

This model is the baseline predictor, designed to be simple, transparent, and fast. It operates on the core assumption that songs played frequently in the recent past are more likely to be played again soon.

### Logic & Features

Given a reference show date (the show we are predicting for), the model performs the following steps:

1.  **Define a 1-Year Window**: It looks at all shows that occurred in the 365 days immediately preceding the *last completed show*.
2.  **Count Plays**: It counts how many times each song was played within that one-year window. This count (`plays_past_year`) is the primary ranking feature.
3.  **Exclude Recent Songs**: To avoid predicting songs that were just played, it identifies all songs performed in the **last three completed shows** and removes them from the candidate list.
4.  **Calculate Current Gap**: For each remaining song, it calculates the `current_gap`, which is the number of shows that have passed since the song was last played.
5.  **Rank and Predict**: Songs are ranked primarily by `plays_past_year` (descending). Any ties are broken by `current_gap` (descending, so songs with a larger gap are ranked higher).

The result is a list of songs that are both popular in the current rotation and not *too* recent, making them strong candidates for the next show.
""",
        "ckplus": """# CK+ Model (Gap-Based)

### Overview

The CK+ model is a gap-based statistical predictor that ranks songs by how "overdue" they are to be played. It complements the frequency-based Notebook model by focusing on historical performance gaps rather than recent play counts.

### Logic & Features

The model's core logic is based on analyzing the number of shows that typically pass between two performances of the same song.

1.  **Define a 5-Year Window**: The model uses a five-year historical window to calculate long-term gap statistics for each song.
2.  **Calculate Gap Statistics**: For each song, it computes:
    *   `avg_gap`: The average number of shows between plays.
    *   `std_gap`: The standard deviation of the gaps, measuring how consistent the song's rotation is.
    *   `current_gap`: The number of shows that have passed since the song was last played.
3.  **Calculate Core Ratios**:
    *   `gap_ratio`: Calculated as `current_gap / avg_gap`. A ratio greater than 1.0 suggests a song is "overdue."
    *   `gap_z_score`: Measures how many standard deviations the `current_gap` is from the `avg_gap`. A high positive Z-score indicates a statistically significant gap.
4.  **Apply Filters**:
    *   **Minimum Plays**: Songs with very few plays in the 5-year window are excluded.
    *   **Retirement Heuristic**: Songs with an extremely large `current_gap` are assumed to be "retired" and are excluded. This threshold is configured on a per-band basis.
5.  **Final Scoring & Ranking**: The final `ckplus_score` is a weighted blend of the `gap_ratio` and the `gap_z_score`, which is then scaled by a "reliability" term. This term gives less weight to songs with very few plays or a high standard deviation (erratic history), preventing them from being ranked too highly.
"""
    }
    return explanations.get(model_slug, "No explanation available for this model.")


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
    # Prefer normalized venue_name; fall back to legacy keys if present
    venue = show_details.get("venue_name") or show_details.get("venue") or show_details.get("venuename")
    if not venue:
        venue = "Unknown Venue"
    city = show_details.get("venue_city") or show_details.get("city") or ""
    state = show_details.get("venue_state") or show_details.get("state") or ""
    
    venue_info = venue
    if city and state:
        venue_info += f" • {city}, {state}"
    
    st.markdown(f"<h4 style='text-align: center;'>Last Show: {formatted_date} — {venue_info}</h4>", unsafe_allow_html=True)
    
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
            song_name = str(row['song_name'])
            rank = int(row['rank']) if use_rank_col and pd.notna(row['rank']) else (idx + 1)
            prediction_ranks[song_name] = rank
    
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
            song_name = song_row['song_name']
            
            # Check if song was predicted
            if song_name in prediction_ranks:
                rank = prediction_ranks[song_name]
                if rank <= 10:
                    # Top 10: Green background
                    song_display = f'<span style="background-color: #4CAF50; padding: 2px 4px; border-radius: 3px; color: white;"><strong>{song_name}</strong> (#{rank})</span>'
                elif rank <= 25:
                    # Top 25: Gold background
                    song_display = f'<span style="background-color: #FFD700; padding: 2px 4px; border-radius: 3px; color: black;"><strong>{song_name}</strong> (#{rank})</span>'
                elif rank <= 50:
                    # Top 50: Light Grey background
                    song_display = f'<span style="background-color: #D3D3D3; padding: 2px 4px; border-radius: 3px; color: black;">{song_name} (#{rank})</span>'
                else:
                    song_display = song_name
            else:
                song_display = song_name
                
            song_list.append(song_display)
        
        # Display songs in the set
        songs_html = "<br>".join(song_list)
        col.markdown(songs_html, unsafe_allow_html=True)
        
        if i < len(set_numbers) - 1:  # Don't add space after last set
            col.markdown("")
    
    # Add legend
    st.markdown("---")
    legend_cols = st.columns(4)
    with legend_cols[0]:
        st.markdown('<span style="background-color: #4CAF50; padding: 2px 6px; border-radius: 3px; color: white;"><strong>Top 10</strong></span>', unsafe_allow_html=True)
    with legend_cols[1]:
        st.markdown('<span style="background-color: #FFD700; padding: 2px 6px; border-radius: 3px; color: black;"><strong>Top 25</strong></span>', unsafe_allow_html=True)
    with legend_cols[2]:
        st.markdown('<span style="background-color: #D3D3D3; padding: 2px 6px; border-radius: 3px; color: black;">Top 50</span>', unsafe_allow_html=True)
    with legend_cols[3]:
        total_predicted = len([s for s in setlist_df['song_name'] if s in prediction_ranks])
        total_songs = len(setlist_df)
        st.markdown(f"**{total_predicted}/{total_songs} songs predicted**")


def display_predictions(client: Client, band: str, model: str):
    """Display the main predictions view."""
    with st.spinner("Loading predictions..."):
        predictions_df, ref_date, meta = fetch_predictions(client, band, model)

    model_display_name = MODEL_CONFIG.get(model, {}).get("display_name", model.title())

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

        display_df = format_predictions_df(predictions_df.head(50), model)

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=700)
        
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
        
        # Display last show setlist with prediction highlights
        st.markdown("---")
        st.markdown(
            "<h3 style='text-align: center;'>Last Show Setlist</h3>",
            unsafe_allow_html=True,
        )
        display_last_show_setlist(client, band, model)

    else:
        st.warning(
            "No predictions found for the selected model. Please run the prediction scripts first."
        )


def display_historical_accuracy(client: Client, band: str, model: str, k: int):
    """Display the historical accuracy section and the model explanation."""
    model_display_name = MODEL_CONFIG.get(model, {}).get("display_name", model.title())
    st.markdown("---")
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

    # --- Display Model Explanation ---
    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align: center;'>How This Model Works - {model_display_name}</h3>",
        unsafe_allow_html=True,
    )
    explanation_content = get_model_explanation(model)
    st.markdown(explanation_content, unsafe_allow_html=True)


# --- Main App ---


def main():
    """Main application entry point."""
    st.set_page_config(page_title="JamBandNerd", layout="wide")
    st.markdown("<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True)

    # Read initial selection from URL with sensible defaults
    defaults = {
        "band": next(iter(BAND_CONFIG.keys())),
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
        supabase_client = supabase_client_cached()
        display_predictions(supabase_client, selected_band, selected_model)
        display_historical_accuracy(
            supabase_client, selected_band, selected_model, selected_k
        )
    except Exception as e:
        st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
