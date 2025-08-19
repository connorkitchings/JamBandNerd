
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


st.set_page_config(page_title="JamBandNerd Predictions", layout="wide")
st.title("JamBandNerd - Goose Predictions")

try:
    supabase_client = get_supabase_client()

    if st.button("Refresh data"):
        fetch_predictions.clear()

    predictions_df, reference_date, meta = fetch_predictions(supabase_client)

    if not predictions_df.empty:
        st.subheader(f"Top Predictions for Show on {reference_date}")
        if meta:
            st.caption(
                " | ".join(
                    part for part in [
                        f"Model: {meta.get('model_version')}" if meta.get("model_version") else None,
                        f"Top K: {meta.get('top_k')}" if meta.get("top_k") else None,
                        f"Predicted at: {meta.get('predicted_at')}" if meta.get("predicted_at") else None,
                    ]
                    if part
                )
            )

        display_df = predictions_df.copy()
        display_df.rename(
            columns={
                "rank": "Rank",
                "song_name": "Song",
                "plays_past_year": "Plays (Last Year)",
                "current_gap": "Current Gap",
                "LTP": "Last Played",
            },
            inplace=True,
        )

        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.info(
            "This table shows the top songs most likely to be played at the next Goose show, based on the Notebook model."
        )
    else:
        st.warning("No predictions found. Please run the prediction scripts first.")

except Exception as e:
    st.error(
        f"An error occurred while trying to connect to the database or render the page. "
        f"Please ensure your .env file is correctly configured. Error: {e}"
    )
