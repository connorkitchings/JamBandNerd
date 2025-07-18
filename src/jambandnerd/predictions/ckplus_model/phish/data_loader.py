"""
Data loader for Phish CK+ prediction pipeline.
Loads setlist, show, and song data and merges them for analysis.
"""

import pandas as pd
from logger import get_logger

logger = get_logger(__name__)


def load_setlist_and_showdata(setlist_path, showdata_path, songdata_path):
    """
    Loads setlist, show, and song data for Phish. Merges show_date and song name into setlist data.
    Returns merged DataFrame with a 'song' column.
    """
    df = pd.read_csv(setlist_path)
    show_df = pd.read_csv(showdata_path, usecols=["showid", "showdate"])
    show_df["showdate"] = pd.to_datetime(show_df["showdate"])
    df = df.merge(show_df, on="showid", how="left")
    song_df = pd.read_csv(songdata_path, usecols=["song_id", "song"])
    df = df.merge(song_df, left_on="songid", right_on="song_id", how="left")
    logger.info(
        "Loaded setlist (%s rows) from %s, shows from %s, songs from %s",
        f"{len(df):,}",
        setlist_path,
        showdata_path,
        songdata_path,
    )
    return df
