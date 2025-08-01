"""
Phish data loaders for API and web scraping. All config dependencies removed; paths are hardcoded.
"""

import os
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .call_api import get_api_key, make_api_request
from .utils import get_logger

# Ensure logs/Goose/ is always relative to the project root, not src/
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
logs_dir = os.path.join(project_root, "logs", "Phish")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "phish_pipeline.log")
logger = get_logger(__name__, log_file=log_file, add_console_handler=True)
DATA_COLLECTED_DIR = os.path.join(project_root, "data", "phish", "collected")



def load_song_data(api_key: str) -> "pd.DataFrame":
    """
    Load song data from the Phish API.

    Args:
        api_key (str): API key for authentication.
    Returns:
        pd.DataFrame: DataFrame containing song data.
    """
    song_data = pd.DataFrame(make_api_request("songs", api_key)["data"])
    song_data = song_data.drop(columns=["slug", "last_permalink", "debut_permalink"])
    response = requests.get("https://phish.net/song", timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    tables = pd.read_html(StringIO(str(soup.find_all("table"))))
    if not tables:
        logger.error("Expected table not found in Phish song page.")
        return pd.DataFrame()
    website_data = tables[0].sort_values(by="Song Name").reset_index(drop=True)
    merged_data = pd.merge(
        song_data, website_data, left_on="song", right_on="Song Name", how="left"
    )

    # Filter out rows where Song Name is null (songs not found on website)
    merged_data = merged_data[merged_data["Song Name"].notna()]

    # Drop duplicates based on the primary key before renaming and returning
    merged_data.drop_duplicates(subset=["songid"], inplace=True)

    final_columns = {
        "songid": "song_id",
        "Song Name": "song",
        "Original Artist": "original_artist",
        "Debut": "debut_date",
    }
    result_data = merged_data[list(final_columns.keys())].rename(columns=final_columns)

    # Convert debut_date from YYYY-MM-DD to MM/DD/YYYY format for consistency
    result_data['debut_date'] = pd.to_datetime(result_data['debut_date'], errors='coerce').dt.strftime('%m/%d/%Y')
    # Explicitly set debut_date as string type to prevent Supabase from inferring it as date type
    result_data['debut_date'] = result_data['debut_date'].astype(str)

    return result_data


def load_show_data(api_key: str) -> tuple["pd.DataFrame", "pd.DataFrame"]:
    """
    Load show and venue data from the Phish API.

    Args:
        api_key (str): API key for authentication.
    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Tuple of DataFrames for show data and venue data.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    shows = pd.DataFrame(make_api_request("shows/artist/phish", api_key)["data"])
    past_shows = shows[shows["showdate"] < today]
    future_shows = shows[shows["showdate"] >= today].sort_values("showdate").head(1)
    all_shows = pd.concat([past_shows, future_shows])
    venue_data = (
        all_shows[["venueid", "venue", "city", "state", "country"]]
        .drop_duplicates()
        .sort_values("venueid")
        .reset_index(drop=True)
    )
    show_data = (
        all_shows[
            [
                "showid",
                "showdate",
                "venueid",
                "tourid",
                "exclude_from_stats",
                "setlist_notes",
            ]
        ]
        .assign(showdate=lambda x: pd.to_datetime(x["showdate"]).dt.strftime("%m/%d/%Y"))
        .sort_values("showdate")
        .reset_index(drop=True)
        .reset_index(names="show_number")
        .assign(show_number=lambda x: x["show_number"] + 1)
    )
    # Explicitly set showdate as string type to prevent Supabase from inferring it as date type
    show_data["showdate"] = show_data["showdate"].astype(str)
    show_data["tourid"] = show_data["tourid"].astype("Int64").astype(str)
    return show_data, venue_data


def load_setlist_data(api_key: str) -> tuple["pd.DataFrame", "pd.DataFrame"]:
    """
    Load setlist and transition data from the Phish API.

    Args:
        api_key (str): API key for authentication.
    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Tuple of DataFrames for setlist data and transition data.
    """
    try:
        setlist_data_response = make_api_request("setlists/artistid/1", api_key)
        if not setlist_data_response or "data" not in setlist_data_response:
            logger.error("Failed to retrieve setlist data or data is malformed.")
            return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames on error
        setlist_data = pd.DataFrame(setlist_data_response["data"])
        # Filter out rows where the transition is null to avoid null primary keys
        transition_data = (
            setlist_data[setlist_data["transition"].notna()][["transition", "trans_mark"]]
            .drop_duplicates()
            .sort_values(by=["transition"])
        )
        setlist_columns = [
            "showid",
            "uniqueid",
            "songid",
            "set",
            "position",
            "transition",
            "isreprise",
            "isjam",
            "isjamchart",
            "jamchart_description",
            "tracktime",
            "gap",
            "is_original",
            "soundcheck",
            "footnote",
            "exclude",
        ]
        setlist_df = setlist_data[setlist_columns].copy()

        # Filter out rows where uniqueid is null to avoid null primary keys
        setlist_df = setlist_df[setlist_df["uniqueid"].notna()]

        return setlist_df, transition_data
    except Exception as e:
        logger.exception("CRITICAL ERROR in load_setlist_data: %s", str(e))
        raise


def load_phish_data() -> dict:
    """
    Load all Phish data from API for prediction models.

    Returns:
        dict: Dictionary containing all loaded DataFrames
    """
    # Load API key from environment
    api_key = get_api_key()

    logger.info("Loading Phish data from API...")

    # Load all data
    logger.info("Loading song data...")
    song_data = load_song_data(api_key)

    logger.info("Loading show and venue data...")
    show_data, venue_data = load_show_data(api_key)

    logger.info("Loading setlist and transition data...")
    setlist_data, transition_data = load_setlist_data(api_key)

    logger.info("✅ Successfully loaded all Phish data from API")
    logger.info("Loaded: %d songs, %d shows, %d venues, %d setlist entries",
                len(song_data), len(show_data), len(venue_data), len(setlist_data))

    return {
        'song_data': song_data,
        'show_data': show_data,
        'venue_data': venue_data,
        'setlist_data': setlist_data,
        'transition_data': transition_data
    }
