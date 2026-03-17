from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.config import (
    BAND_ID_COLUMNS,
    EXCLUDED_SHOW_DATES,
    STREAMLIT_CACHE_TTL,
    STREAMLIT_CACHE_TTL_LONG,
)

# This is a temporary solution. In the future, this should be moved to a more centralized location.
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


@st.cache_data(ttl=STREAMLIT_CACHE_TTL_LONG)
def fetch_available_prediction_dates(
    _db_client: Client, band: str, model: str
) -> list[str]:
    """Fetch all dates that have predictions for a band, sorted descending."""
    if band not in BAND_CONFIG:
        return []
    try:
        table_name = f"predictions_{model}"
        # We query the predictions table directly for reference_dates
        # This ensures we only show dates where we actually have a prediction
        resp = (
            _db_client.table(table_name)
            .select("reference_date")
            .eq("band", band)
            .order("reference_date", desc=True)
            .execute()
        )
        # Deduplicate dates (though they should be unique per band/model/date ideally,
        # unless there are multiple runs, but we only care about distinct dates here)
        dates = sorted(
            list(
                {
                    r["reference_date"]
                    for r in (resp.data or [])
                    if r.get("reference_date")
                }
            ),
            reverse=True,
        )
        return dates
    except Exception as e:
        st.error(f"Failed to fetch prediction dates for {band}: {e}")
        return []


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
        return None
    except Exception:
        return None


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
) -> tuple[pd.DataFrame, dict | None]:
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
            return pd.DataFrame(), None
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
        return df, row
    except Exception:
        return pd.DataFrame(), None


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

        if "show_date" in df.columns and not df.empty:
            original_count = len(df)

            # Remove rows with invalid show_date values
            df = df.dropna(subset=["show_date"])
            df = df[df["show_date"].astype(str).str.strip() != ""]

            # Apply exclusions in Python
            valid_excluded_dates = {d for d in EXCLUDED_SHOW_DATES if d and d.strip()}
            if valid_excluded_dates:
                df = df[~df["show_date"].isin(valid_excluded_dates)]

            # Convert show_date to datetime for proper sorting
            df["_show_date_dt"] = pd.to_datetime(df["show_date"], errors="coerce")
            df = df.dropna(
                subset=["_show_date_dt"]
            )  # Remove any that couldn't be parsed

            # Sort and limit in Python
            df = df.sort_values("_show_date_dt", ascending=False).head(limit)

            # Remove the temporary column
            df = df.drop(columns=["_show_date_dt"])

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
def fetch_setlist_for_date(
    _db_client: Client, band: str, show_date: str
) -> tuple[pd.DataFrame, dict | None]:
    """Fetch the setlist for a specific show date."""
    if band not in BAND_CONFIG:
        st.warning(f"Band '{band}' not found in configuration")
        return pd.DataFrame(), None

    try:
        id_col = BAND_ID_COLUMNS.get(band, "show_id")
        pos_col = "position" if band == "phish" else "song_position"
        setlist_table = f"{band}_setlists_raw"
        shows_table = f"{band}_shows_raw"

        # Get the show ID for the given date
        show_resp = (
            _db_client.table(shows_table)
            .select(id_col)
            .eq("show_date", show_date)
            .limit(1)
            .execute()
        )
        if not show_resp.data:
            return pd.DataFrame(), None

        show_id = show_resp.data[0].get(id_col)

        if not show_id:
            return pd.DataFrame(), None

        # Get full setlist for this show
        setlist_data = (
            _db_client.table(setlist_table)
            .select(f"set_number, {pos_col}, song_name")
            .eq(id_col, show_id)
            .order("set_number")
            .order(pos_col)
            .execute()
        )
        setlist_df = pd.DataFrame(setlist_data.data)

        # Deduplicate setlist data at the source
        if not setlist_df.empty:
            dedup_cols = ["set_number", pos_col]
            if all(col in setlist_df.columns for col in dedup_cols):
                setlist_df = setlist_df.drop_duplicates(subset=dedup_cols, keep="first")

        # Get show details
        show_details = None
        show_query = (
            _db_client.table(shows_table)
            .select("*")
            .eq(id_col, show_id)
            .limit(1)
            .execute()
        )

        if show_query.data:
            show_details = show_query.data[0]

        return setlist_df, show_details

    except Exception as e:
        st.error(f"Failed to fetch setlist for {band} on {show_date}: {e}")
        return pd.DataFrame(), None


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
        recent_ids = [
            str(r.get(id_col)) for r in recent_shows if r.get(id_col) is not None
        ]

        if not recent_ids:
            st.info(f"No recent shows found for {band}")
            return pd.DataFrame(), None

        setlist_ids_resp = (
            _db_client.table(setlist_table)
            .select(id_col)
            .in_(id_col, recent_ids)
            .execute()
        )
        setlist_ids = {
            str(r.get(id_col))
            for r in (setlist_ids_resp.data or [])
            if r.get(id_col) is not None
        }

        candidates = [r for r in recent_shows if str(r.get(id_col)) in setlist_ids]
        if not candidates:
            st.info(
                f"No completed shows found in the last 50 {band} shows. They may all be upcoming."
            )
            return pd.DataFrame(), None

        candidates_sorted = sorted(
            candidates, key=lambda x: str(x.get("show_date", "")), reverse=True
        )
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

        # Deduplicate setlist data at the source
        # Some database entries may have duplicate rows due to data collection issues
        if not setlist_df.empty:
            dedup_cols = ["set_number", pos_col]
            if all(col in setlist_df.columns for col in dedup_cols):
                setlist_df = setlist_df.drop_duplicates(subset=dedup_cols, keep="first")

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
