
import streamlit as st
import pandas as pd
from supabase import Client
import altair as alt

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
    """Fetch the latest predictions for a given band from the unified table."""
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
        predictions_json = row.get("predictions")
        df = pd.DataFrame(predictions_json) if predictions_json else pd.DataFrame()
        if "last_played_date" in df.columns and "LTP" not in df.columns:
            df.rename(columns={"last_played_date": "LTP"}, inplace=True)
        return df, reference_date, {
            "band": row.get("band"),
            "model_version": row.get("model_version"),
            "predicted_at": row.get("predicted_at"),
            "top_k": row.get("top_k"),
        }
    except Exception as e:
        st.error(f"Failed to fetch predictions: {e}")
        return pd.DataFrame(), None, {}

@st.cache_data
def fetch_per_show_accuracy(_db_client: Client, band: str, model: str, limit: int = 100) -> pd.DataFrame:
    """Fetch the last N per-show accuracy records for charting."""
    try:
        model_version = f"{model}_v1"
        response = (
            _db_client.table("accuracy_per_show")
            .select("*")
            .eq("band", band)
            .eq("model_version", model_version)
            .order("show_date", desc=True)
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch per-show accuracy: {e}")
        return pd.DataFrame()


def fetch_show_details_by_date(_db_client: Client, reference_date: str | None) -> dict | None:
    """Fetch venue details for the given reference show date from goose_shows_raw."""
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
        return resp.data[0] if resp.data else None
    except Exception:
        return None


@st.cache_data
def fetch_last_collection_time(_db_client: Client, band: str) -> str | None:
    """Fetch the most recent collection run timestamp for a band from collection_runs."""
    try:
        resp = (
            _db_client.table("collection_runs")
            .select("created_at")
            .eq("band", band)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0].get("created_at")
    except Exception:
        pass
    return None

st.set_page_config(page_title="JamBandNerd", layout="wide")

# --- Sidebar --- #
band_options = ["Goose"]
selected_band = st.sidebar.selectbox("Select a Band", band_options)
model_options = {"Notebook": "notebook", "CK+": "ckplus"}
selected_model_label = st.sidebar.selectbox("Select a Model", list(model_options.keys()))
selected_model = model_options[selected_model_label]
display_method_explanation(selected_model_label)

# --- Main App --- #
try:
    supabase_client = get_supabase_client()
    selected_band_slug = selected_band.lower()

    # --- Predictions View ---
    predictions_df, ref_date, meta = fetch_predictions(supabase_client, selected_band_slug, selected_model)
    st.markdown("<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<h3 style='text-align: center;'>{selected_band.title()} Predictions - {selected_model_label}</h3>",
        unsafe_allow_html=True,
    )

    if not predictions_df.empty:
        show_details = fetch_show_details_by_date(supabase_client, ref_date)
        date_str = pd.to_datetime(ref_date).strftime("%m/%d/%Y") if ref_date else ""
        header = f"Next Show: {date_str}"
        if show_details:
            header += f" at {show_details.get('venue_name')} in {show_details.get('venue_city')}, {show_details.get('venue_state')}"
        st.markdown(f"<h4 style='text-align: center;'>{header}</h4>", unsafe_allow_html=True)

        # Reorder and rename columns per model
        display_df = predictions_df.copy()
        if selected_model == "notebook":
            desired_order = ["rank", "song_name", "plays_past_year", "LTP", "current_gap"]
            cols = [c for c in desired_order if c in display_df.columns]
            display_df = display_df[cols]
            display_df = display_df.rename(
                columns={
                    "rank": "Rank",
                    "song_name": "Song",
                    "plays_past_year": "Plays in Last Year",
                    "LTP": "LTP",
                    "current_gap": "Current Gap",
                }
            )
        else:  # ckplus
            desired_order = [
                "rank",
                "song_name",
                "LTP",
                "current_gap",
                "avg_gap",
                "gap_ratio",
                "gap_z_score",
                "ckplus_score",
            ]
            cols = [c for c in desired_order if c in display_df.columns]
            display_df = display_df[cols]
            display_df = display_df.rename(
                columns={
                    "rank": "Rank",
                    "song_name": "Song",
                    "LTP": "LTP",
                    "current_gap": "Current Gap",
                    "avg_gap": "Avg Gap",
                    "gap_ratio": "Gap Ratio",
                    "gap_z_score": "Gap Z-Score",
                    "ckplus_score": "CKPlus Score",
                }
            )

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=900)

        # Caption under table with collected_at and predicted_at
        collected_at_raw = meta.get("collected_at") if meta else None
        if not collected_at_raw:
            # Fallback to last collection run in collection_runs
            collected_at_raw = fetch_last_collection_time(supabase_client, selected_band_slug)
        predicted_at_raw = meta.get("predicted_at") if meta else None
        try:
            collected_at = pd.to_datetime(collected_at_raw).floor("min") if collected_at_raw else None
        except Exception:
            collected_at = None
        try:
            predicted_at = pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
        except Exception:
            predicted_at = None
        collected_at_str = collected_at.strftime("%Y-%m-%d %H:%M") if collected_at is not None else "unknown"
        predicted_at_str = predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at is not None else "unknown"
        st.markdown(
            f"<p style='text-align: center; color: gray;'>Data Collected: {collected_at_str} - Predictions Made: {predicted_at_str}</p>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("No predictions found for the selected model. Please run the prediction scripts first.")

    # --- Historical Accuracy View ---
    st.markdown("---")
    st.markdown(f"<h3 style='text-align: center;'>Historical Accuracy - {selected_model_label}</h3>", unsafe_allow_html=True)

    per_show_accuracy_df = fetch_per_show_accuracy(supabase_client, selected_band_slug, selected_model)

    if not per_show_accuracy_df.empty:
        num_shows = len(per_show_accuracy_df)
        st.markdown(f"<p style='text-align: center; color: gray;'>Aggregate metrics based on the last {num_shows} completed shows.</p>", unsafe_allow_html=True)
        
        # Calculate aggregate metrics from the per-show data (K=50)
        avg_matches = per_show_accuracy_df['k50_matches'].mean()
        avg_recall = per_show_accuracy_df['k50_recall'].mean()

        # Center the two metrics by adding side spacers
        cols = st.columns([1, 2, 2, 1])
        with cols[1]:
            st.metric("Recall @ K=50", f"{avg_recall:.1%}")
        with cols[2]:
            st.metric("Avg. Matches @ K=50", f"{avg_matches:.2f}")
    
        # Build Altair line chart for Top-50 Recall with show index on X and matches in tooltip
        # Most recent show should be #1, older shows increase to the right
        df_sorted = per_show_accuracy_df.sort_values("show_date", ascending=False).reset_index(drop=True).copy()
        df_sorted["show_num"] = range(1, len(df_sorted) + 1)

        # Enrich with venue details (optional)
        try:
            show_ids = df_sorted["show_id"].dropna().astype(str).unique().tolist()
            if show_ids:
                shows_resp = (
                    supabase_client.table("goose_shows_raw")
                    .select("show_id,venue_name,venue_city,venue_state")
                    .in_("show_id", show_ids)
                    .execute()
                )
                venue_map = {}
                if shows_resp.data:
                    for r in shows_resp.data:
                        vid = str(r.get("show_id"))
                        vname = r.get("venue_name") or ""
                        vcity = r.get("venue_city") or ""
                        vstate = r.get("venue_state") or ""
                        venue_map[vid] = ", ".join([p for p in [vname, vcity, vstate] if p])
                df_sorted["_venue"] = df_sorted["show_id"].astype(str).map(venue_map)
            else:
                df_sorted["_venue"] = None
        except Exception:
            df_sorted["_venue"] = None

        chart_df = df_sorted[["show_num", "show_date", "k50_recall", "k50_matches", "_venue"]].copy()
        chart_df["show_date"] = pd.to_datetime(chart_df["show_date"])  # ensure temporal type
        chart_df.rename(columns={"k50_recall": "Recall", "k50_matches": "Matches"}, inplace=True)

        line = (
            alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("show_num:Q", title="Show #"),
                y=alt.Y("Recall:Q", title="Recall (Top-50)", scale=alt.Scale(domain=[0, 1])),
                tooltip=[
                    alt.Tooltip("show_num:Q", title="Show #"),
                    alt.Tooltip("show_date:T", title="Show Date"),
                    alt.Tooltip("_venue:N", title="Venue"),
                    alt.Tooltip("Recall:Q", title="Recall", format=".1%"),
                    alt.Tooltip("Matches:Q", title="Matches in Top-50"),
                ],
            )
        )
        st.altair_chart(line, use_container_width=True)
        st.markdown(
            """
<div style='font-size:0.9em; color: gray; text-align:center; margin-top:8px;'>
<b>Recall</b>: Of the songs actually played, the fraction that appear in the top-K predictions.
</div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("No per-show accuracy data found. Please run the backtesting scripts.")

except Exception as e:
    st.error(
        f"An error occurred while trying to connect to the database or render the page. "
        f"Please ensure your .env file is correctly configured. Error: {e}"
    )
