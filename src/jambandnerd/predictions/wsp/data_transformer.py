import pandas as pd

from jambandnerd.data_collection.wsp.utils import get_logger

logger = get_logger(__name__, add_console_handler=True)

def transform_wsp_data(wsp_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Transforms raw WSP data from Supabase into a format suitable for prediction models.

    Args:
        wsp_data: A dictionary containing 'songs', 'shows', and 'setlists' DataFrames.

    Returns:
        A single DataFrame merged and formatted for the prediction models.
    """
    songs = wsp_data.get("songs")
    shows = wsp_data.get("shows")
    setlists = wsp_data.get("setlists")

    if any(df is None or df.empty for df in [songs, shows, setlists]):
        logger.error("One or more WSP dataframes are missing or empty. Cannot transform data.")
        return pd.DataFrame()

    try:
        # Merge shows and setlists
        merged_df = pd.merge(shows, setlists, on='link', how='inner')

        # Merge with songs
        # Note: WSP 'song_name' in setlists should match 'song' in songs table
        final_df = pd.merge(merged_df, songs, left_on='song_name', right_on='song', how='left')

        # Rename columns to match model expectations
        column_mapping = {
            'code': 'song_id',
            'song_x': 'song_name',
            'link': 'show_id',
            'date': 'show_date',
            'venue_full': 'show_venue',
            'city': 'show_city',
            'state': 'show_state',
            'set_name': 'set_name',
            'is_into': 'is_into',
            # Add other mappings as needed by models
        }
        final_df = final_df.rename(columns=column_mapping)

        # Ensure required columns exist
        required_cols = ['song_id', 'song_name', 'show_id', 'show_date']
        for col in required_cols:
            if col not in final_df.columns:
                logger.error(f"Missing required column '{col}' after transformation.")
                return pd.DataFrame()

        # Convert date column to datetime
        final_df['show_date'] = pd.to_datetime(final_df['show_date'])

        logger.info(f"Successfully transformed and merged WSP data. Final shape: {final_df.shape}")

        return final_df

    except Exception as e:
        logger.exception(f"An error occurred during data transformation: {e}")
        return pd.DataFrame()
