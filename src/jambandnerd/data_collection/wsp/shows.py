"""Module for collecting WSP show data."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Union

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from .session import make_request

logger = logging.getLogger(__name__)


def collect_shows(
    session: requests.Session,
    base_url: str,
    start_date: Union[datetime.date, None] = None,
    end_date: Union[datetime.date, None] = None,
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
        years_to_scrape, desc="Collecting Widespread Panic shows", unit="year"
    )

    for year_2d in iterable:
        year_str = f"{year_2d:02d}"
        url = f"{base_url}/asp/tour{year_str}.asp"
        try:
            # Use enhanced request method with rate limiting
            response = make_request(session, url)
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
                        show_url = f"{base_url}/{href[3:]}"  # Remove ../ and prepend base URL
                    elif href.startswith("setlist"):
                        # Absolute path within asp directory
                        show_url = f"{base_url}/asp/{href}"
                    else:
                        # Assume it needs asp directory
                        show_url = f"{base_url}/asp/{href}"

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

    logger.info(f"✅ Widespread Panic: Collected {len(shows)} show URLs.")
    return shows
