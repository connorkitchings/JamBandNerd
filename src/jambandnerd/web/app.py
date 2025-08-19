
import streamlit as st
import pandas as pd
from supabase import Client

from jambandnerd.db.connection import get_supabase_client


@st.cache_data
def fetch_predictions(_db_client: Client) -> tuple[pd.DataFrame, str | None, dict]:
    """Fetch the latest predictions, handling both nested-JSON and flat-table schemas.

    Returns a tuple of (predictions_df, reference_date, metadata_dict).
    """
    try:
        latest_response = (
            _db_client.table("goose_notebook_predictions")
            .select("*")
            .order("reference_date", desc=True)
            .limit(1)
            .execute()
        )
        if not latest_response.data:
            return pd.DataFrame(), None, {}

        row = latest_response.data[0]
        reference_date = row.get("reference_date")

        # Preferred: nested predictions JSON
        predictions_json = row.get("predictions")
        if predictions_json:
            df = pd.DataFrame(predictions_json)
            # Normalize potential field name differences
            if "last_played_date" in df.columns and "LTP" not in df.columns:
                df.rename(columns={"last_played_date": "LTP"}, inplace=True)
            return df, reference_date, {
                "model_version": row.get("model_version"),
                "predicted_at": row.get("predicted_at"),
                "top_k": row.get("top_k"),
            }

        # Fallback: flat rows stored per prediction
        flat_resp = (
            _db_client.table("goose_notebook_predictions")
            .select("rank, song_name, plays_past_year, current_gap, last_played_date")
            .eq("reference_date", reference_date)
            .order("rank", desc=False)
            .limit(50)
            .execute()
        )
        if not flat_resp.data:
            return pd.DataFrame(), reference_date, {}
        df = pd.DataFrame(flat_resp.data)
        if "last_played_date" in df.columns and "LTP" not in df.columns:
            df.rename(columns={"last_played_date": "LTP"}, inplace=True)
        return df, reference_date, {}
    except Exception as e:
        st.error(f"Failed to fetch data from Supabase: {e}")
        return pd.DataFrame(), None, {}


def fetch_show_details_by_date(_db_client: Client, reference_date: str | None) -> dict | None:
    """Fetch venue details for the given reference show date from goose_shows_raw.

    Returns a dict containing keys: show_date, venue_name, venue_city, venue_state if found, else None.
    """
    if not reference_date:
        return None
    try:
        resp = (
            _db_client.table("goose_shows_raw")
            .select("show_date,venue_name,venue_city,venue_state,show_id")
            .eq("show_date", reference_date)
            .order("show_id", desc=False)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        row = resp.data[0]
        return {
            "show_date": row.get("show_date"),
            "venue_name": row.get("venue_name"),
            "venue_city": row.get("venue_city"),
            "venue_state": row.get("venue_state"),
        }
    except Exception:
        return None


st.set_page_config(page_title="JamBandNerd Predictions", layout="wide")
st.title("JamBandNerd - Goose Predictions")

try:
    supabase_client = get_supabase_client()

    if st.button("Refresh data"):
        fetch_predictions.clear()

    predictions_df, reference_date, meta = fetch_predictions(supabase_client)

    if not predictions_df.empty:
        show_details = fetch_show_details_by_date(supabase_client, reference_date)
        if show_details:
            header = (
                f"Next Show: {show_details.get('show_date')} at "
                f"{show_details.get('venue_name')} in "
                f"{show_details.get('venue_city')}, {show_details.get('venue_state')}"
            )
        else:
            header = f"Next Show: {reference_date}"
        st.subheader(header)

        display_df = predictions_df.copy()
        # Keep and order the desired columns
        desired_order = ["rank", "song_name", "plays_past_year", "LTP", "current_gap"]
        display_df = display_df[[c for c in desired_order if c in display_df.columns]]
        # Rename headers to match requested labels
        display_df.rename(
            columns={
                "rank": "rank",
                "song_name": "Song",
                "plays_past_year": "Plays in Last Year",
                "LTP": "LTP Date (Last Played)",
                "current_gap": "Current Gap",
            },
            inplace=True,
        )

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Caption at the bottom with loaded_at and predicted_at without seconds
        loaded_at = pd.Timestamp.utcnow().floor("min")
        predicted_at_raw = meta.get("predicted_at") if meta else None
        try:
            predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
        except Exception:
            predicted_at = None
        loaded_at_str = loaded_at.strftime("%Y-%m-%d %H:%M")
        predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at is not None else "unknown"
        st.caption(f"data loaded at {loaded_at_str} and predictions made at {predicted_at_str}")
    else:
        st.warning("No predictions found. Please run the prediction scripts first.")

except Exception as e:
    st.error(
        f"An error occurred while trying to connect to the database or render the page. "
        f"Please ensure your .env file is correctly configured. Error: {e}"
    )
