"""
Consolidated WSP data loaders for scraping from everydaycompanion.com.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from jambandnerd.db.supabase_client import create_supabase_client
from tqdm import tqdm

supabase = create_supabase_client()


def scrape_wsp_songs(
    logger: logging.Logger, base_url: str = "http://www.everydaycompanion.com/"
) -> pd.DataFrame:
    """
    Scrape and return the WSP song catalog from everydaycompanion.com.
    """
    songcode_url = f"{base_url}asp/songcode.asp"
    try:
        response = requests.get(songcode_url, timeout=15)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all("table")
    except Exception as e:
        logger.exception("Error fetching song codes: %s", e)
        return pd.DataFrame()

    song_table_idx = 4
    if not tables or len(tables) <= song_table_idx:
        logger.error(
            "Expected song catalog table at index %s not found in song codes page.",
            song_table_idx,
        )
        return pd.DataFrame()

    song_table_html = str(tables[song_table_idx])
    try:
        song_codes = pd.read_html(StringIO(song_table_html))[0]
    except Exception as e:
        logger.error("Failed to parse song catalog table: %s", e)
        return pd.DataFrame()

    song_codes.columns = [
        "code",
        "song",
        "first_played",
        "last_played",
        "times_played",
        "aka",
    ]
    song_codes = song_codes.dropna(subset=["code", "song"]).reset_index(drop=True)
    song_codes["times_played"] = (
        pd.to_numeric(song_codes["times_played"], errors="coerce").fillna(0).astype(int)
    )

    for col in ["first_played", "last_played"]:
        song_codes[col] = song_codes[col].replace("First", None)
        song_codes[col] = pd.to_datetime(song_codes[col], errors="coerce")
        song_codes[col] = song_codes[col].dt.strftime("%m/%d/%Y")

    return song_codes


def scrape_wsp_shows(
    logger: logging.Logger,
    base_url: str = "http://www.everydaycompanion.com/",
    start_year: int = 1985,
    years: list = None,
) -> pd.DataFrame:
    """
    Scrape and return show data for all years from everydaycompanion.com.
    """
    if years is None:
        years = []
    today = date.today()
    this_year = today.year
    tour_list = [x for x in range(start_year, this_year + 1) if x not in years]
    tour_df_list = []
    for yr in tour_list:
        yr_str = str(yr)[-2:]
        year_link = f"{base_url}asp/tour{yr_str}.asp"
        try:
            response = requests.get(year_link, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            p_tag = soup.find("p")
            if p_tag is None:
                logger.warning("No <p> tag found for year %s.", yr)
                continue
            tour_string = p_tag.get_text()
        except Exception as e:
            logger.error("Error fetching/parsing year %s: %s", yr, e)
            continue

        tour_string = re.sub(r"\?\?", "00", tour_string)
        venues = [
            v.strip() for v in re.split(r"\d{2}/\d{2}/\d{2}", tour_string) if v.strip()
        ]
        dates = re.findall(r"\d{2}/\d{2}/\d{2}", tour_string)
        tour_data = pd.DataFrame({"date": dates, "venue": venues})

        tour_data["link_date"] = tour_data["date"].str.replace("/", "", regex=False)
        tour_data["link_date"] = tour_data["link_date"].apply(lambda x: x[4:] + x[:4])
        tour_data["link"] = base_url + "setlists/" + tour_data["link_date"] + ".asp"
        tour_data = tour_data.drop(columns=["link_date"])

        tour_data["date"] = pd.to_datetime(tour_data["date"], errors="coerce")
        tour_data["date"] = tour_data["date"].dt.strftime("%m/%d/%Y")

        if tour_data.empty:
            continue
        tour_df_list.append(tour_data)

    if not tour_df_list:
        return pd.DataFrame()

    return pd.concat(tour_df_list, ignore_index=True)


def process_raw_setlist(setlist_raw: pd.DataFrame, link: str) -> pd.DataFrame:
    """
    Process raw setlist data and assign proper column names matching Supabase schema.
    """
    if setlist_raw.empty:
        return pd.DataFrame()

    # Assign proper column names based on the expected structure
    # The raw HTML table typically has columns: song, notes, etc.
    expected_columns = (
        ["song_name", "song_note_detail"]
        if setlist_raw.shape[1] >= 2
        else ["song_name"]
    )

    # Pad with additional columns if needed
    while len(expected_columns) < setlist_raw.shape[1]:
        expected_columns.append(f"col_{len(expected_columns)}")

    setlist_raw.columns = expected_columns[: setlist_raw.shape[1]]

    # Add required columns matching Supabase schema
    setlist_raw["link"] = link
    setlist_raw["song_index_show"] = range(1, len(setlist_raw) + 1)
    setlist_raw["set_name"] = "Set 1"  # Default set name, can be enhanced later
    setlist_raw["song_index_set"] = range(
        1, len(setlist_raw) + 1
    )  # Default to same as show index
    setlist_raw["is_into"] = False  # Default to False, can be enhanced later

    # Clean up the data
    setlist_raw = setlist_raw.dropna(subset=["song_name"]).reset_index(drop=True)

    # Recalculate indices after cleaning
    setlist_raw["song_index_show"] = range(1, len(setlist_raw) + 1)
    setlist_raw["song_index_set"] = range(1, len(setlist_raw) + 1)

    return setlist_raw


def get_setlist_from_link(link: str, logger: logging.Logger) -> pd.DataFrame:
    """
    Scrape setlist data from a single link with retry logic.
    """
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(link, timeout=15)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")
            tables = soup.find_all("table")

            if not tables or len(tables) <= 4:
                return pd.DataFrame()

            setlist_raw = pd.read_html(StringIO(str(tables[4])))[0]
            return process_raw_setlist(setlist_raw, link)
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1 * (2**attempt))
                continue
            else:
                logger.error(
                    "Failed to fetch %s after %d retries: %s", link, retries, e
                )
                return pd.DataFrame()
    return pd.DataFrame()


def _link_exists_in_supabase(link: str, logger: logging.Logger) -> bool:
    """Lightweight existence check for a setlist link in Supabase."""
    try:
        # Limit to a single row to minimize payload
        resp = (
            supabase.table("wsp_setlists")
            .select("link")
            .eq("link", link)
            .limit(1)
            .execute()
        )
        return bool(resp.data)
    except Exception as e:
        logger.exception("Error checking existence for link %s: %s", link, e)
        # On error, default to assuming it does exist to avoid unnecessary scraping
        return True


def load_setlist_data(
    shows: pd.DataFrame, logger: logging.Logger, update: bool = False, scrape: bool = True
) -> pd.DataFrame:
    """
    Load WSP setlist data from everydaycompanion.com.
    """
    if not scrape:
        return pd.DataFrame({"link": shows["link"].tolist()})

    links_to_scrape = shows["link"].tolist()
    if update:
        # Lightweight per-link existence check in parallel to minimize payload from Supabase
        filtered_links = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_map = {
                executor.submit(_link_exists_in_supabase, link_url, logger): link_url
                for link_url in links_to_scrape
            }
            for future in tqdm(
                future_map,
                total=len(links_to_scrape),
                desc="Checking existing setlists",
            ):
                exists = future.result()
                link_val = future_map[future]
                if not exists:
                    filtered_links.append(link_val)
        links_to_scrape = filtered_links

    if not links_to_scrape:
        return pd.DataFrame()

    setlist_frames = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(get_setlist_from_link, link, logger): link
            for link in links_to_scrape
        }
        for future in tqdm(
            futures, total=len(links_to_scrape), desc="Scraping Setlists"
        ):
            setlist = future.result()
            if not setlist.empty:
                setlist_frames.append(setlist)

    if not setlist_frames:
        return pd.DataFrame()

    new_setlists = pd.concat(setlist_frames, ignore_index=True)
    return new_setlists.dropna(subset=["song_name"]).reset_index(drop=True)
