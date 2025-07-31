import pandas as pd

from jambandnerd.data_collection.wsp.utils import get_logger
from jambandnerd.models.notebook_model import run_notebook_model
from jambandnerd.models.prediction_exporter import save_predictions_to_supabase
from jambandnerd.predictions.wsp.data_loader import load_wsp_data
from jambandnerd.predictions.wsp.data_transformer import transform_wsp_data

logger = get_logger(__name__, add_console_handler=True)

BAND_NAME = "wsp"
MODEL_NAME = "notebook"


def main():
    """Run the full WSP Notebook prediction pipeline."""
    logger.info("Starting WSP Notebook prediction pipeline...")

    # Step 1: Load data from Supabase (assumes data is already up-to-date)
    wsp_data = load_wsp_data()
    if all(df.empty for df in wsp_data.values()):
        logger.error("Failed to load WSP data from Supabase. Halting pipeline.")
        return False

    # Diagnostic: Log the date range of the shows data
    shows_df = wsp_data.get("shows")
    if shows_df is not None and not shows_df.empty:
        shows_df["date"] = pd.to_datetime(shows_df["date"])
        min_date = shows_df["date"].min().strftime("%Y-%m-%d")
        max_date = shows_df["date"].max().strftime("%Y-%m-%d")
        logger.info("Loaded %d shows with date range from %s to %s", len(shows_df), min_date, max_date)

    # Step 2: Transform data
    transformed_data = transform_wsp_data(wsp_data)
    if transformed_data.empty:
        logger.error("Failed to transform WSP data. Halting pipeline.")
        return

    # Step 3: Run the Notebook model
    logger.info("Running the Notebook model on WSP data...")
    # Notebook model expects individual DataFrames with specific column names
    # Keep DataFrames separate - the model handles merging internally
    songs_for_model = wsp_data["songs"].rename(columns={"code": "song_id"})
    shows_for_model = wsp_data["shows"].rename(
        columns={"link": "show_id", "date": "show_date"}
    )
    # Add the band column that the Notebook model expects
    shows_for_model['band'] = BAND_NAME
    # Add song_id to setlists by mapping song_name to songs table
    # Need to handle case differences between setlist and songs data
    songs_normalized = wsp_data["songs"].copy()
    songs_normalized["song_lower"] = songs_normalized["song"].str.lower()
    setlists_normalized = wsp_data["setlists"].copy()
    setlists_normalized["song_name_lower"] = setlists_normalized[
        "song_name"
    ].str.lower()

    setlists_with_ids = setlists_normalized.merge(
        songs_normalized[["code", "song", "song_lower"]],
        left_on="song_name_lower",
        right_on="song_lower",
        how="left",
    )
    setlists_for_model = setlists_with_ids.rename(
        columns={"link": "show_id", "code": "song_id"}
    )

    predictions = run_notebook_model(
        song_data=songs_for_model,
        show_data=shows_for_model,
        venue_data=pd.DataFrame(),  # WSP doesn't have separate venue data
        setlist_data=setlists_for_model,
        transition_data=pd.DataFrame(),  # WSP doesn't have transition data
        recent_shows_filter=100,  # Or get from a config
    )

    if predictions is None or predictions.empty:
        logger.error("Notebook model returned no predictions")
        return

    # Step 4: Export predictions to Supabase
    table_name = f"predictions_{MODEL_NAME}"
    logger.info("Exporting %d predictions to Supabase table: %s", len(predictions), table_name)
    success = save_predictions_to_supabase(predictions, table_name)

    if success:
        logger.info(" WSP Notebook prediction pipeline completed successfully")
        return True
    else:
        logger.error(" Failed to export predictions to Supabase")
        return False


if __name__ == "__main__":
    main()
