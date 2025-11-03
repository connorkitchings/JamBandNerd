"""Data collector for Widespread Panic from everydaycompanion.com."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from ...db.connection import get_supabase_client
from ..base import BandCollector
from ..config import get_collector_config

from ..setlist_reviewer import review_setlist

from .parser import parse_setlist_from_text, _validate_song_name
from .session import create_enhanced_session, make_request

logger = logging.getLogger(__name__)


class WSPCollector(BandCollector):
    """Collects WSP data by scraping everydaycompanion.com with enhanced session management."""

    ARTIST_NAME = "Widespread Panic"
    BASE_URL = "http://www.everydaycompanion.com"

    def __init__(self):
        config = get_collector_config("wsp")

        super().__init__(config)

        self.supabase_client = get_supabase_client()

        # Enhanced session with proper headers and retry logic

        self.session = create_enhanced_session()

        logger.info(f"Initialized WSPCollector")

    def _scrape_single_setlist(self, show_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrapes the setlist for a single show with improved parsing and rate limiting."""

        show_url = show_info.get("source_url")

        show_id = show_info.get("show_id")

        if not show_url or not show_id:
            return []

        try:
            # Use enhanced request method with rate limiting

            response = make_request(self.session, show_url, allow_redirects=True)

            # Update show_info with final URL if redirected

            final_url = response.url

            if final_url != show_url:
                logger.debug(f"URL redirected: {show_url} -> {final_url}")

            soup = BeautifulSoup(response.content, "html.parser")

            # Try the new text-based parsing first

            setlist_data = parse_setlist_from_text(soup, show_id)

            if setlist_data:
                # Validate the parsed data quality

                valid_songs = [
                    s for s in setlist_data if _validate_song_name(s["song_name"])
                ]

                contaminated_count = len(setlist_data) - len(valid_songs)

                if contaminated_count > 0:
                    logger.warning(
                        f"Filtered {contaminated_count} contaminated songs from {show_url}"
                    )

                if valid_songs:
                    return valid_songs

                else:
                    logger.warning(
                        f"All songs filtered as contaminated for {show_url}, trying fallback parsing"
                    )

            # Fallback to old table-based parsing if text parsing fails

            logger.debug(f"Text parsing failed for {show_url}, trying table parsing")

            tables = soup.find_all("table")

            if len(tables) < 5:
                return []

            # Look for the right table (one that contains setlist, not stats)

            setlist_table = None

            for i, table in enumerate(tables[4:8]):  # Check tables 4-7
                table_text = table.get_text()

                # Include Set 0 (soundcheck) in detection

                if (
                    "0:" in table_text or "1:" in table_text or "2:" in table_text
                ) and "Song Stats" not in table_text:
                    # Prioritize shorter tables (less likely to be contaminated with stats)

                    if not setlist_table or len(table_text) < len(
                        setlist_table.get_text()
                    ):
                        setlist_table = table

            if not setlist_table:
                logger.warning(f"Could not find setlist table for {show_url}")

                return []

            setlist_df = pd.read_html(StringIO(str(setlist_table)))[0]

            if setlist_df.empty:
                return []

            setlist_df.columns = (
                ["song_name", "song_note_detail"]
                if setlist_df.shape[1] > 1
                else ["song_name"]
            )

            setlist_df.dropna(subset=["song_name"], inplace=True)

            setlist_data = []

            current_set = "1"

            song_position = 1

            for _, row in setlist_df.iterrows():
                song_name = row["song_name"]

                # Skip invalid song names

                if not _validate_song_name(song_name):
                    continue

                if song_name.startswith("Set "):  # Detects Set 2, Set 3, etc.
                    current_set = song_name.split(" ")[1]

                    song_position = 1

                    continue

                if song_name.startswith("Encore"):
                    current_set = "E"

                    song_position = 1

                    continue

                is_segue = song_name.endswith(">")

                if is_segue:
                    song_name = song_name[:-1].strip()

                # Strip note indicators

                song_name = song_name.rstrip("*").strip()

                setlist_data.append(
                    {
                        "show_id": show_id,
                        "set_number": current_set,
                        "song_position": song_position,
                        "song_name": song_name,
                        "is_segue": is_segue,
                        "song_notes": row.get("song_note_detail", ""),
                    }
                )

                song_position += 1

            return setlist_data

        except Exception as e:
            logger.error(f"Failed to scrape setlist for {show_url}: {e}")

            return []

    def collect_shows(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Collects show data by scraping the tour pages (tourYY.asp) with rate limiting."""
        shows = []
        current_year_2_digit = datetime.now().year % 100

        # Honor date parameters if provided
        if start_date and end_date:
            start_year_2d = start_date.year % 100
            end_year_2d = end_date.year % 100

            # Handle century crossing (e.g., 1999 to 2001)
            if start_date.year < 2000 <= end_date.year:
                years_to_scrape = list(range(start_year_2d, 100)) + list(
                    range(0, end_year_2d + 1)
                )
            elif start_date.year >= 2000 and end_date.year >= 2000:
                years_to_scrape = list(range(start_year_2d, end_year_2d + 1))
            else:
                years_to_scrape = list(range(start_year_2d, end_year_2d + 1))

            logger.info(
                f"Collecting shows for years: {start_date.year}-{end_date.year} (2-digit: {years_to_scrape})"
            )
        else:
            # Default: scan all historical years
            years_to_scrape = list(range(86, 100)) + list(
                range(0, current_year_2_digit + 1)
            )
            logger.info(f"No date range specified, collecting all historical shows")

        iterable = tqdm(
            years_to_scrape, desc=f"Collecting {self.ARTIST_NAME} shows", unit="year"
        )

        for year_2d in iterable:
            year_str = f"{year_2d:02d}"
            url = f"{self.BASE_URL}/asp/tour{year_str}.asp"
            try:
                # Use enhanced request method with rate limiting
                response = make_request(self.session, url)
                soup = BeautifulSoup(response.content, "html.parser")

                # Define a filter function to find the correct table
                def find_show_table(tag):
                    if tag.name != "table":
                        return False
                    # A valid show table should contain at least one link to a setlist page
                    # Handle both absolute and relative paths (../setlists/file.asp or setlist.asp)
                    return tag.find(
                        "a",
                        href=lambda href: href
                        and (
                            ".asp" in href
                            and ("setlist" in href or "/setlists/" in href)
                        ),
                    )

                target_table = soup.find(find_show_table)

                if not target_table:
                    logger.warning(f"No show table found for year {year_str} at {url}")
                    continue

                # Extract show data directly from setlist links instead of parsing table rows
                # The links contain all the information we need in their text
                setlist_links = target_table.find_all(
                    "a",
                    href=lambda href: href
                    and (
                        ".asp" in href and ("setlist" in href or "/setlists/" in href)
                    ),
                )

                for link in setlist_links:
                    try:
                        # Parse link text format: "01/18/24 Stifel Theatre, St. Louis, MO"
                        link_text = link.get_text().strip()
                        if not link_text:
                            continue

                        # Extract date (first part before space)
                        parts = link_text.split(" ", 1)
                        if len(parts) < 2:
                            continue

                        date_part = parts[0]  # "01/18/24"
                        venue_location_part = parts[
                            1
                        ]  # "Stifel Theatre, St. Louis, MO"

                        # Parse date - convert 2-digit year to 4-digit
                        try:
                            # Split date into components
                            month_day_year = date_part.split("/")
                            if len(month_day_year) != 3:
                                continue

                            month, day, year_2digit = month_day_year

                            # Convert 2-digit year to 4-digit
                            year_2digit_int = int(year_2digit)
                            if year_2digit_int >= 80:  # 80-99 -> 1980-1999
                                full_year = f"19{year_2digit}"
                            else:  # 00-79 -> 2000-2079
                                full_year = f"20{year_2digit}"

                            show_date = datetime.strptime(
                                f"{month}/{day}/{full_year}", "%m/%d/%Y"
                            ).date()
                        except (ValueError, IndexError) as date_error:
                            logger.debug(
                                f"Skipping link due to date parse error: {link_text} | Error: {date_error}"
                            )
                            continue

                        # Parse venue and location
                        # Format: "Venue Name, City, State" or "Venue Name, City State"
                        venue_parts = [
                            part.strip() for part in venue_location_part.split(",")
                        ]

                        if len(venue_parts) >= 3:
                            venue_name = venue_parts[0]
                            city = venue_parts[1]
                            state = venue_parts[2]
                        elif len(venue_parts) == 2:
                            venue_name = venue_parts[0]
                            city_state = venue_parts[1].strip()
                            # Try to split "City State" format
                            city_state_parts = city_state.rsplit(
                                " ", 1
                            )  # Split from right to handle multi-word cities
                            if len(city_state_parts) == 2:
                                city, state = city_state_parts
                            else:
                                city = city_state
                                state = ""
                        else:
                            venue_name = venue_location_part
                            city = ""
                            state = ""

                        # Handle relative vs absolute URLs
                        href = link["href"]
                        if href.startswith("../"):
                            # Relative path like ../setlists/20240118a.asp
                            show_url = f"{self.BASE_URL}/{href[3:]}"  # Remove ../ and prepend base URL
                        elif href.startswith("setlist"):
                            # Absolute path within asp directory
                            show_url = f"{self.BASE_URL}/asp/{href}"
                        else:
                            # Assume it needs asp directory
                            show_url = f"{self.BASE_URL}/asp/{href}"

                        shows.append(
                            {
                                "show_date": show_date.isoformat(),
                                "venue_name": venue_name.strip(),
                                "city": city.strip(),
                                "state": state.strip(),
                                "source_url": show_url,
                            }
                        )

                    except Exception as parse_error:
                        logger.debug(
                            f"Skipping link due to parse error in year {year_str}: {link_text} | Error: {parse_error}"
                        )
                        continue

            except requests.RequestException as e:
                if (
                    hasattr(e, "response")
                    and e.response
                    and e.response.status_code == 404
                ):
                    logger.info(
                        f"No tour page found for year {year_str} (404), skipping."
                    )
                else:
                    logger.error(f"Failed to fetch or parse year {year_str}: {e}")

        logger.info(f"✅ {self.ARTIST_NAME}: Collected {len(shows)} show URLs.")
        return shows

    def collect_setlists(
        self, shows_to_process: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Collect setlists with rate limiting enforced."""
        if not shows_to_process:
            logger.info("No new shows to process for setlists.")
            return []

        all_setlists = []
        # Reduced max_workers to be more respectful to the server
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_show = {
                executor.submit(self._scrape_single_setlist, show): show
                for show in shows_to_process
            }
            iterable = tqdm(
                future_to_show,
                total=len(shows_to_process),
                desc=f"Collecting {self.ARTIST_NAME} setlists",
            )
            for future in iterable:
                try:
                    setlist_data = future.result()
                    if setlist_data:
                        all_setlists.extend(setlist_data)
                except Exception as exc:
                    show_url = future_to_show[future].get("source_url", "unknown URL")
                    logger.error(f"Scraping {show_url} generated an exception: {exc}")

        # Review and clean the setlist data before returning
        all_setlists = review_setlist(all_setlists)

        logger.info(
            f"✅ {self.ARTIST_NAME}: Collected {len(all_setlists)} total setlist records."
        )
        return all_setlists

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects song data by scraping the song catalog page with rate limiting."""
        url = f"{self.BASE_URL}/asp/songcode.asp"
        logger.info(f"Scraping songs from {url}")
        try:
            # Use enhanced request method with rate limiting
            response = make_request(self.session, url)
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")

            if len(tables) < 5:
                logger.error("Could not find the song table on the page.")
                return []

            songs_df = pd.read_html(StringIO(str(tables[4])))[0]
            songs_df.columns = [
                "code",
                "song_name",
                "first_played",
                "last_played",
                "times_played",
                "aka",
            ]
            songs_df.dropna(subset=["code", "song_name"], inplace=True)

            # Clean and format data
            songs_df["times_played"] = (
                pd.to_numeric(songs_df["times_played"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
            for col in ["first_played", "last_played"]:
                songs_df[col] = pd.to_datetime(
                    songs_df[col], format="%m/%d/%y", errors="coerce"
                ).dt.date

            logger.info(f"✅ {self.ARTIST_NAME}: Scraped {len(songs_df)} songs.")
            # Explicit type conversion to satisfy type checker
            return [dict(row) for row in songs_df.to_dict("records")]  # type: ignore[misc]

        except Exception as e:
            logger.error(f"Failed to scrape songs: {e}")
            return []

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collects venue data by scraping."""
        logger.warning(
            "%s: Venue collection is not separately implemented. "
            "Venues are collected as part of shows.",
            self.ARTIST_NAME,
        )
        return []

    def __del__(self):
        """Cleanup session on deletion."""
        if hasattr(self, "session"):
            self.session.close()
