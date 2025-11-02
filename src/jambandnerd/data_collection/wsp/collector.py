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
        self.session = self._create_enhanced_session()

        # Rate limiting
        self.rate_limit_delay = 1.5  # 1.5 seconds between requests
        self.last_request_time = 0

        logger.info(
            f"Initialized WSPCollector with rate limit: {self.rate_limit_delay}s between requests"
        )

    def _create_enhanced_session(self) -> requests.Session:
        """Create a requests session with browser-like headers and retry logic."""
        session = requests.Session()

        # Comprehensive browser-like headers to avoid 403 Forbidden
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "DNT": "1",
                "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
            }
        )

        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=10, pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with rate limiting and error handling."""
        self._enforce_rate_limit()

        try:
            logger.debug(f"Fetching: {url}")
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e: # Catch base RequestException
            if isinstance(e, requests.exceptions.HTTPError) and e.response and e.response.status_code == 403:
                logger.error(
                    f"403 Forbidden for {url} - site may be blocking scrapers despite headers"
                )
            elif isinstance(e, requests.exceptions.ConnectionError):
                logger.error(f"Connection error for {url}: {e}")
            # Add other specific exception handling if needed
            raise # Re-raise the original exception

    def _get_existing_show_urls(self) -> List[str]:
        """Fetches all source_urls from the wsp_shows_raw table."""
        try:
            response = (
                self.supabase_client.table("wsp_shows_raw")
                .select("source_url")
                .execute()
            )
            return [
                item["source_url"] for item in response.data if item.get("source_url")
            ]
        except Exception as e:
            logger.error(f"Could not fetch existing show URLs from Supabase: {e}")
            return []

    def _validate_song_name(self, song_name: str) -> bool:
        """Validate that this looks like a real song name, not statistics or metadata."""
        if not song_name or len(song_name.strip()) == 0:
            return False

        # Skip very long entries (likely statistics) - tightened threshold
        if len(song_name) > 80:
            logger.debug(
                f"Rejecting long song name (>{len(song_name)} chars): {song_name[:50]}..."
            )
            return False

        # Enhanced statistics detection - more comprehensive patterns
        stats_indicators = [
            "Song Stats",
            "LTP Date",
            "L3TP",
            "#/10",
            "#/100",
            "#/Ever",
            "StatsSong",
            "Last Time Played",
            "Average of last",
            "LTPL3TP",
            "DateLTP",
            "LTP (Last Time Played)",
            "Number of shows since",
            "Number of times played",
            "Total number of times",
            "Average of last 3",
            # Common contamination patterns from actual data
            "ALONE 12/31/23",
            "BEAR 03/24/24",
            "APLANE 03/22/24",
        ]

        for indicator in stats_indicators:
            if indicator in song_name:
                logger.debug(f"Rejecting statistics entry: {song_name[:50]}...")
                return False

        # Reject entries that look like show headers or metadata
        if song_name.startswith(
            (
                "01/",
                "02/",
                "03/",
                "04/",
                "05/",
                "06/",
                "07/",
                "08/",
                "09/",
                "10/",
                "11/",
                "12/",
            )
        ):
            if "Hard Rock Hotel" in song_name or "Casino" in song_name:
                logger.debug(f"Rejecting show header: {song_name[:50]}...")
                return False

        # Reject entries with too many numbers/codes (likely statistics)
        import re

        if len(re.findall(r"\b\d+\b", song_name)) > 5:
            logger.debug(f"Rejecting numeric data: {song_name[:50]}...")
            return False

        return True

    def _parse_setlist_from_text(
        self, soup: BeautifulSoup, show_id: str
    ) -> List[Dict[str, Any]]:
        """Parse setlist directly from text content, looking for 0:, 1:, 2:, E: patterns."""
        setlist_data = []

        # Get all text and look for setlist lines
        page_text = soup.get_text()
        lines = page_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for set indicators: "0:" (soundcheck), "1:", "2:", "E:", etc.
            if ":" in line and (
                line.startswith("0:")
                or line.startswith("1:")
                or line.startswith("2:")
                or line.startswith("3:")
                or line.startswith("E:")
                or line.startswith("Encore")
            ):
                # Extract set number
                if line.startswith("E:") or line.startswith("Encore"):
                    set_number = "E"
                    songs_part = (
                        line[2:].strip() if line.startswith("E:") else line[6:].strip()
                    )
                elif line.startswith("0:"):
                    set_number = "0"  # Soundcheck
                    songs_part = line[2:].strip()
                else:
                    set_number = line[0]
                    songs_part = line[2:].strip()

                # Parse individual songs
                # Split by comma first, then handle segues (>)
                song_parts = songs_part.split(",")

                song_position = 1
                for song_part in song_parts:
                    song_part = song_part.strip()
                    if not song_part:
                        continue

                    # Handle segues within a song part (e.g., "Song A > Song B")
                    if ">" in song_part:
                        segued_songs = song_part.split(">")
                        for i, segued_song in enumerate(segued_songs):
                            segued_song = segued_song.strip().rstrip("*").strip()
                            if segued_song and self._validate_song_name(segued_song):
                                setlist_data.append(
                                    {
                                        "show_id": show_id,
                                        "set_number": set_number,
                                        "song_position": song_position,
                                        "song_name": segued_song,
                                        "is_segue": i
                                        < len(segued_songs)
                                        - 1,  # All but last are segues
                                        "song_notes": "",
                                    }
                                )
                                song_position += 1
                    else:
                        # Regular song
                        song_name = song_part.rstrip("*").strip()
                        if self._validate_song_name(song_name):
                            setlist_data.append(
                                {
                                    "show_id": show_id,
                                    "set_number": set_number,
                                    "song_position": song_position,
                                    "song_name": song_name,
                                    "is_segue": False,
                                    "song_notes": "",
                                }
                            )
                            song_position += 1

        return setlist_data

    def _scrape_single_setlist(self, show_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrapes the setlist for a single show with improved parsing and rate limiting."""
        show_url = show_info.get("source_url")
        show_id = show_info.get("show_id")
        if not show_url or not show_id:
            return []

        try:
            # Use enhanced request method with rate limiting
            response = self._make_request(show_url, allow_redirects=True)

            # Update show_info with final URL if redirected
            final_url = response.url
            if final_url != show_url:
                logger.debug(f"URL redirected: {show_url} -> {final_url}")

            soup = BeautifulSoup(response.content, "html.parser")

            # Try the new text-based parsing first
            setlist_data = self._parse_setlist_from_text(soup, show_id)

            if setlist_data:
                # Validate the parsed data quality
                valid_songs = [
                    s for s in setlist_data if self._validate_song_name(s["song_name"])
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
                if not self._validate_song_name(song_name):
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
                response = self._make_request(url)
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
            response = self._make_request(url)
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
