"""
Scrape WSP setlist data from everydaycompanion.com. Standalone after refactor.
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from jambandnerd.db.supabase_client import create_supabase_client

from .utils import get_logger

logger = get_logger(__name__)

supabase = create_supabase_client()

# --- Constants ---
SETLIST_TABLE_IDX = 4

COMMA_SONGS = [
    "Guns",
    "And Money",
    "Let Me Follow You Down",
    "Let Me Hold Your Hand",
    "Please Don't Go",
    "Rattle",
    "And Roll",
    "Narrow Mind",
    "Woman Smarter",
]
COMMA_SONGS_COMPLETER = {
    "Lawyers": "Lawyers Guns And Money",
    "Baby": "One of the 3 Baby Songs",
    "Shake": "Shake, Rattle, And Roll",
    "Weak Brain": "Weak Brain, Narrow Mind",
    "Man Smart": "Man Smart, Woman Smarter",
}


EXPECTED_COLUMNS = [
    "song_name",
    "set_name",
    "song_index_set",
    "song_index_show",
    "is_into",
    "song_note_detail",
    "link",
]


def get_setlist_from_link(link):
    """
    Scrape setlist data from a single link with retry logic.

    Args:
        link (str): Link to scrape setlist data from.

    Returns:
        pd.DataFrame: Setlist data for the given link.
    """
    retries = 3
    backoff_factor = 1.0  # Start with 1 second

    for attempt in range(retries):
        try:
            # Increase timeout to 20 seconds
            response = requests.get(link, timeout=20)
            response.raise_for_status()  # Raise an exception for bad status codes

            # If successful, proceed with parsing
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")
            tables = soup.find_all("table")

            if not tables or len(tables) <= SETLIST_TABLE_IDX:
                logger.error("Not enough tables found for link %s. Skipping.", link)
                return pd.DataFrame(columns=EXPECTED_COLUMNS)

            tables_str = str(tables)
            tables_io = StringIO(tables_str)
            setlist_tables = pd.read_html(tables_io)
            setlist_raw = setlist_tables[SETLIST_TABLE_IDX].copy()
            break  # Exit loop on success

        except requests.exceptions.RequestException as e:
            logger.warning(
                "Request for %s failed (attempt %d/%d): %s.",
                link,
                attempt + 1,
                retries,
                e,
            )
            if attempt < retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                logger.info("Retrying in %.1f seconds...", sleep_time)
                time.sleep(sleep_time)
            else:
                logger.error("All %d retry attempts failed for %s.", retries, link)
                return pd.DataFrame(columns=EXPECTED_COLUMNS)
        except Exception as e:
            logger.exception("An unexpected error occurred while processing %s: %s", link, e)
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
    try:
        if setlist_raw.empty or 0 not in setlist_raw.columns:
            logger.warning(
                "Setlist table at %s is empty or missing expected columns. Skipping.", link
            )
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
        setlist_raw["Raw"] = setlist_raw[0].astype(str).str.replace("ï", "i")
        # Identify set/encore markers, otherwise mark as 'Other' for now
        setlist_raw["set_name"] = setlist_raw["Raw"].apply(
            lambda x: x[:3]
            if x[:2] in (["0:", "1:", "2:", "3:", "4:", "E:", "E1", "E2", "E3", "E4"])
            else "Other"
        )
        # Re-classify specific 'Other' rows as 'Details' if they match certain patterns
        setlist_raw["set_name"] = setlist_raw.apply(
            lambda row: "Details"
            if row["set_name"] == "Other"
            and (row["Raw"].startswith("??") or re.match(r"^\d{2}/", row["Raw"]))
            else row["set_name"],
            axis=1,
        )
        setlist_raw["set_name"] = setlist_raw["set_name"].str.strip()
        setlist_raw["Raw"] = setlist_raw["Raw"].str.lstrip()
        setlist_raw["Raw"] = np.where(
            setlist_raw["set_name"].isin(["0", "1", "2", "3", "4", "E"]),
            setlist_raw["Raw"].str.replace("^.{3}", "", regex=True),
            setlist_raw["Raw"],
        )

        songs1 = setlist_raw[~setlist_raw["set_name"].isin(["Details", "Notes"])].copy()
        songs1["Raw"] = songs1["Raw"].str.replace(">", ",>", regex=False)
        songs1["Raw"] = songs1["Raw"].str.split(",")
        songs2 = songs1.explode("Raw").copy()
        songs2["is_into"] = songs2["Raw"].apply(lambda x: 1 if ">" in x else 0)
        songs2["Raw"] = songs2["Raw"].str.replace(">", "", regex=False)
        songs2["Raw"] = songs2["Raw"].str.lstrip()
        songs2["Raw"] = songs2["Raw"].replace("|".join(songs2["set_name"]), "", regex=True)
        songs3 = songs2[~songs2["Raw"].str.contains("|".join(COMMA_SONGS))].copy()
        songs3["Raw"] = songs3["Raw"].map(COMMA_SONGS_COMPLETER).fillna(songs3["Raw"])
        songs3["song_name"] = songs3["Raw"].str.capitalize().str.strip()
        songs3["notes_id"] = songs3["song_name"].str.count(r"\*")
        songs3["song_notes_key"] = np.where(
            songs3["notes_id"] == 0, "", songs3["notes_id"].apply(lambda x: "*" * x)
        )
        songs4 = songs3.reset_index(drop=True).copy()
        songs4["song_index_show"] = songs4.index + 1
    except Exception as e:
        logger.error("Failed to parse DataFrame for link %s: %s", link, e)
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    songs4["song_index_set"] = songs4.groupby("set_name").cumcount() + 1
    songs4["link"] = str(link)

    # Notes processing: True notes are marked with '*' and were not classified as set entries
    notes = setlist_raw[
        (setlist_raw["set_name"] == "Other") & (setlist_raw["Raw"].str.contains(r"\*"))
    ].copy()
    notes["notes_id"] = notes["Raw"].str.count(r"\*")
    notes["song_notes_key"] = np.where(
        notes["notes_id"] == 0, "", notes["notes_id"].apply(lambda x: "*" * x)
    )
    notes["song_note_detail"] = (
        notes["Raw"].str.replace(r"\*", "", regex=True).str.strip()
    )
    notes = notes[["song_notes_key", "song_note_detail"]]

    # Aggregate notes with the same key and merge
    if not notes.empty:
        # Group by the key and join the note details into a single string
        notes_agg = (
            notes.groupby("song_notes_key")["song_note_detail"]
            .apply("; ".join)
            .reset_index()
        )
        songs_with_notes = pd.merge(
            songs4, notes_agg, on="song_notes_key", how="left"
        )
        final_df = songs_with_notes.copy()
    else:
        # If there are no notes, create the column with empty strings
        songs4["song_note_detail"] = ""
        final_df = songs4.copy()

    # Final column selection and cleaning
    final_df = final_df[
        [
            "song_name",
            "set_name",
            "song_index_set",
            "song_index_show",
            "is_into",
            "song_note_detail",
            "link",
        ]
    ].copy()

    # Drop rows with empty song names that might have been created during parsing
    final_df = final_df[final_df["song_name"] != ""].reset_index(drop=True)

    # Recalculate song_index_show after cleaning to ensure it's sequential
    final_df["song_index_show"] = final_df.index + 1

    return final_df


def load_setlist_data(
    shows: pd.DataFrame, update: bool = False, scrape: bool = True
) -> pd.DataFrame:
    """Load WSP setlist data from everydaycompanion.com.

    If update is True, it queries Supabase for the latest show date and scrapes a
    three-year window (YYYY-1, YYYY, YYYY+1) around that date. Otherwise, it
    performs a full scrape of all shows.

    Args:
        shows: DataFrame of WSP shows, including a 'link' column.
        update: If True, performs an intelligent update based on the latest data
                in Supabase. Defaults to False.
        scrape: If True, actually scrapes the data. If False, returns dry-run info.
                Defaults to True.

    Returns:
        DataFrame of WSP setlist data.
    """
    links_to_scrape: list[str] = []

    if update:
        try:
            supabase = create_supabase_client()
            logger.info("Checking for existing setlists in Supabase...")

            # First, get the total count
            response = (
                supabase.table("wsp_setlists")
                .select("*", count="exact")
                .limit(1)
                .execute()
            )
            total_count = response.count
            logger.info("Total rows in wsp_setlists: %d", total_count)

            # Use a conservative page size that Supabase definitely supports
            page_size = 1000
            offset = 0
            all_rows = []

            while offset < total_count:
                try:
                    response = (
                        supabase.table("wsp_setlists")
                        .select("link")  # Only select the link column we need
                        .range(offset, offset + page_size - 1)
                        .execute()
                    )
                    data = response.data

                    if not data:
                        logger.warning(
                            "No data returned at offset %d, but expected more rows",
                            offset,
                        )
                        break

                    all_rows.extend(data)
                    offset += len(
                        data
                    )  # Increment by actual rows received, not page_size
                    logger.info(
                        "Fetched %d rows so far (offset now %d)...",
                        len(all_rows),
                        offset,
                    )

                    # If we got fewer rows than expected, we've reached the end
                    if len(data) < page_size:
                        logger.info(
                            "Received fewer rows than page size, assuming end of data"
                        )
                        break

                except Exception as e:
                    logger.error("Error fetching batch at offset %d: %s", offset, e)
                    # You might want to retry or break here depending on your needs
                    break

            logger.info(
                "Successfully fetched %d total rows from Supabase", len(all_rows)
            )

            if len(all_rows) != total_count:
                logger.warning(
                    "Mismatch: fetched %d rows but expected %d. Some data may be missing.",
                    len(all_rows),
                    total_count,
                )

            all_setlists = pd.DataFrame(all_rows)

            if all_setlists.empty:
                logger.warning("No existing setlists found in Supabase")
                existing_links = set()
            else:
                existing_links = set(all_setlists["link"].tolist())
                logger.info(
                    "Found %d unique existing links in Supabase.", len(existing_links)
                )

            all_show_links = set(shows["link"].tolist())
            logger.info("Total show links available: %d", len(all_show_links))

            new_links = list(all_show_links - existing_links)

            if not new_links:
                logger.info(
                    "All shows already have setlists in Supabase. Nothing to scrape."
                )
                links_to_scrape = []
            else:
                logger.info(
                    "Found %d new shows that need setlists scraped.", len(new_links)
                )
                # Log a few examples for debugging
                logger.info("Sample new links: %s", new_links[:5])
                links_to_scrape = new_links

        except Exception as e:
            logger.exception(
                "Error querying Supabase for existing setlists: %s. Falling back to full scrape.",
                e,
            )
            links_to_scrape = shows["link"].tolist()
    else:
        logger.info(
            "Performing a full initial scrape of all WSP setlists as 'update' is False."
        )
        links_to_scrape = shows["link"].tolist()

    if not links_to_scrape:
        logger.info("No new show links to scrape.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    logger.info("Found %d show links that would be scraped.", len(links_to_scrape))
    if not scrape:
        # Dry-run mode: return DataFrame listing links that would be scraped
        return pd.DataFrame({"link": links_to_scrape})

    logger.info("Scraping setlists for real…")
    setlist_frames = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(get_setlist_from_link, link): link
            for link in links_to_scrape
        }
        for future in tqdm(
            futures, total=len(links_to_scrape), desc="Scraping Setlists"
        ):
            setlist = future.result()
            if setlist is not None and not setlist.empty:
                setlist_frames.append(setlist)

    if not setlist_frames:
        logger.warning("No new setlist data was scraped from the links.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    new_setlists = pd.concat(setlist_frames, ignore_index=True)
    return new_setlists.dropna(subset=["song_name"]).reset_index(drop=True)
