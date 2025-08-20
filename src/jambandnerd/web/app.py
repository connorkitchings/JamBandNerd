
import streamlit as st
import pandas as pd
from supabase import Client

from jambandnerd.db.connection import get_supabase_client


def display_method_explanation(file_label: str) -> None:
    """Render a short explanation for the selected prediction method under the picker."""
    method_explanations = {
        "CK+": (
            """
<div style='font-size:0.95em; color:#666; margin-bottom:10px;'>
<b>CK+ Method:</b> Gap-based statistical predictor that ranks songs by how overdue they are, using historical
show-to-show gaps, recency, and reliability scaling. It emphasizes songs likely to return given typical gaps.
</div>
            """
        ),
        "Notebook": (
            """
<div style='font-size:0.95em; color:#666; margin-bottom:10px;'>
<b>Notebook Method:</b> Focuses on songs most frequently played in the last year, excluding those played in the
last three shows. It surfaces in-rotation songs and provides last played date and current gap context.
</div>
            """
        ),
    }

    st.sidebar.markdown(method_explanations.get(file_label, ""), unsafe_allow_html=True)


@st.cache_data
def fetch_predictions(_db_client: Client, band: str = "goose", model: str = "notebook") -> tuple[pd.DataFrame, str | None, dict]:
    """Fetch the latest predictions for a given band from the unified table.

    Handles both nested-JSON and flat-table schemas.

    Returns a tuple of (predictions_df, reference_date, metadata_dict).
    """
    try:
        table_name = f"predictions_{model}"
        latest_response = (
            _db_client.table(table_name)
            .select("*")
            .eq("band", band)
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
                "band": row.get("band"),
                "model_version": row.get("model_version"),
                "predicted_at": row.get("predicted_at"),
                "top_k": row.get("top_k"),
            }

        # Fallback logic is removed as it's not the primary schema path.
        # If needed, it would query predictions_notebook with a band filter.
        return pd.DataFrame(), reference_date, {}
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


st.set_page_config(page_title="JamBandNerd", layout="wide")

# Add a sidebar for band and model selection
band_options = ["Goose"]  # Add other bands like "Phish", "WSP" when ready
selected_band = st.sidebar.selectbox("Select a Band", band_options)
model_options = {
    "Notebook": "notebook",
    "CK+": "ckplus",
}
selected_model_label = st.sidebar.selectbox("Select a Model", list(model_options.keys()))
selected_model = model_options[selected_model_label]

# Show method explanation under the picker
display_method_explanation(selected_model_label)

try:
    supabase_client = get_supabase_client()

    if selected_band:
        # Map display label to slug for DB queries
        selected_band_slug = selected_band.lower()
        predictions_df, reference_date, meta = fetch_predictions(
            supabase_client, band=selected_band_slug, model=selected_model
        )

    if not predictions_df.empty:
        # Top centered titles
        band_slug = (meta.get("band") if meta else None) or (selected_band.lower() if selected_band else "goose")
        band_display = band_slug.title()
        model_display = selected_model_label  # "Notebook" or "CK+"
        st.markdown("<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True)
        st.markdown(
            f"<h3 style='text-align: center;'>{band_display} Predictions - {model_display}</h3>",
            unsafe_allow_html=True,
        )

        # Centered next show header with mm/dd/yyyy date
        show_details = fetch_show_details_by_date(supabase_client, reference_date)
        if show_details and show_details.get("show_date"):
            try:
                mmddyyyy = pd.to_datetime(show_details.get("show_date")).strftime("%m/%d/%Y")
            except Exception:
                mmddyyyy = show_details.get("show_date")
            header = (
                f"Next Show: {mmddyyyy} at "
                f"{show_details.get('venue_name')} in "
                f"{show_details.get('venue_city')}, {show_details.get('venue_state')}"
            )
        else:
            try:
                mmddyyyy = pd.to_datetime(reference_date).strftime("%m/%d/%Y") if reference_date else ""
            except Exception:
                mmddyyyy = reference_date or ""
            header = f"Next Show: {mmddyyyy}"
        st.markdown(f"<h4 style='text-align: center;'>{header}</h4>", unsafe_allow_html=True)

        display_df = predictions_df.copy()
        # Keep and order the desired columns
        # Harmonize columns between notebook and ckplus
        desired_order = [
            "rank",
            "song_name",
            # notebook-only column; may not exist for ckplus
            "plays_past_year",
            # ckplus-only columns; may not exist for notebook
            "ckplus_score",
            "avg_gap",
            "gap_ratio",
            "gap_z_score",
            # shared-ish
            "LTP",
            "current_gap",
        ]
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

        # Larger height to show ~25 rows without scrolling
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=900)

        # Caption at the bottom with loaded_at and predicted_at without seconds
        loaded_at = pd.Timestamp.utcnow().floor("min")
        predicted_at_raw = meta.get("predicted_at") if meta else None
        try:
            predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
        except Exception:
            predicted_at = None
        loaded_at_str = loaded_at.strftime("%Y-%m-%d %H:%M")
        predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at is not None else "unknown"
        st.markdown(
            f"<p style='text-align: center; color: gray;'>Data Loaded: {loaded_at_str} - Predictions Made: {predicted_at_str}</p>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("No predictions found. Please run the prediction scripts first.")

except Exception as e:
    st.error(
        f"An error occurred while trying to connect to the database or render the page. "
        f"Please ensure your .env file is correctly configured. Error: {e}"
    )
