from __future__ import annotations

import json

# Where we need regex helpers
import re
from datetime import date, datetime, timezone
from typing import Any, List, Optional

import altair as alt
import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.config import (
    BAND_ID_COLUMNS,
    EXCLUDED_SHOW_DATES,
    STREAMLIT_CACHE_TTL,
    STREAMLIT_CACHE_TTL_LONG,
)
from jambandnerd.db.connection import get_supabase_client

# --- Configuration ---

# Note: EXCLUDED_SHOW_DATES imported from config

BAND_CONFIG = {
    "eggy": {
        "display_name": "Eggy",
        "shows_table": "eggy_shows_raw",
    },
    "billy": {
        "display_name": "Billy Strings",
        "shows_table": "billy_shows_raw",
    },
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
    "um": {
        "display_name": "Umphrey's McGee",
        "shows_table": "um_shows_raw",
    },
}

ACTIVE_BANDS = list(BAND_CONFIG.keys())
ACTIVE_BAND_SET = set(ACTIVE_BANDS)

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

# Artist-credit spillovers we strip from WSP setlists/Panic displays
WSP_ARTIST_MARKERS = {
    "david bromberg band",
    "new riders of the purple sage",
    "j.j. cale",
    "the doors",
}

@st.cache_data(ttl=STREAMLIT_CACHE_TTL)
def fetch_wsp_upcoming_show(_db_client: Client) -> dict | None:
    """Fetch the next upcoming WSP show from the manual upcoming table."""
    try:
        today_iso = datetime.now(timezone.utc).isoformat()
        resp = (
            _db_client.table("wsp_shows_upcoming")
            .select("*")
            .gte("show_date", today_iso[:10])
            .order("show_date", desc=False)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        resp = (
            _db_client.table("wsp_shows_upcoming")
            .select("*")
            .order("show_date", desc=False)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None

# (Logos removed for a cleaner header)

# --- Data Fetching ---


@st.cache_data(ttl=STREAMLIT_CACHE_TTL)
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


@st.cache_data(ttl=STREAMLIT_CACHE_TTL)
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


@st.cache_data(ttl=STREAMLIT_CACHE_TTL)
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
                # Only show warning for debugging, not in production
                # st.info(f"Processed {original_count} records, showing {len(df)} valid records")
                pass
        return df

    except Exception as e:
        st.error(f"Failed to fetch per-show accuracy: {e}")
        # For debugging - show the specific error and parameters
        import traceback
        st.error(f"Error details: band={band}, model={model}, model_version={model}_v1")
        st.error(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame()


@st.cache_data(ttl=STREAMLIT_CACHE_TTL_LONG)
def fetch_last_show_setlist(
    _db_client: Client, band: str
) -> tuple[pd.DataFrame, dict | None]:
    """Fetch the most recent completed show's setlist for the given band."""
    if band not in BAND_CONFIG:
        st.warning(f"Band '{band}' not found in configuration")
        return pd.DataFrame(), None

    try:
        # Use centralized config for ID columns
        id_col = BAND_ID_COLUMNS.get(band, "show_id")
        pos_col = "position" if band == "phish" else "song_position"

        setlist_table = f"{band}_setlists_raw"
        shows_table = f"{band}_shows_raw"

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
            st.info(f"No recent shows found for {band}")
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
            st.info(f"No completed shows found in the last 50 {band} shows. They may all be upcoming.")
            return pd.DataFrame(), None

        candidates_sorted = sorted(candidates, key=lambda x: str(x.get("show_date", "")), reverse=True)
        most_recent_show_id = str(candidates_sorted[0].get(id_col))

        if not most_recent_show_id:
            return pd.DataFrame(), None

        # Get full setlist for this show
        setlist_data = (
            _db_client.table(setlist_table)
            .select(f"set_number, {pos_col}, song_name")
            .eq(id_col, most_recent_show_id)
            .order("set_number")
            .order(pos_col)
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
        st.error(f"Failed to fetch last show setlist for {band}: {e}")
        import traceback
        with st.expander("Show error details"):
            st.code(traceback.format_exc())
        return pd.DataFrame(), None


@st.cache_data(ttl=STREAMLIT_CACHE_TTL_LONG)
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


@st.cache_data(ttl=STREAMLIT_CACHE_TTL)
def fetch_um_upcoming_show(_db_client: Client) -> dict | None:
    """Fetch the next upcoming UM show from the Seated-backed table."""
    try:
        today_iso = datetime.now(timezone.utc).isoformat()
        resp = (
            _db_client.table("um_upcoming_shows")
            .select("*")
            .gte("starts_at", today_iso)
            .order("starts_at", desc=False)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]

        # Fallback to the most recently stored upcoming show if nothing is in the future
        resp = (
            _db_client.table("um_upcoming_shows")
            .select("*")
            .order("starts_at", desc=False)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None


# --- UI Components ---


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
    if band_val not in ACTIVE_BAND_SET:
        band_val = default_band
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

    sorted_bands = sorted(
        ((slug, BAND_CONFIG[slug]) for slug in ACTIVE_BANDS),
        key=lambda item: item[1]["display_name"].lower(),
    )
    band_display_names = [config["display_name"] for _, config in sorted_bands]
    display_to_slug = {config["display_name"]: slug for slug, config in sorted_bands}

    if initial_band in ACTIVE_BAND_SET:
        initial_band_display = BAND_CONFIG[initial_band]["display_name"]  # type: ignore[index]
    else:
        initial_band_display = band_display_names[0]
    try:
        band_index = band_display_names.index(initial_band_display)
    except ValueError:
        band_index = 0

    selected_band_display = st.sidebar.selectbox("Select a Band", band_display_names, index=band_index)
    selected_band_slug = display_to_slug[selected_band_display]

    model_display_names = [config["display_name"] for config in MODEL_CONFIG.values()]
    if initial_model in MODEL_CONFIG:
        initial_model_display = MODEL_CONFIG[initial_model]["display_name"]  # type: ignore[index]
    else:
        initial_model_display = model_display_names[0]
    try:
        model_index = model_display_names.index(initial_model_display)
    except ValueError:
        model_index = 0
    selected_model_display = st.sidebar.radio("Select a Model", model_display_names, index=model_index)
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
        "notebook": "# Notebook Model (Frequency-Based)\n\n### Overview\n\nThis model is the baseline predictor, designed to be simple, transparent, and fast. It operates on the core assumption that songs played frequently in the recent past are more likely to be played again soon.\n\n### Logic & Features\n\nGiven a reference show date (the show we are predicting for), the model performs the following steps:\n\n1.  **Define a 1-Year Window**: It looks at all shows that occurred in the 365 days immediately preceding the *last completed show*.\n2.  **Count Plays**: It counts how many times each song was played within that one-year window. This count (`plays_past_year`) is the primary ranking feature.\n3.  **Exclude Recent Songs**: To avoid predicting songs that were just played, it identifies all songs performed in the **last three completed shows** and removes them from the candidate list.\n4.  **Calculate Current Gap**: For each remaining song, it calculates the `current_gap`, which is the number of shows that have passed since the song was last played.\n5.  **Rank and Predict**: Songs are ranked primarily by `plays_past_year` (descending). Any ties are broken by `current_gap` (descending, so songs with a larger gap are ranked higher).\n\nThe result is a list of songs that are both popular in the current rotation and not *too* recent, making them strong candidates for the next show.\n",
        "ckplus": "# CK+ Model (Gap-Based)\n\n### Overview\n\nThe CK+ model is a gap-based statistical predictor that ranks songs by how \"overdue\" they are to be played. It complements the frequency-based Notebook model by focusing on historical performance gaps rather than recent play counts.\n\n### Logic & Features\n\nThe model's core logic is based on analyzing the number of shows that typically pass between two performances of the same song.\n\n1.  **Define a 5-Year Window**: The model uses a five-year historical window to calculate long-term gap statistics for each song.\n2.  **Calculate Gap Statistics**: For each song, it computes:\n    *   `avg_gap`: The average number of shows between plays.\n    *   `std_gap`: The standard deviation of the gaps, measuring how consistent the song's rotation is.\n    *   `current_gap`: The number of shows that have passed since the song was last played.\n3.  **Calculate Core Ratios**:\n    *   `gap_ratio`: Calculated as `current_gap / avg_gap`. A ratio greater than 1.0 suggests a song is \"overdue.\"\n    *   `gap_z_score`: Measures how many standard deviations the `current_gap` is from the `avg_gap`. A high positive Z-score indicates a statistically significant gap.\n4.  **Apply Filters**:\n    *   **Minimum Plays**: Songs with very few plays in the 5-year window are excluded.\n    *   **Retirement Heuristic**: Songs with an extremely large `current_gap` are assumed to be \"retired\" and are excluded. This threshold is configured on a per-band basis.\n5.  **Final Scoring & Ranking**: The final `ckplus_score` is a weighted blend of the `gap_ratio` and the `gap_z_score`, which is then scaled by a \"reliability\" term. This term gives less weight to songs with very few plays or a high standard deviation (erratic history), preventing them from being ranked too highly.\n"
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
    venue = show_details.get("venue_name") or show_details.get("venue") or show_details.get("venuename")
    if not venue:
        venue = "Unknown Venue"
    city = show_details.get("venue_city") or show_details.get("city") or ""
    state = show_details.get("venue_state") or show_details.get("state") or ""

    # Fetch collection and prediction times for this specific show date
    collection_time = fetch_last_collection_time(client, band) # This fetches the latest, not necessarily for this show
    # To get prediction time for this show, we need to fetch predictions for this specific date
    _, _, prediction_meta = fetch_predictions(client, band, model) # This fetches latest predictions
    predicted_at_raw = prediction_meta.get("predicted_at")
    predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
    predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"

    col1, col2 = st.columns([1, 2]) # Adjust column width as needed

    with col1:
        st.markdown(f"**Date:** {formatted_date}")
        st.markdown(f"**Venue:** {venue}")
        if city and state:
            st.markdown(f"**Location:** {city}, {state}")
        # Add collection and prediction times if available
        if collection_time:
            st.markdown(f"**Data Collected:** {pd.to_datetime(collection_time).strftime("%Y-%m-%d %H:%M")}")
        if predicted_at_str != "unknown":
            st.markdown(f"**Model Predicted:** {predicted_at_str}")

    with col2:
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

            if i < len(set_numbers) - 1:  # Don't add space after last set
                col.markdown("")

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



































        st.dataframe(display_df, use_container_width=True, hide_index=True, height=450)





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
    st.divider()
    st.markdown(
        f"<h3 style='text-align: center;'>How This Model Works - {model_display_name}</h3>",
        unsafe_allow_html=True,
    )
    explanation_content = get_model_explanation(model)
    st.markdown(explanation_content, unsafe_allow_html=True)


def display_band_comparison(client: Client, model: str, k: int):
    """Display a comparison of model accuracy across all bands."""
    st.markdown(f"<h3 style='text-align: center;'>Model Accuracy Comparison: {MODEL_CONFIG[model]['display_name']} (Top-{k})</h3>", unsafe_allow_html=True)

    @st.cache_data(ttl=STREAMLIT_CACHE_TTL)
    def fetch_all_bands_accuracy(_db_client: Client, model: str) -> pd.DataFrame:
        try:
            model_version = f"{model}_v1"
            response = _db_client.table("accuracy_per_show").select("band, show_date, k10_recall, k25_recall, k50_recall").eq("model_version", model_version).execute()
            return pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to fetch accuracy data for all bands: {e}")
            return pd.DataFrame()

    accuracy_df = fetch_all_bands_accuracy(client, model)

    if not accuracy_df.empty:
        recall_col = f'k{k}_recall'
        if recall_col not in accuracy_df.columns:
            st.warning(f"Recall data for K={k} not available.")
            return

        # Calculate average recall per band
        avg_recall_by_band = accuracy_df.groupby('band')[recall_col].mean().reset_index()
        avg_recall_by_band = avg_recall_by_band.sort_values(by=recall_col, ascending=False)

        chart = alt.Chart(avg_recall_by_band).mark_bar().encode(
            x=alt.X('band:N', title='Band', sort='-y'),
            y=alt.Y(f'{recall_col}:Q', title=f'Average Recall @ Top {k}', axis=alt.Axis(format='.0%')),
            color=alt.Color('band:N', legend=None),
            tooltip=[
                alt.Tooltip('band:N', title='Band'),
                alt.Tooltip(f'{recall_col}:Q', title='Avg. Recall', format='.1%')
            ]
        ).properties(
            title=f"Average Top-{k} Recall by Band for {MODEL_CONFIG[model]['display_name']} Model"
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No accuracy data available to compare bands.")

st.divider()


def main():
    """Main application entry point."""
    st.set_page_config(page_title="JamBandNerd", layout="wide")
    st.markdown("<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True)

    st.markdown("""
    <style>
        :root {
            --primary-color: #F63366; /* Streamlit's default primary color */
            --success-color: #4CAF50; /* Green for Top 10 */
            --warning-color: #FFD700; /* Gold for Top 25 */
            --info-color: #D3D3D3;    /* Light Grey for Top 50 */
            --background-color: #F0F2F6; /* Light grey for tab background */
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            justify-content: space-around;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: var(--background-color);
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
            color: var(--primary-color); /* Highlight selected tab with primary color */
        }
        button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
            font-size: 1.1rem;
        }
        /* Custom classes for badges */
        .badge-top10 {
            background-color: var(--success-color);
            color: white;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }
        .badge-top25 {
            background-color: var(--warning-color);
            color: black;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
        }
        .badge-top50 {
            background-color: var(--info-color);
            color: black;
            padding: 2px 4px;
            border-radius: 3px;
        }
    </style>""", unsafe_allow_html=True)

    # Read initial selection from URL with sensible defaults
    defaults = {
        "band": ACTIVE_BANDS[0],
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

        # Use tabs for a cleaner layout
        tab1, tab2, tab3, tab4 = st.tabs(["Predictions", "Last Show Analysis", "Model Performance", "Compare Bands"])

        with tab1:
            display_predictions(supabase_client, selected_band, selected_model)

        with tab2:
            st.markdown(
                "<h3 style='text-align: center;'>Last Show Setlist</h3>",
                unsafe_allow_html=True,
            )
            display_last_show_setlist(supabase_client, selected_band, selected_model)

        with tab3:
            display_historical_accuracy(
                supabase_client, selected_band, selected_model, selected_k
            )

        with tab4:
            display_band_comparison(supabase_client, selected_model, selected_k)

    except Exception as e:
        st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
