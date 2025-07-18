"""
Data loading utilities for WSP CK+ prediction pipelines.
Handles merging setlist, show, and song data for modeling.
"""

import pandas as pd

from .utils.logger import get_logger

logger = get_logger(__name__)


def load_setlist_and_showdata(setlist_path, showdata_path, songdata_path):
    """
    Loads setlist, show, and song data for WSP. Merges show date and song name into setlist data.
    Returns merged DataFrame with a 'song' column and 'show_date' column (standardized for modeling).
    """
    df = pd.read_csv(setlist_path)
    # Remove Jam and Drums from setlist
    df = df[~df["song_name"].isin(["JAM", "DRUMS"])]
    show_df = pd.read_csv(showdata_path, usecols=["date", "show_index_overall", "link"])
    show_df = show_df.rename(columns={"date": "show_date"})
    show_df["show_date"] = pd.to_datetime(show_df["show_date"], errors="coerce")
    df = df.merge(show_df, on="link", how="left")
    song_df = pd.read_csv(songdata_path, usecols=["song"])
    df = df.merge(song_df, left_on="song_name", right_on="song", how="left")
    # Drop rows with missing song names
    df = df[~df["song_name"].isnull()].copy()
    # Merge song info, but ensure only one 'song' column remains
    df["song"] = df["song_name"].astype(str)
    # Remove any duplicate song columns from merge
    for col in ["song_name", "song_x", "song_y"]:
        if col in df.columns and col != "song":
            df = df.drop(columns=[col])
    logger.info(
        "Loaded setlist (%s) rows from %s, shows from %s, songs from %s",
        f"{len(df):,}",
        setlist_path,
        showdata_path,
        songdata_path,
    )
    return df
