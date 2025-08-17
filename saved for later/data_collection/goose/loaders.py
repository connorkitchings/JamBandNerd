"""
Goose Data Loaders
"""

import json
import os
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .call_api import make_api_request
from .utils import get_logger


def get_next_show_info(show_data: pd.DataFrame, logger=None) -> dict:
    """
    Get next show info (show_date, venue_name, city, state) by calling the Goose API.
    Returns dict with these keys (values can be None if not found).
    """
    if logger is None:
        logger = get_logger(__name__)
    today = datetime.today().strftime("%Y-%m-%d")
    next_show_row = (
        show_data[show_data["show_date"] >= today].sort_values("show_date").head(1)
    )
    show_id = next_show_row.iloc[0]["show_id"]
    result = {"show_date": None, "venue_name": None, "city": None, "state": None}
    if show_id is not None:
        try:
            api_response = make_api_request(f"shows/show_id/{show_id}", version="v2")
            if "data" in api_response and api_response["data"]:
                api_show = api_response["data"]
                if isinstance(api_show, list):
                    api_show = api_show[0] if api_show else None
                if isinstance(api_show, dict):
                    result["show_date"] = api_show.get("showdate") or api_show.get(
                        "show_date"
                    )
                    result["venue_name"] = api_show.get("venuename")
                    result["city"] = api_show.get("city")
                    result["state"] = api_show.get("state")
        except Exception as e:
            logger.warning(
                "Failed to fetch show info from API for show_id=%s: %s", show_id, e
            )
    return result


# Ensure logs/Goose/ is always relative to the project root, not src/
"""
Goose Data Loaders
"""

import logging
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .call_api import make_api_request


