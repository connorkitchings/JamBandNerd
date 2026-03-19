"""Billy Strings data collector (bmfsdb.com scraper)."""

from __future__ import annotations

import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup
from requests import RequestException
from tqdm import tqdm

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)


class BillyCollector(BandCollector):
    """Collect Billy Strings shows and setlists from bmfsdb.com."""

    ARTIST_NAME = "Billy Strings"
    BASE_URL = "https://bmfsdb.com"
    LISTING_PATH = "/setlists"
    UPCOMING_PATH = "/setlists?view=upcoming"
    MAX_PAGES = 400  # Safety guard against infinite pagination

    def __init__(self) -> None:
        config = get_collector_config("billy")
        super().__init__(config)
        logger.info(
            "Initialized BillyCollector with rate limit: %s/%ss",
            config.rate_limit_calls,
            config.rate_limit_window,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def _fetch_and_parse_show_page(self, page: int) -> List[Dict[str, Any]]:
        """Fetches and parses a single page of show listings."""
        url = f"{self.BASE_URL}{self.LISTING_PATH}?page={page}"
        logger.debug("Fetching Billy Strings show listing page %s", url)
        page_shows = []

        try:
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code == 404:
                return []  # Stop this page
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch show listing page %s: %s", page, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        show_links = soup.select("a.link-unstyled")
        if not show_links:
            return []

        for link in show_links:
            parsed = self._parse_show_card(link)
            if not parsed:
                continue

            show_date, venue_data = parsed
            show_uuid = self._extract_show_uuid(link)

            page_shows.append(
                {
                    "source_uuid": show_uuid,
                    "show_date": show_date.isoformat(),
                    **venue_data,
                    "source_url": f"{self.BASE_URL}/setlist/{show_uuid}",
                }
            )
        return page_shows

    def collect_shows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Scrape show listings from the bmfsdb setlists index with pagination awareness."""
        all_shows: List[Dict[str, Any]] = []
        start_date = start_date or date(1900, 1, 1)
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        consecutive_empty = 0
        pages_fetched = 0

        iterator = range(1, self.MAX_PAGES + 1)
        try:
            iterator = tqdm(iterator, desc="Scraping Billy Strings show pages")
        except Exception:  # pragma: no cover - tqdm optional
            pass

        for page in iterator:
            page_shows = self._fetch_and_parse_show_page(page)
            if not page_shows:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    break
                continue

            # Stop once the newest show on a page is already older than the requested window.
            newest_date = datetime.fromisoformat(page_shows[0]["show_date"]).date()
            if start_date and newest_date < start_date:
                break

            all_shows.extend(page_shows)
            pages_fetched += 1
            consecutive_empty = 0

        # Filter and deduplicate
        unique_shows = {}
        for show in all_shows:
            # Use a tuple of (uuid, date) as key to handle potential duplicate UUIDs with different dates
            show_uuid = show.get("source_uuid")
            show_date = show.get("show_date")
            if show_uuid and show_date:
                if (show_uuid, show_date) not in unique_shows:
                    unique_shows[(show_uuid, show_date)] = show

        filtered_shows = []
        for show in unique_shows.values():
            show_dt = datetime.fromisoformat(show["show_date"]).date()
            if start_date <= show_dt and (not end_date or show_dt <= end_date):
                filtered_shows.append(show)

        logger.info(
            "✅ %s: Collected %s shows across %s page(s).",
            self.ARTIST_NAME,
            len(filtered_shows),
            pages_fetched or max(len(filtered_shows) // 10, 1),
        )

        # Collect and add upcoming shows
        upcoming_cutoff = date.today()
        upcoming_shows = self._collect_upcoming_shows(
            min_date=end_date or start_date or upcoming_cutoff
        )

        # Add upcoming shows, avoiding duplicates
        seen_uuids = {s["source_uuid"] for s in filtered_shows}
        for show in upcoming_shows:
            if show.get("source_uuid") not in seen_uuids:
                filtered_shows.append(show)
                if show.get("source_uuid"):
                    seen_uuids.add(show["source_uuid"])

        logger.info(
            "✅ %s: Total shows including upcoming: %s",
            self.ARTIST_NAME,
            len(filtered_shows),
        )
        return sorted(filtered_shows, key=lambda s: s["show_date"], reverse=True)

    def collect_setlists(
        self, shows_to_process: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Scrape setlist entries for the provided shows."""

        if not shows_to_process:
            logger.info("No Billy Strings shows supplied for setlist scraping.")
            return []

        def _submit_args(
            show: Dict[str, Any],
        ) -> Tuple[str, str, Optional[str], Optional[str]]:
            show_id = str(show.get("show_id"))
            source_url = show.get("source_url") or ""
            uuid = show.get("source_uuid")
            show_date = show.get("show_date")
            if not source_url and uuid:
                source_url = f"{self.BASE_URL}/setlist/{uuid}"
            return show_id, source_url, uuid, show_date

        results: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for record in shows_to_process:
                show_id, source_url, uuid, show_date = _submit_args(record)
                if not show_id or not source_url:
                    continue
                futures[
                    executor.submit(
                        self._scrape_show_setlist, show_id, source_url, uuid, show_date
                    )
                ] = (
                    show_id,
                    source_url,
                    show_date,
                )

            iterable: Iterable = futures
            try:
                iterable = tqdm(
                    futures,
                    total=len(futures),
                    desc=f"Collecting {self.ARTIST_NAME} setlists",
                )
            except Exception:  # pragma: no cover - tqdm optional
                pass

            for future in iterable:
                try:
                    data = future.result()
                    if data:
                        results.extend(data)
                except Exception as exc:  # pragma: no cover - defensive logging
                    show_id, source_url, _ = futures[future]
                    logger.error(
                        "Error scraping setlist for show_id=%s (%s): %s",
                        show_id,
                        source_url,
                        exc,
                    )

        logger.info("✅ %s: Collected %s setlist rows.", self.ARTIST_NAME, len(results))
        return results

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Scrape the Billy Strings song catalog from bmfsdb.com."""

        params = {"showAll": "1", "perPage": "2000"}
        url = f"{self.BASE_URL}/songs/"
        logger.info("Fetching Billy Strings song catalog from %s", url)

        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch Billy Strings songs: %s", exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        component = self._find_livewire_component(soup, "songs-index")
        if component is None:
            logger.error("Could not locate songs table component on bmfsdb.com")
            return []

        rows = component.select("table.table-hover tbody tr")
        if not rows:
            logger.warning("No Billy Strings songs found in songs table.")
            return []

        catalog: List[Dict[str, Any]] = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            title_cell, artist_cell, plays_cell, teases_cell, first_cell, last_cell = (
                cells[:6]
            )

            song_link = title_cell.find("a")
            song_name = (song_link or title_cell).get_text(strip=True)
            if not song_name:
                continue

            original_artist_link = artist_cell.find("a")
            original_artist_text = (original_artist_link or artist_cell).get_text(
                strip=True
            )
            original_artist = original_artist_text or None
            if original_artist:
                original_artist = (
                    None
                    if original_artist.upper() in {"N/A", "--"}
                    else original_artist
                )

            catalog.append(
                {
                    "song_uuid": (
                        self._extract_song_uuid(song_link) if song_link else None
                    ),
                    "song_name": song_name,
                    "original_artist": original_artist,
                    "original_artist_id": self._extract_artist_id(original_artist_link),
                    "times_played": self._parse_int_cell(plays_cell),
                    "times_teased": self._parse_int_cell(teases_cell),
                    "first_played": self._parse_song_date(first_cell),
                    "last_played": self._parse_song_date(last_cell),
                    "source_url": song_link.get("href") if song_link else None,
                }
            )

        logger.info("✅ %s: Collected %s songs.", self.ARTIST_NAME, len(catalog))
        return catalog

    def collect_venues(self) -> List[Dict[str, Any]]:  # pragma: no cover - placeholder
        logger.info(
            "%s: Venue collection not implemented; venues derived from shows.",
            self.ARTIST_NAME,
        )
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_show_uuid(self, link: Any) -> Optional[str]:
        href = link.get("href")
        if not href:
            return None
        parts = href.rstrip("/").split("/")
        token = parts[-1] if parts else None
        if not token:
            return None
        token = token.split("?")[0]
        return self._ensure_uuid(token)

    def _parse_show_card(self, link: Any) -> Optional[Tuple[date, Dict[str, Any]]]:
        badge = link.select_one("div.badge")
        venue_block = link.select_one("div.col-8") or link.select_one(
            "div.col-8.col-md-9"
        )

        if not badge or not venue_block:
            return None

        spans = badge.find_all("span")
        if len(spans) < 3:
            return None

        month_day = spans[0].get_text(strip=True)
        year_text = spans[2].get_text(strip=True)

        show_date = self._parse_show_date(month_day, year_text)
        if not show_date:
            return None

        venue_lines = list(venue_block.stripped_strings)
        if not venue_lines:
            return None

        venue_name = venue_lines[0]
        location_text = venue_lines[1] if len(venue_lines) > 1 else ""
        city, state, country = self._parse_location(location_text)

        return show_date, {
            "venue_name": venue_name,
            "venue_city": city,
            "venue_state": state,
            "venue_country": country,
        }

    def _parse_show_date(self, month_day: str, year_text: str) -> Optional[date]:
        cleaned_day = re.sub(r"[^0-9A-Za-z ]", "", month_day).strip()
        for fmt in ("%b %d %Y", "%B %d %Y"):
            try:
                return datetime.strptime(f"{cleaned_day} {year_text}", fmt).date()
            except ValueError:
                continue
        logger.debug("Could not parse show date from '%s %s'", month_day, year_text)
        return None

    def _parse_location(self, location: str) -> Tuple[str, str, str]:
        if not location:
            return "", "", ""

        parts = [part.strip() for part in location.split(",") if part.strip()]
        if not parts:
            return location.strip(), "", ""

        if len(parts) == 1:
            return parts[0], "", ""

        if len(parts) == 2:
            city, second = parts
            if len(second) == 2 and second.isalpha():
                return city, second.upper(), "USA"
            return city, "", second

        city = ", ".join(parts[:-2])
        state = parts[-2]
        country = parts[-1]
        return city, state, country

    def _collect_upcoming_shows(self, min_date: date) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(
                f"{self.BASE_URL}/setlists",
                params={"view": "upcoming"},
                timeout=self.config.timeout,
            )
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch upcoming shows: %s", exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        upcoming: List[Dict[str, Any]] = []
        for link in soup.select("a.link-unstyled"):
            badge = link.select_one("div.badge")
            spans = badge.find_all("span") if badge else []
            if len(spans) < 3:
                continue
            month_day = spans[0].get_text(strip=True)
            year_text = spans[2].get_text(strip=True)
            show_date = self._parse_show_date(month_day, year_text)
            if not show_date or show_date < min_date:
                continue

            venue_block = link.select_one("div.col-8") or link.select_one(
                "div.col-8.col-md-9"
            )
            venue_lines = list(venue_block.stripped_strings) if venue_block else []
            venue_name = venue_lines[0] if venue_lines else ""
            location_text = venue_lines[1] if len(venue_lines) > 1 else ""
            city, state, country = self._parse_location(location_text)

            href = link.get("href") or ""
            source_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            source_uuid = self._extract_show_uuid(link)

            upcoming.append(
                {
                    "source_uuid": source_uuid,
                    "show_date": show_date.isoformat(),
                    "venue_name": venue_name,
                    "venue_city": city,
                    "venue_state": state,
                    "venue_country": country,
                    "source_url": source_url,
                }
            )

        logger.info(
            "✅ %s: Collected %s upcoming shows.", self.ARTIST_NAME, len(upcoming)
        )
        return upcoming

    def _scrape_show_setlist(
        self,
        show_id: str,
        source_url: str,
        uuid: Optional[str],
        show_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(source_url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error(
                "Failed to fetch setlist for show_id=%s (%s): %s",
                show_id,
                source_url,
                exc,
            )
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        panel = soup.select_one("#shows-panel")
        if not panel:
            logger.warning(
                "No setlist panel found for show_id=%s (%s)", show_id, source_url
            )
            return []

        entries: List[Dict[str, Any]] = []
        current_set_number: Optional[int] = None
        per_set_position = 0
        show_position = 0

        for child in panel.children:
            if not hasattr(child, "get"):
                continue
            classes = child.get("class", [])
            if "alert" in classes and "alert-info" in classes:
                label_text = child.get_text(strip=True).rstrip(":")
                current_set_number = self._decode_set_label(label_text)
                per_set_position = 0
                continue

            if "song-stripe" not in classes or current_set_number is None:
                continue

            per_set_position += 1
            show_position += 1

            row = child.select_one("div.row.mb-2")
            if not row:
                continue

            song_anchor = row.find("a")
            if not song_anchor:
                continue

            song_name = song_anchor.get_text(strip=True)
            song_uuid = self._extract_song_uuid(song_anchor)

            notes_section = row.select_one("div.col-11.col-md-2")
            song_notes = (
                notes_section.get_text(" ", strip=True) if notes_section else ""
            )

            entries.append(
                {
                    "show_id": show_id,
                    "source_uuid": uuid,
                    "song_uuid": song_uuid,
                    "set_number": current_set_number,
                    "song_position": per_set_position,
                    "song_name": song_name,
                    "is_segue": False,
                    "encore": current_set_number >= 90,
                    "song_notes": song_notes,
                }
            )
        if not entries:
            parsed_date = None
            if show_date:
                try:
                    parsed_date = datetime.fromisoformat(show_date).date()
                except ValueError:
                    parsed_date = None
            if not parsed_date or parsed_date < date.today():
                logger.warning(
                    "No setlist rows parsed for show_id=%s (%s)", show_id, source_url
                )
        return entries

    def _extract_song_notes(self, stripe: Any, primary_text: str) -> str:
        notes_container = stripe.select_one("div.col-10.col-md-6")
        if not notes_container:
            return ""

        notes: List[str] = []
        for anchor in notes_container.select("a"):
            text = anchor.get_text(strip=True)
            if text and text != primary_text:
                notes.append(text)

        if not notes:
            return ""

        return ", ".join(dict.fromkeys(notes))  # Preserve order, remove duplicates

    def _extract_song_uuid(self, anchor: Any) -> Optional[str]:
        href = anchor.get("href")
        if not href or "/song/" not in href:
            return None
        after = href.split("/song/")[-1]
        return after.split("?")[0]

    def _ensure_uuid(self, value: str) -> str:
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            normalized = value.strip()
            if not normalized:
                normalized = "unknown"
            generated = uuid.uuid5(
                uuid.NAMESPACE_URL, f"{self.BASE_URL}/setlist/{normalized}"
            )
            return str(generated)

    def _extract_artist_id(self, anchor: Any) -> Optional[str]:
        if not anchor:
            return None
        href = anchor.get("href")
        if not href or "/artist/" not in href:
            return None
        return href.rstrip("/").split("/")[-1] or None

    def _find_livewire_component(self, soup: Any, component_name: str) -> Optional[Any]:
        for candidate in soup.select("div[wire\\:id]"):
            snapshot = candidate.get("wire:snapshot") or ""
            if component_name in snapshot:
                return candidate
        return None

    def _parse_int_cell(self, cell: Any) -> int:
        text = (cell.get_text(strip=True) if cell else "").replace(",", "")
        if not text or text.upper() in {"N/A", "--"}:
            return 0
        try:
            return int(text)
        except (TypeError, ValueError):
            return 0

    def _parse_song_date(self, cell: Any) -> Optional[str]:
        text = (cell.get_text(strip=True) if cell else "").strip()
        if not text or text.upper() in {"N/A", "--"}:
            return None
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d").date()
            return parsed.isoformat()
        except ValueError:
            return None

    def _decode_set_label(self, label: str) -> int:
        normalized = label.strip().lower()
        if "soundcheck" in normalized:
            return 0
        if "encore" in normalized:
            # Encore 1, Encore 2 => 90 + index, default 99
            match = re.search(r"(\d+)", normalized)
            if match:
                return 90 + int(match.group(1))
            return 99
        match = re.search(r"(\d+)", normalized)
        if match:
            return int(match.group(1))
        return 1
        if match:
            return int(match.group(1))
        return 1
