"""
Phish data loaders for API and web scraping. All config dependencies removed; paths are hardcoded.
"""

import logging
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .api_utils import make_api_request


def load_song_data(api_key: str, logger: logging.Logger) -> pd.DataFrame:
    """
    Load song data from the Phish API.

    Args:
        api_key (str): API key for authentication.
        logger (logging.Logger): Logger instance.
    Returns:
        pd.DataFrame: DataFrame containing song data.
    """
    song_data = pd.DataFrame(make_api_request("songs", api_key, logger)["data"])
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

    return result_data


def load_show_data(api_key: str, logger: logging.Logger, since: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load show and venue data from the Phish API.

    Args:
        api_key (str): API key for authentication.
        logger (logging.Logger): Logger instance.
        since (str | None): Optional date string in YYYY-MM-DD format to fetch shows since.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Tuple of DataFrames for show data and venue data.
    """
    if since:
        endpoint = f"shows/since/{since}"
    else:
        endpoint = "shows/artist/phish"

    shows = pd.DataFrame(make_api_request(endpoint, api_key, logger)["data"])

    if shows.empty:
        return pd.DataFrame(), pd.DataFrame()

    venue_data = (
        shows[["venueid", "venue", "city", "state", "country"]]
        .drop_duplicates()
        .sort_values("venueid")
        .reset_index(drop=True)
    )
    show_data = (
        shows[
            [
                "showid",
                "showdate",
                "venueid",
                "tourid",
                "exclude_from_stats",
                "setlist_notes",
            ]
        ]
        .sort_values("showdate")
        .reset_index(drop=True)
        .reset_index(names="show_number")
        .assign(show_number=lambda x: x["show_number"] + 1)
    )
    return show_data, venue_data


def load_setlist_data(api_key: str, logger: logging.Logger, show_ids: list[int] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load setlist and transition data from the Phish API.

    Args:
        api_key (str): API key for authentication.
        logger (logging.Logger): Logger instance.
        show_ids (list[int] | None): Optional list of show IDs to fetch setlists for.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Tuple of DataFrames for setlist data and transition data.
    """
    try:
        all_setlists = []
        if show_ids:
            # Chunk show_ids to avoid URI too long error
            chunk_size = 100
            for i in range(0, len(show_ids), chunk_size):
                chunk = show_ids[i:i + chunk_size]
                logger.info(f"Fetching setlists for show_ids chunk {i // chunk_size + 1}/{(len(show_ids) + chunk_size - 1) // chunk_size}")
                endpoint = f"setlists/showids/{','.join(map(str, chunk))}"
                setlist_data_response = make_api_request(endpoint, api_key, logger)
                if setlist_data_response and "data" in setlist_data_response:
                    all_setlists.extend(setlist_data_response["data"])
        else:
            endpoint = "setlists/artistid/1"
            setlist_data_response = make_api_request(endpoint, api_key, logger)
            if setlist_data_response and "data" in setlist_data_response:
                all_setlists = setlist_data_response["data"]

        if not all_setlists:
            logger.error("Failed to retrieve setlist data or data is malformed.")
            return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames on error

        # Create a DataFrame from the raw API data
        full_setlist_data = pd.DataFrame(all_setlists)

        # Create the smaller transitions DataFrame first
        transition_data = (
            full_setlist_data[full_setlist_data["transition"].notna()][
                ["transition", "trans_mark"]
            ]
            .drop_duplicates()
            .sort_values(by=["transition"])
        )

        # Define the columns we need for the final setlist DataFrame
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

        # Create the final DataFrame with only the necessary columns, avoiding a full copy
        setlist_df = full_setlist_data[setlist_columns].copy()

        return setlist_df, transition_data
    except Exception as e:
        logger.exception("CRITICAL ERROR in load_setlist_data: %s", str(e))
        raise