def load_song_data(logger: logging.Logger) -> pd.DataFrame:
    """
    Load and process Goose song data from API and website scrape.

    Args:
        logger: Logger instance for logging.

    Returns:
        pd.DataFrame: DataFrame containing merged song data.
    """
    song_table_idx = 1
    songdata_api = pd.DataFrame(make_api_request("songs", "v2")["data"]).drop(
        columns=["slug", "created_at", "updated_at"], errors="ignore"
    )
    response = requests.get("https://elgoose.net/song/", timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    tables = pd.read_html(StringIO(str(soup.find_all("table"))))
    if not tables or len(tables) <= song_table_idx:
        logger.error(
            "Expected table at index %d not found in Goose song page.", song_table_idx
        )
        return pd.DataFrame()
    songdata_scrape = (
        tables[song_table_idx].sort_values(by="Song Name").reset_index(drop=True)
    )
    merged_data = songdata_api.merge(
        songdata_scrape, left_on="name", right_on="Song Name", how="inner"
    )
    columns = [
        "id",
        "Song Name",
        "isoriginal",
        "Original Artist",
        "Debut Date",
        "Last Played",
        "Times Played Live",
        "Avg Show Gap",
    ]
    merged_data = merged_data[columns].copy()
    final_columns = {
        "id": "song_id",
        "Song Name": "song",
        "isoriginal": "is_original",
        "Original Artist": "original_artist",
        "Debut Date": "debut_date",
        "Last Played": "last_played",
        "Times Played Live": "times_played",
        "Avg Show Gap": "avg_show_gap",
    }
    return merged_data.rename(columns=final_columns)


def load_show_data(logger: logging.Logger, since: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and process Goose show, venue, and tour data.

    Args:
        logger: Logger instance for logging.
        since (str | None): Optional date string in YYYY-MM-DD format to filter shows since.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        Tuple of DataFrames for show data, venue data, and tour data.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    shows = pd.DataFrame(make_api_request("shows", "v2")["data"])

    if since:
        shows = shows[shows["showdate"] > since]

    past_shows = shows[shows["showdate"] < today]
    future_shows = shows[shows["showdate"] >= today].sort_values("showdate").head(1)
    all_shows = pd.concat([past_shows, future_shows])
    all_shows = (
        all_shows[(all_shows["artist"] == "Goose")].copy().reset_index(drop=True)
    )
    venue_data = (
        all_shows[["venue_id", "venuename", "city", "state", "country", "location"]]
        .drop_duplicates()
        .sort_values("venue_id")
        .reset_index(drop=True)
        .rename(columns={"venue": "venue_name"})
    )
    tour_data = (
        all_shows[["tour_id", "tourname"]]
        .drop_duplicates()
        .sort_values("tour_id")
        .reset_index(drop=True)
    )
    show_data = (
        all_shows[["show_id", "showdate", "venue_id", "tour_id", "showorder"]]
        .sort_values("showdate")
        .reset_index(names="show_number")
        .rename(columns={"showdate": "show_date", "showorder": "show_order"})
        .assign(show_number=lambda x: x["show_number"] + 1)
    )
    show_data["tour_id"] = show_data["tour_id"].astype("Int64").astype(str)
    return show_data, venue_data, tour_data


def load_setlist_data(logger: logging.Logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load and process Goose setlist and transition data.

    Args:
        logger: Logger instance for logging.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Tuple of DataFrames for setlist data and transition data.
    """
    setlist_df = pd.DataFrame(make_api_request("setlists", "v1")["data"])
    transition_data = (
        setlist_df[["transition_id", "transition"]]
        .drop_duplicates()
        .sort_values(by=["transition_id"])
    )
    setlist_data = (
        setlist_df[setlist_df["artist"] == "Goose"].copy().reset_index(drop=True)
    )

    # Clean boolean columns to handle invalid data from the API
    boolean_columns = [
        "isreprise",
        "isjam",
        "isjamchart",
        "soundcheck",
        "isverified",
        "isrecommended",
    ]
    for col in boolean_columns:
        if col in setlist_data.columns:
            # Convert to boolean, coercing errors to NaT, then fill NaNs with False
            setlist_data[col] = pd.to_numeric(setlist_data[col], errors='coerce').fillna(0).astype(bool)

    # Clean integer columns to handle invalid data from the API
    integer_columns = ["show_id", "song_id", "setnumber", "position", "transition_id"]
    for col in integer_columns:
        if col in setlist_data.columns:
            setlist_data[col] = pd.to_numeric(setlist_data[col], errors='coerce').fillna(0).astype(int)
    setlist_columns = [
        "uniqueid",
        "show_id",
        "song_id",
        "setnumber",
        "position",
        "tracktime",
        "transition_id",
        "isreprise",
        "isjam",
        "footnote",
        "isjamchart",
        "jamchart_notes",
        "soundcheck",
        "isverified",
        "isrecommended",
    ]
    return setlist_data[setlist_columns], transition_data

logs_dir = os.path.join(project_root, "logs", "Goose")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "goose_pipeline.log")
logger = get_logger(__name__, log_file=log_file, add_console_handler=True)


def load_song_data() -> "pd.DataFrame":
    """
    Load and process Goose song data from API and website scrape.

    Returns:
        pd.DataFrame: DataFrame containing merged song data.
    """
    song_table_idx = 1
    songdata_api = pd.DataFrame(make_api_request("songs", "v2")["data"]).drop(
        columns=["slug", "created_at", "updated_at"], errors="ignore"
    )
    response = requests.get("https://elgoose.net/song/", timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    tables = pd.read_html(StringIO(str(soup.find_all("table"))))
    if not tables or len(tables) <= song_table_idx:
        logger.error(
            "Expected table at index %d not found in Goose song page.", song_table_idx
        )
        return pd.DataFrame()
    songdata_scrape = (
        tables[song_table_idx].sort_values(by="Song Name").reset_index(drop=True)
    )
    merged_data = songdata_api.merge(
        songdata_scrape, left_on="name", right_on="Song Name", how="inner"
    )
    columns = [
        "id",
        "Song Name",
        "isoriginal",
        "Original Artist",
        "Debut Date",
        "Last Played",
        "Times Played Live",
        "Avg Show Gap",
    ]
    merged_data = merged_data[columns].copy()
    final_columns = {
        "id": "song_id",
        "Song Name": "song",
        "isoriginal": "is_original",
        "Original Artist": "original_artist",
        "Debut Date": "debut_date",
        "Last Played": "last_played",
        "Times Played Live": "times_played",
        "Avg Show Gap": "avg_show_gap",
    }
    return merged_data.rename(columns=final_columns)


def load_show_data() -> tuple["pd.DataFrame", "pd.DataFrame", "pd.DataFrame"]:
    """
    Load and process Goose show, venue, and tour data.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        Tuple of DataFrames for show data, venue data, and tour data.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    shows = pd.DataFrame(make_api_request("shows", "v2")["data"])
    past_shows = shows[shows["showdate"] < today]
    future_shows = shows[shows["showdate"] >= today].sort_values("showdate").head(1)
    all_shows = pd.concat([past_shows, future_shows])
    all_shows = (
        all_shows[(all_shows["artist"] == "Goose")].copy().reset_index(drop=True)
    )
    venue_data = (
        all_shows[["venue_id", "venuename", "city", "state", "country", "location"]]
        .drop_duplicates()
        .sort_values("venue_id")
        .reset_index(drop=True)
        .rename(columns={"venue": "venue_name"})
    )
    tour_data = (
        all_shows[["tour_id", "tourname"]]
        .drop_duplicates()
        .sort_values("tour_id")
        .reset_index(drop=True)
    )
    show_data = (
        all_shows[["show_id", "showdate", "venue_id", "tour_id", "showorder"]]
        .sort_values("showdate")
        .reset_index(names="show_number")
        .rename(columns={"showdate": "show_date", "showorder": "show_order"})
        .assign(show_number=lambda x: x["show_number"] + 1)
    )
    show_data["tour_id"] = show_data["tour_id"].astype("Int64").astype(str)
    return show_data, venue_data, tour_data


def load_setlist_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load and process Goose setlist and transition data.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Tuple of DataFrames for setlist data and transition data.
    """
    setlist_df = pd.DataFrame(make_api_request("setlists", "v1")["data"])
    transition_data = (
        setlist_df[["transition_id", "transition"]]
        .drop_duplicates()
        .sort_values(by=["transition_id"])
    )
    setlist_data = (
        setlist_df[setlist_df["artist"] == "Goose"].copy().reset_index(drop=True)
    )

    # Clean boolean columns to handle invalid data from the API
    boolean_columns = [
        "isreprise",
        "isjam",
        "isjamchart",
        "soundcheck",
        "isverified",
        "isrecommended",
    ]
    for col in boolean_columns:
        if col in setlist_data.columns:
            # Convert to boolean, coercing errors to NaT, then fill NaNs with False
            setlist_data[col] = pd.to_numeric(setlist_data[col], errors='coerce').fillna(0).astype(bool)

    # Clean integer columns to handle invalid data from the API
    integer_columns = ["show_id", "song_id", "setnumber", "position", "transition_id"]
    for col in integer_columns:
        if col in setlist_data.columns:
            setlist_data[col] = pd.to_numeric(setlist_data[col], errors='coerce').fillna(0).astype(int)
    setlist_columns = [
        "uniqueid",
        "show_id",
        "song_id",
        "setnumber",
        "position",
        "tracktime",
        "transition_id",
        "isreprise",
        "isjam",
        "footnote",
        "isjamchart",
        "jamchart_notes",
        "soundcheck",
        "isverified",
        "isrecommended",
    ]
    return setlist_data[setlist_columns], transition_data


def load_nextshow_data(show_id: int) -> json:
    """_summary_

    Returns:
        json: _description_
    """
    return make_api_request(f"shows/{show_id}", "v2")["data"][
        ["showdate", "venue_name", "city", "state", "country", ""]
    ]


def load_goose_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Main orchestration function to load all Goose data from API.
    This function coordinates the loading of all data types needed for prediction models:
    - Song data (with debut dates, play counts, etc.)
    - Show data (dates, venues, etc.)
    - Venue data (locations, names, etc.)
    - Setlist data (songs played in each show)
    - Transition data (how songs connect)
    - Next show info (upcoming show details)
    Returns:
        tuple: (song_data, show_data, venue_data, setlist_data, transition_data, next_show_info)
    """
    logger.info("Loading Goose data from API...")
    # Load all data types
    logger.info("Loading song data...")
    song_data = load_song_data()
    logger.info("Loading show, venue, and tour data...")
    show_data, venue_data, _ = load_show_data()  # We don't need tour_data for predictions
    logger.info("Loading setlist and transition data...")
    setlist_data, transition_data = load_setlist_data()
    logger.info("Loaded %s transitions from API", len(transition_data))
    logger.info("Getting next show info...")
    next_show_info = get_next_show_info(show_data, logger=logger)
    logger.info("✅ Successfully loaded all Goose data from API")
    logger.info("Loaded: %s songs, %s shows, %s venues, %s setlist entries", len(song_data), len(show_data), len(venue_data), len(setlist_data))
    return song_data, show_data, venue_data, setlist_data, transition_data, next_show_info
