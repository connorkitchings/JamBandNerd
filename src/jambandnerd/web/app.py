
import streamlit as st
import pandas as pd
from supabase import Client

from jambandnerd.db.connection import get_supabase_client


@st.cache_data
def fetch_predictions(_db_client: Client) -> tuple[pd.DataFrame, str | None]:
    """Fetches the latest predictions from the database."""
    # 1. Find the most recent reference_date
    try:
        latest_date_response = (
            _db_client.table("goose_notebook_predictions")
            .select("reference_date")
            .order("reference_date", desc=True)
            .limit(1)
            .execute()
        )
        if not latest_date_response.data:
            return pd.DataFrame(), None
        latest_date = latest_date_response.data[0]["reference_date"]

        # 2. Fetch all predictions for that date
        response = (
            _db_client.table("goose_notebook_predictions")
            .select("rank", "song_name", "plays_past_year", "current_gap", "last_played_date")
            .eq("reference_date", latest_date)
            .order("rank", desc=False)
            .limit(50)
            .execute()
        )

        if not response.data:
            return pd.DataFrame(), None

        df = pd.DataFrame(response.data)
        return df, latest_date
    except Exception as e:
        st.error(f"Failed to fetch data from Supabase: {e}")
        return pd.DataFrame(), None


st.set_page_config(page_title="JamBandNerd Predictions", layout="wide")
st.title("JamBandNerd - Goose Predictions")

try:
    supabase_client = get_supabase_client()
    predictions_df, reference_date = fetch_predictions(supabase_client)

    if not predictions_df.empty:
        st.subheader(f"Top 50 Predictions for Show on {reference_date}")

        display_df = predictions_df.copy()
        display_df.rename(
            columns={
                "rank": "Rank",
                "song_name": "Song",
                "plays_past_year": "Plays (Last Year)",
                "current_gap": "Current Gap",
                "last_played_date": "Last Played",
            },
            inplace=True,
        )

        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.info(
            "This table shows the top 50 most likely songs to be played at the next Goose show, based on the Notebook model."
        )
    else:
        st.warning("No predictions found. Please run the prediction scripts first.")

except Exception as e:
    st.error(
        f"An error occurred while trying to connect to the database or render the page. "
        f"Please ensure your .env file is correctly configured. Error: {e}"
    )
