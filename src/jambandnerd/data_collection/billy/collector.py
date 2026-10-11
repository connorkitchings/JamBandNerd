"""Billy Strings data collector (billybase.net scraper)."""

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
    """Collect Billy Strings shows and setlists from billybase.net."""

    ARTIST_NAME = "Billy Strings"
    BASE_URL = "https://billybase.net"
    LISTING_PATH = "/past-shows/"
    UPCOMING_PATH = "/upcoming-shows/"
    SITEMAP_PATH = "/wp-sitemap-posts-show-1.xml"
    SONGS_SITEMAP_PATH = "/wp-sitemap-posts-song-1.xml"
    MAX_BACKWALK = 500  # Safety guard when following Prev show links

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
    def collect_shows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Scrape show listings from billybase.net.

        Uses the server-rendered ``/past-shows/`` page plus the ``< Prev``
        navigation on individual show pages to walk backwards through history.
        Upcoming shows are collected from ``/upcoming-shows/``.
        """
        start_date = start_date or date(1900, 1, 1)
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        all_shows: List[Dict[str, Any]] = []

        # Recent completed shows from the listing page + chronological walk.
        past_shows = self._collect_past_shows(start_date)
        all_shows.extend(past_shows)

        # Future shows from the dedicated upcoming page.
        upcoming_cutoff = end_date or start_date or date.today()
        upcoming_shows = self._collect_upcoming_shows(min_date=upcoming_cutoff)
        all_shows.extend(upcoming_shows)

        # Deduplicate and filter to the requested window.
        unique_shows: Dict[str, Dict[str, Any]] = {}
        for show in all_shows:
            show_uuid = show.get("source_uuid")
            show_dt = show.get("show_date")
            if not show_uuid or not show_dt:
                continue
            if show_uuid in unique_shows:
                continue
            parsed_dt = datetime.fromisoformat(show_dt).date()
            if parsed_dt < start_date:
                continue
            if end_date and parsed_dt > end_date:
                continue
            unique_shows[show_uuid] = show

        filtered_shows = sorted(
            unique_shows.values(), key=lambda s: s["show_date"], reverse=True
        )

        logger.info(
            "✅ %s: Collected %s shows across the requested window.",
            self.ARTIST_NAME,
            len(filtered_shows),
        )
        return filtered_shows

    def collect_setlists(  # type: ignore[override]
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
            show_uuid = show.get("source_uuid")
            show_date = show.get("show_date")
            return show_id, source_url, show_uuid, show_date

        results: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for record in shows_to_process:
                show_id, source_url, show_uuid, show_date = _submit_args(record)
                if not show_id or not source_url:
                    continue
                futures[
                    executor.submit(
                        self._scrape_show_setlist,
                        show_id,
                        source_url,
                        show_uuid,
                        show_date,
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
        """Return an empty song catalog for now.

        billybase.net exposes song pages with rich metadata, but the full catalog
        (~1,000 songs) requires scraping each individual song page. The existing
        ``billy_songs_raw`` rows remain valid for ``is_cover`` lookups, so we
        defer a full backfill to a later optimization.
        """
        logger.info(
            "%s: Song catalog collection deferred; relying on existing "
            "billy_songs_raw rows for cover metadata.",
            self.ARTIST_NAME,
        )
        return []

    def collect_venues(self) -> List[Dict[str, Any]]:  # pragma: no cover - placeholder
        logger.info(
            "%s: Venue collection not implemented; venues derived from shows.",
            self.ARTIST_NAME,
        )
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fetch_soup(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[BeautifulSoup]:
        """Fetch a URL and return a BeautifulSoup object."""
        self.rate_limiter.wait_if_needed()
        try:
            self.rate_limiter.record_call()
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            self.record_success()
            return BeautifulSoup(response.text, "html.parser")
        except RequestException as exc:
            self.record_failure()
            logger.error("Failed to fetch %s: %s", url, exc)
            return None

    def _collect_past_shows(self, start_date: date) -> List[Dict[str, Any]]:
        """Collect recent completed shows from /past-shows/ and walk backwards."""
        url = f"{self.BASE_URL}{self.LISTING_PATH}"
        soup = self._fetch_soup(url)
        if soup is None:
            return []

        shows: List[Dict[str, Any]] = []
        seen_slugs: set[str] = set()

        # Parse the server-rendered first page of cards.
        for card in soup.find_all("article", class_="ecs-post-loop"):
            show = self._parse_show_card(card)
            if not show:
                continue
            slug = self._extract_slug_from_url(show["source_url"])
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            shows.append(show)

        if not shows:
            logger.warning("No past show cards found on %s", url)
            return shows

        # If the oldest card on the first page is still newer than the window,
        # walk backward through individual show pages using the Prev link.
        oldest_show = min(shows, key=lambda s: s["show_date"])
        oldest_date = datetime.fromisoformat(oldest_show["show_date"]).date()

        if oldest_date > start_date:
            prev_url = oldest_show["source_url"]
            for _ in range(self.MAX_BACKWALK):
                prev_soup = self._fetch_soup(prev_url)
                if prev_soup is None:
                    break
                prev_show = self._parse_show_page(prev_soup)
                if not prev_show:
                    break
                slug = self._extract_slug_from_url(prev_show["source_url"])
                if not slug or slug in seen_slugs:
                    break
                seen_slugs.add(slug)
                shows.append(prev_show)

                prev_date = datetime.fromisoformat(prev_show["show_date"]).date()
                if prev_date <= start_date:
                    break

                next_prev = self._find_prev_show_url(prev_soup)
                if not next_prev:
                    break
                prev_url = next_prev

        logger.info(
            "✅ %s: Collected %s past shows.",
            self.ARTIST_NAME,
            len(shows),
        )
        return shows

    def _collect_upcoming_shows(self, min_date: date) -> List[Dict[str, Any]]:
        """Collect upcoming shows from /upcoming-shows/."""
        url = f"{self.BASE_URL}{self.UPCOMING_PATH}"
        soup = self._fetch_soup(url)
        if soup is None:
            return []

        upcoming: List[Dict[str, Any]] = []
        for card in soup.find_all("article", class_="ecs-post-loop"):
            show = self._parse_show_card(card)
            if not show:
                continue
            show_dt = datetime.fromisoformat(show["show_date"]).date()
            if show_dt < min_date:
                continue
            upcoming.append(show)

        logger.info(
            "✅ %s: Collected %s upcoming shows.",
            self.ARTIST_NAME,
            len(upcoming),
        )
        return upcoming

    def _parse_show_card(self, card: Any) -> Optional[Dict[str, Any]]:
        """Parse a show card from /past-shows/ or /upcoming-shows/."""
        show_link: Optional[str] = None
        venue_text: Optional[str] = None
        show_date: Optional[str] = None

        for anchor in card.find_all("a", href=True):
            href = anchor.get("href") or ""
            if "/show/" not in href:
                continue
            if show_link is None:
                show_link = href

            text = anchor.get_text(strip=True)
            if not text:
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                show_date = text
            elif "–" in text or "-" in text:
                venue_text = text

        if not show_link or not show_date or not venue_text:
            return None

        # venue_text: "Venue Name – City, ST" (uses en-dash)
        split_char = "–" if "–" in venue_text else "-"
        parts = [p.strip() for p in venue_text.split(split_char, 1)]
        if len(parts) != 2:
            return None

        venue_name, location_text = parts
        city, state, country = self._parse_location(location_text)
        source_url = (
            show_link if show_link.startswith("http") else f"{self.BASE_URL}{show_link}"
        )
        slug = self._extract_slug_from_url(source_url)
        if not slug:
            return None

        return {
            "source_uuid": self._ensure_uuid(slug),
            "show_date": show_date,
            "venue_name": venue_name,
            "venue_city": city,
            "venue_state": state,
            "venue_country": country,
            "source_url": source_url,
        }

    def _parse_show_page(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse SHOW INFO from an individual show page."""
        info = self._extract_show_info(soup)
        if not info:
            return None

        show_date = info.get("SHOW DATE")
        venue_name = info.get("SHOW VENUE")
        city = info.get("CITY", "")
        state_country = info.get("STATE / COUNTRY", "")

        if not show_date or not venue_name:
            return None

        # Build a location string so _parse_location can split it consistently.
        location_parts = [p for p in (city, state_country) if p]
        _, state, country = self._parse_location(
            ", ".join(location_parts) if len(location_parts) > 1 else state_country
        )

        source_url = info.get("source_url", "")
        if not source_url:
            return None

        slug = self._extract_slug_from_url(source_url)
        if not slug:
            return None

        return {
            "source_uuid": self._ensure_uuid(slug),
            "show_date": show_date,
            "venue_name": venue_name,
            "venue_city": city,
            "venue_state": state,
            "venue_country": country,
            "source_url": source_url,
        }

    def _extract_show_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract SHOW INFO label/value pairs from a show page."""
        info: Dict[str, str] = {}
        show_info_heading = None
        for heading in soup.find_all("h2"):
            if heading.get_text(strip=True) == "SHOW INFO":
                show_info_heading = heading
                break

        if not show_info_heading:
            return info

        section = show_info_heading.find_parent("section")
        if not section:
            return info

        text = section.get_text("\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        labels = {"SHOW DATE", "SHOW VENUE", "TOUR", "CITY", "STATE / COUNTRY"}

        for i, line in enumerate(lines):
            if line in labels and i + 1 < len(lines):
                info[line] = str(lines[i + 1])

        # Capture canonical URL so callers do not need to reconstruct the slug.
        canonical = soup.find("link", rel="canonical")
        if canonical:
            href = canonical.get("href")
            info["source_url"] = str(href) if href else ""

        return info

    def _find_prev_show_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Return the URL of the previous show from the page navigation."""
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(strip=True)
            if text in {"< Prev", "← Prev"}:
                href = anchor.get("href")
                href_str = str(href) if href else ""
                if href_str.startswith("http"):
                    return href_str
                if href_str.startswith("/"):
                    return f"{self.BASE_URL}{href_str}"
                if href_str:
                    return f"{self.BASE_URL}/{href_str}"
        return None

    def _scrape_show_setlist(
        self,
        show_id: str,
        source_url: str,
        show_uuid: Optional[str],
        show_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Scrape setlist rows from a show page."""
        soup = self._fetch_soup(source_url)
        if soup is None:
            return []

        setlist_heading = None
        for heading in soup.find_all("h2"):
            if heading.get_text(strip=True) == "SETLIST":
                setlist_heading = heading
                break

        if not setlist_heading:
            logger.warning(
                "No SETLIST heading found for show_id=%s (%s)", show_id, source_url
            )
            return []

        section = setlist_heading.find_parent("section")
        if not section:
            return []

        entries: List[Dict[str, Any]] = []
        current_set_number: Optional[int] = None
        per_set_position = 0

        for elem in section.find_all(["p", "ol"]):
            if elem.name == "p":
                label_text = elem.get_text(strip=True).rstrip(":")
                current_set_number = self._decode_set_label(label_text)
                per_set_position = 0
                continue

            if elem.name != "ol" or current_set_number is None:
                continue

            for li in elem.find_all("li", recursive=False):
                song_anchor = li.find("a", href=True)
                if not song_anchor:
                    continue

                song_name = song_anchor.get_text(strip=True)
                if not song_name:
                    continue

                song_uuid = self._extract_song_uuid(song_anchor)
                per_set_position += 1

                # Segues are indicated by a greater-than arrow SVG/image.
                is_segue = bool(li.find("img", src=re.compile(r"greater-than", re.I)))

                notes_sup = li.find("sup", class_="item-notes")
                song_notes = notes_sup.get_text(strip=True) if notes_sup else ""

                entries.append(
                    {
                        "show_id": show_id,
                        "source_uuid": show_uuid,
                        "song_uuid": song_uuid,
                        "set_number": current_set_number,
                        "song_position": per_set_position,
                        "song_name": song_name,
                        "is_segue": is_segue,
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

    def _extract_show_uuid(self, link: Any) -> Optional[str]:
        """Derive a stable source_uuid from a show link."""
        href = link.get("href")
        if not href:
            return None
        slug = self._extract_slug_from_url(href)
        if not slug:
            return None
        return self._ensure_uuid(slug)

    def _extract_song_uuid(self, anchor: Any) -> Optional[str]:
        """Derive a stable song_uuid from a song link."""
        href = anchor.get("href")
        if not href or "/song/" not in href:
            return None
        after = href.split("/song/")[-1]
        token = after.split("?")[0].strip("/")
        if not token:
            return None
        return self._ensure_uuid(token)

    def _extract_slug_from_url(self, url: str) -> Optional[str]:
        """Extract the show/song slug from a billybase.net URL."""
        if not url:
            return None
        cleaned = url.split("?")[0].rstrip("/")
        parts = cleaned.split("/")
        return parts[-1] if parts else None

    def _ensure_uuid(self, value: str) -> str:
        """Return a UUID string for the given token.

        If ``value`` is already a valid UUID it is returned unchanged; otherwise
        a deterministic UUIDv5 is generated from the billybase URL namespace.
        """
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            normalized = (value or "").strip()
            if not normalized:
                normalized = "unknown"
            generated = uuid.uuid5(
                uuid.NAMESPACE_URL, f"{self.BASE_URL}/setlist/{normalized}"
            )
            return str(generated)

    def _parse_location(self, location: str) -> Tuple[str, str, str]:
        """Split a location string into city, state, country."""
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

    def _decode_set_label(self, label: str) -> int:
        """Map set labels (Set 1, Encore, Soundcheck) to set numbers."""
        normalized = label.strip().lower()
        if "soundcheck" in normalized:
            return 0
        if "encore" in normalized:
            match = re.search(r"(\d+)", normalized)
            if match:
                return 90 + int(match.group(1))
            return 99
        match = re.search(r"(\d+)", normalized)
        if match:
            return int(match.group(1))
        return 1
