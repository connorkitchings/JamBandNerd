import pandas as pd

from jambandnerd.models.data_exporter import export_dataframe_to_supabase
from jambandnerd.data_collection.wsp.utils import get_logger

logger = get_logger(__name__, add_console_handler=True)

def save_wsp_data_to_supabase(songs: pd.DataFrame, shows: pd.DataFrame, setlists: pd.DataFrame):
    """
    Saves WSP songs, shows, and setlist data to their respective Supabase tables.

    Args:
        songs (pd.DataFrame): DataFrame containing song data.
        shows (pd.DataFrame): DataFrame containing show data.
        setlists (pd.DataFrame): DataFrame containing setlist data.
    """
    logger.info("Saving WSP data to Supabase...")

    # Save songs
    if not songs.empty:
        logger.info(f"Upserting {len(songs)} records to wsp_songs...")
        export_dataframe_to_supabase(
            songs,
            'wsp_songs',
            'code',
            logger
        )
    else:
        logger.warning("Song data is empty, skipping save.")

    # Save shows
    if not shows.empty:

        logger.info(f"Upserting {len(shows)} records to wsp_shows...")
        export_dataframe_to_supabase(
            shows,
            'wsp_shows',
            'link',
            logger
        )
    else:
        logger.warning("Show data is empty, skipping save.")

    # Save setlists
    if not setlists.empty:
        logger.info(f"Upserting {len(setlists)} records to wsp_setlists...")
        # Use a composite key for upsert conflict resolution
        export_dataframe_to_supabase(
            setlists,
            'wsp_setlists',
            'link,song_index_show',
            logger
        )
    else:
        logger.warning("Setlist data is empty, skipping save.")

    logger.info("Successfully saved all WSP data to Supabase.")
