import pandas as pd

from jambandnerd.data_collection.wsp.utils import get_logger
from jambandnerd.models.ckplus_model import run_ckplus_model
from jambandnerd.models.prediction_exporter import save_predictions_to_supabase
from jambandnerd.predictions.wsp.data_loader import load_wsp_data
from jambandnerd.predictions.wsp.data_transformer import transform_wsp_data

logger = get_logger(__name__, add_console_handler=True)

BAND_NAME = "wsp"
MODEL_NAME = "ckplus"

# WSP-specific configuration
WSP_CONFIG = {
    "gap_threshold": 100,  # WSP plays less frequently, higher gap threshold
    "top_predictions": 100,
    "recent_shows_filter": 3,
}

def main():
    """Run the full WSP CK+ prediction pipeline."""
    logger.info("Starting WSP CK+ prediction pipeline...")

    # Step 1: Load data from Supabase (assumes data is already up-to-date)
    wsp_data = load_wsp_data()
    if all(df.empty for df in wsp_data.values()):
        logger.error("Failed to load WSP data from Supabase. Halting pipeline.")
        return False

    # Step 2: Transform data for the model
    transformed_data = transform_wsp_data(wsp_data)
    if transformed_data.empty:
        logger.error("Failed to transform WSP data. Halting pipeline.")
        return False

    # Step 3: Run the CK+ model
    logger.info("Running the CK+ model on WSP data...")
    # CK+ model expects individual DataFrames with specific column names
    # Keep DataFrames separate - the model handles merging internally
    songs_for_model = wsp_data["songs"].rename(columns={'code': 'song_id'})
    shows_for_model = wsp_data["shows"].rename(columns={'link': 'show_id', 'date': 'show_date'})
    # Add the band column that the CK+ model expects
    shows_for_model['band'] = BAND_NAME
    # Add song_id to setlists by mapping song_name to songs table
    # Need to handle case differences between setlist and songs data
    songs_normalized = wsp_data["songs"].copy()
    songs_normalized['song_lower'] = songs_normalized['song'].str.lower()
    setlists_normalized = wsp_data["setlists"].copy()
    setlists_normalized['song_name_lower'] = setlists_normalized['song_name'].str.lower()

    setlists_with_ids = setlists_normalized.merge(
        songs_normalized[['code', 'song', 'song_lower']],
        left_on='song_name_lower',
        right_on='song_lower',
        how='left'
    )
    setlists_for_model = setlists_with_ids.rename(columns={'link': 'show_id', 'code': 'song_id'})

    predictions = run_ckplus_model(
        song_data=songs_for_model,
        show_data=shows_for_model,
        venue_data=pd.DataFrame(),  # WSP doesn't have separate venue data
        setlist_data=setlists_for_model,
        transition_data=pd.DataFrame(),  # WSP doesn't have transition data
        gap_threshold=WSP_CONFIG["gap_threshold"],
        top_n=WSP_CONFIG["top_predictions"]
    )
    if predictions.empty:
        logger.error("CK+ model did not return any predictions. Halting pipeline.")
        return False

    # Step 4: Export predictions to Supabase
    table_name = f"predictions_{MODEL_NAME}"
    logger.info("Exporting %d predictions to Supabase table: %s", len(predictions), table_name)
    save_predictions_to_supabase(predictions, table_name)

    logger.info("WSP CK+ prediction pipeline completed successfully.")
    return True

if __name__ == "__main__":
    main()
