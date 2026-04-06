"""Data collector for Widespread Panic from everydaycompanion.com."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from ...db.connection import get_supabase_client
from ..base import BandCollector
from ..config import get_collector_config
from ..setlist_reviewer import review_setlist
from .parser import _validate_song_name, parse_setlist_from_text
from .parser_profile import DEFAULT_PROFILE, fingerprint_page, validate_fingerprint
from .session import (
    IS_GITHUB_ACTIONS,
    cleanup_playwright,
    create_enhanced_session,
    decode_ec_response,
    make_request,
    make_simple_request,
)
from .status import CollectionStatus

logger = logging.getLogger(__name__)


class WSPCollector(BandCollector):
    """Collects WSP data by scraping everydaycompanion.com with enhanced session management."""

    ARTIST_NAME = "Widespread Panic"
    BASE_URL = "https://www.everydaycompanion.com"

    def __init__(self, status: Optional[CollectionStatus] = None):
        config = get_collector_config("wsp")

        super().__init__(config)

        self.supabase_client = get_supabase_client()

        # Enhanced session with proper headers and retry logic

        self.session = create_enhanced_session()

        # Status tracking for error handling and exit code determination
        self.status = status if status is not None else CollectionStatus()

        logger.info("Initialized WSPCollector")

    def _scrape_single_setlist(self, show_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrapes the setlist for a single show, skipping if it already exists."""

        show_url = show_info.get("source_url")
        show_id = show_info.get("show_id")

        if not show_url or not show_id:
            return []

        # More efficient: check for existing setlist before making any web requests
        try:
            response = (
                self.supabase_client.table("wsp_setlists_raw")
                .select("show_id")
                .eq("show_id", show_id)
                .limit(1)
                .execute()
            )
            if response.data:
                logger.info(
                    f"Setlist for show_id {show_id} already exists. Skipping scrape."
                )
                return []
        except Exception as e:
            logger.warning(
                f"Could not check for existing setlist for show_id {show_id}: {e}"
            )

        try:
            response = make_request(self.session, show_url, allow_redirects=True)
            final_url = response.url
            if final_url != show_url:
                logger.debug(f"URL redirected: {show_url} -> {final_url}")

            soup = BeautifulSoup(decode_ec_response(response), "html.parser")
            setlist_data = parse_setlist_from_text(soup, show_id)
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 403:
                self.status.record_403_error(show_url)
                logger.warning(
                    f"403 Forbidden for {show_url}. Skipping EC scrape for this show. "
                    f"(Total 403s: {self.status.http_403_errors})"
                )
                return []  # Skip this show, TourWrangler fallback will handle it
            else:
                self.status.record_http_error(
                    show_url, e.response.status_code if e.response else 0
                )
                logger.error(
                    f"HTTP {e.response.status_code if e.response else 'unknown'} error for {show_url}: {e}"
                )
                return (
                    []
                )  # Don't raise, return empty to continue processing other shows
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to scrape setlist for {show_url}: {e}")
            return []  # Don't raise, return empty to continue processing other shows

        # Continue with normal parsing if no exception
        try:
            if setlist_data:
                valid_songs = [
                    s for s in setlist_data if _validate_song_name(s["song_name"])
                ]
                if len(valid_songs) < len(setlist_data):
                    logger.warning(
                        f"Filtered {len(setlist_data) - len(valid_songs)} contaminated songs from {show_url}"
                    )
                return valid_songs

            logger.debug(f"Text parsing failed for {show_url}, trying table parsing")
            tables = soup.find_all("table")
            if len(tables) < DEFAULT_PROFILE.song_table_min_tables:
                return []

            fp = fingerprint_page(soup, DEFAULT_PROFILE)
            warnings = validate_fingerprint(fp, DEFAULT_PROFILE)
            if warnings:
                logger.warning(
                    "WSP DOM fingerprint mismatch for %s: %s",
                    show_url,
                    "; ".join(warnings),
                )

            setlist_table = None
            lo, hi = DEFAULT_PROFILE.setlist_table_range
            for table in tables[lo:hi]:
                table_text = table.get_text()
                if (
                    any(m in table_text for m in DEFAULT_PROFILE.setlist_set_markers)
                ) and not any(
                    m in table_text for m in DEFAULT_PROFILE.setlist_noise_markers
                ):
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
                if not _validate_song_name(song_name):
                    continue

                if song_name.startswith("Set "):
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
            logger.error(f"Failed to parse setlist table for {show_url}: {e}")
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
            logger.info("No date range specified, collecting all historical shows")

        iterable = tqdm(
            years_to_scrape, desc=f"Collecting {self.ARTIST_NAME} shows", unit="year"
        )

        for year_2d in iterable:
            year_str = f"{year_2d:02d}"
            url = f"{self.BASE_URL}/asp/tour{year_str}.asp"
            try:
                # Use simple request for tour pages (no rate limiting needed for index pages)
                response = make_simple_request(self.session, url)
                soup = BeautifulSoup(decode_ec_response(response), "html.parser")

                # Define a filter function to find the correct table
                def find_show_table(tag):
                    if tag.name != "table":
                        return False
                    return tag.find(
                        "a",
                        href=lambda href: href
                        and (
                            DEFAULT_PROFILE.tour_link_extension in href
                            and any(
                                p in href
                                for p in DEFAULT_PROFILE.tour_link_href_patterns
                            )
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
                        DEFAULT_PROFILE.tour_link_extension in href
                        and any(
                            p in href for p in DEFAULT_PROFILE.tour_link_href_patterns
                        )
                    ),
                )

                for link in setlist_links:
                    try:
                        link_text = link.get_text().strip()
                        if not link_text:
                            continue

                        parts = link_text.split(" ", 1)
                        if len(parts) < 2:
                            continue

                        date_part = parts[0]

                        venue_location_part = parts[1]

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

            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    logger.info(
                        f"No tour page found for year {year_str} (404), skipping."
                    )
                elif e.response and e.response.status_code == 403:
                    self.status.record_403_error(f"tour page {url}")
                    logger.warning(
                        f"403 Forbidden for {url}. Skipping year {year_str}. "
                        f"(Total 403s: {self.status.http_403_errors})"
                    )
                else:
                    status_code = e.response.status_code if e.response else "unknown"
                    self.status.record_http_error(f"tour page {url}", status_code)
                    logger.error(f"Failed to fetch or parse year {year_str}: {e}")
            except requests.RequestException as e:
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
        if IS_GITHUB_ACTIONS:
            logger.info(
                "Running sequential setlist collection for CI (Playwright compatibility)"
            )
            iterable = tqdm(
                shows_to_process,
                desc=f"Collecting {self.ARTIST_NAME} setlists (Sequential)",
            )
            for show in iterable:
                try:
                    setlist_data = self._scrape_single_setlist(show)
                    if setlist_data:
                        all_setlists.extend(setlist_data)
                except Exception as exc:
                    show_url = show.get("source_url", "unknown URL")
                    logger.warning(f"Unexpected exception scraping {show_url}: {exc}")
        else:
            # Reduced to 1 worker to avoid rate limiting and bot detection
            with ThreadPoolExecutor(max_workers=1) as executor:
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
                        show_url = future_to_show[future].get(
                            "source_url", "unknown URL"
                        )
                        # This should rarely trigger now that _scrape_single_setlist handles errors internally
                        logger.warning(
                            f"Unexpected exception scraping {show_url}: {exc}"
                        )

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

            if len(tables) < DEFAULT_PROFILE.song_table_min_tables:
                logger.error("Could not find the song table on the page.")
                return []

            songs_df = pd.read_html(
                StringIO(str(tables[DEFAULT_PROFILE.song_table_index]))
            )[0]
            songs_df.columns = list(DEFAULT_PROFILE.song_table_columns)
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

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 403:
                self.status.record_403_error(f"songs page {url}")
                logger.warning(
                    f"403 Forbidden for {url}. Proceeding without song data. "
                    f"(Total 403s: {self.status.http_403_errors})"
                )
                return []
            else:
                status_code = e.response.status_code if e.response else "unknown"
                self.status.record_http_error(f"songs page {url}", status_code)
                logger.error(f"HTTP {status_code} error scraping songs from {url}: {e}")
                return []
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
        """Cleanup session and Playwright browser on deletion."""
        if hasattr(self, "session"):
            self.session.close()
        # Clean up Playwright browser if it was used (in GitHub Actions)
        cleanup_playwright()
