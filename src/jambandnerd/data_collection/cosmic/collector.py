"""Data collector for Daniel Donato's Cosmic Country (danielbase.com)."""

from __future__ import annotations

import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from requests import RequestException

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)

_DURATION_PATTERN = re.compile(r"^(?P<minutes>\d{1,2}):(?P<seconds>\d{2})")
_TOTAL_SIZE_PATTERN = re.compile(r"totalSize\s*:\s*(\d+)")


@dataclass
class _ShowParseResult:
    show: Dict[str, Any]
    setlist_rows: List[Dict[str, Any]]
    venue: Optional[Dict[str, Any]]


class CosmicCollector(BandCollector):
    """Collector implementation for Daniel Donato's Cosmic Country."""

    ARTIST_NAME = "Daniel Donato's Cosmic Country"
    _SHOW_SEARCH_PATH = "/db-show-search.xhtml"
    _SHOW_DETAIL_PATH = "/db-show.xhtml"
    _SONG_SEARCH_PATH = "/db-song-search.xhtml"
    _SONG_DETAIL_PATH = "/db-song.xhtml"

    def __init__(self) -> None:
        config = get_collector_config("cosmic")
        super().__init__(config)
        self._setlist_cache: dict[int, List[Dict[str, Any]]] = {}
        self._venues_cache: OrderedDict[int, Dict[str, Any]] = OrderedDict()
        logger.info(
            "Initialized CosmicCollector with rate limit %s/%ss",
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
        """Scrape the full Cosmic Country show catalog."""
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        total_expected = self._fetch_total_count(self._SHOW_SEARCH_PATH)
        highest_id_hint = self._fetch_highest_id_hint(self._SHOW_SEARCH_PATH)
        logger.info(
            "%s: Expecting approximately %s shows (hint max id=%s).",
            self.ARTIST_NAME,
            total_expected if total_expected is not None else "unknown",
            highest_id_hint if highest_id_hint is not None else "unknown",
        )

        shows: List[Dict[str, Any]] = []
        discovered_ids: set[int] = set()
        misses = 0
        consecutive_miss_limit = 200

        start_id = 1
        max_id = max(highest_id_hint or 0, total_expected or 0)
        if max_id <= 0:
            max_id = 600  # reasonable safety net for initial crawl

        current_id = start_id
        while True:
            parse_result = self._fetch_show(current_id)
            if parse_result:
                show_data = parse_result.show
                show_date_str = show_data.get("show_date")
                show_date_obj = self._parse_iso_date(show_date_str)
                if show_date_obj:
                    within_start = not start_date or show_date_obj >= start_date
                    within_end = not end_date or show_date_obj <= end_date
                    if within_start and within_end:
                        shows.append(show_data)
                self._setlist_cache[int(show_data["show_id"])] = parse_result.setlist_rows
                if parse_result.venue and parse_result.venue.get("venue_id") is not None:
                    venue_id = int(parse_result.venue["venue_id"])
                    self._venues_cache.setdefault(venue_id, parse_result.venue)

                discovered_ids.add(current_id)
                misses = 0
            else:
                misses += 1

            current_id += 1

            if total_expected is not None and len(discovered_ids) >= total_expected:
                break
            if misses >= consecutive_miss_limit:
                break
            if current_id > max_id and (total_expected is None or len(discovered_ids) < total_expected):
                # Extend the search window to catch newer shows and fill gaps.
                max_id += 200

        logger.info(
            "✅ %s: Discovered %s shows (filtered to %s after date constraints).",
            self.ARTIST_NAME,
            len(discovered_ids),
            len(shows),
        )
        return shows

    def collect_setlists(self, shows_to_process: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return normalized setlist rows for supplied shows."""
        results: List[Dict[str, Any]] = []
        for show in shows_to_process:
            raw_id = show.get("show_id")
            if raw_id is None:
                continue
            try:
                show_id = int(str(raw_id))
            except ValueError:
                continue

            if show_id not in self._setlist_cache:
                parse_result = self._fetch_show(show_id)
                if not parse_result:
                    continue
                self._setlist_cache[show_id] = parse_result.setlist_rows
                if parse_result.venue and parse_result.venue.get("venue_id") is not None:
                    venue_id = int(parse_result.venue["venue_id"])
                    self._venues_cache.setdefault(venue_id, parse_result.venue)

            results.extend(self._setlist_cache.get(show_id, []))

        logger.info("✅ %s: Prepared %s setlist rows.", self.ARTIST_NAME, len(results))
        return results

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Scrape the Cosmic Country song catalog."""
        total_expected = self._fetch_total_count(self._SONG_SEARCH_PATH)
        highest_id_hint = self._fetch_highest_id_hint(self._SONG_SEARCH_PATH)

        logger.info(
            "%s: Expecting approximately %s songs (hint max id=%s).",
            self.ARTIST_NAME,
            total_expected if total_expected is not None else "unknown",
            highest_id_hint if highest_id_hint is not None else "unknown",
        )

        songs: List[Dict[str, Any]] = []
        discovered_ids: set[int] = set()
        misses = 0
        consecutive_miss_limit = 200

        start_id = 1
        max_id = max(highest_id_hint or 0, total_expected or 0)
        if max_id <= 0:
            max_id = 600

        current_id = start_id
        while True:
            song_data = self._fetch_song(current_id)
            if song_data is not None:
                songs.append(song_data)
                discovered_ids.add(current_id)
                misses = 0
            else:
                misses += 1

            current_id += 1

            if total_expected is not None and len(discovered_ids) >= total_expected:
                break
            if misses >= consecutive_miss_limit:
                break
            if current_id > max_id and (total_expected is None or len(discovered_ids) < total_expected):
                max_id += 200

        logger.info("✅ %s: Collected %s songs.", self.ARTIST_NAME, len(songs))
        return songs

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Return venues observed while scraping shows."""
        return list(self._venues_cache.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fetch_total_count(self, path: str) -> Optional[int]:
        url = urljoin(self.config.base_url, path)
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.warning("Could not fetch total count from %s (%s)", url, exc)
            return None

        match = _TOTAL_SIZE_PATTERN.search(response.text)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _fetch_highest_id_hint(self, path: str) -> Optional[int]:
        url = urljoin(self.config.base_url, path)
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        max_id: Optional[int] = None
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "db-show.xhtml" in href or "db-song.xhtml" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                candidate = params.get("id") or params.get("show")
                if not candidate:
                    continue
                try:
                    value = int(candidate[0])
                except (ValueError, TypeError):
                    continue
                if max_id is None or value > max_id:
                    max_id = value
        return max_id

    def _fetch_show(self, show_id: int) -> Optional[_ShowParseResult]:
        url = urljoin(self.config.base_url, f"{self._SHOW_DETAIL_PATH}?id={show_id}")
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
        except RequestException:
            logger.debug("%s: show_id=%s not available.", self.ARTIST_NAME, show_id)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        if soup.find(id="mainForm:noShowTitle"):
            return None

        show_data = self._parse_show_metadata(soup, show_id, url)
        setlist_rows = self._parse_setlist(soup, show_id)
        venue_data = self._parse_venue(soup, show_id, url)

        return _ShowParseResult(show=show_data, setlist_rows=setlist_rows, venue=venue_data)

    def _fetch_song(self, song_id: int) -> Optional[Dict[str, Any]]:
        url = urljoin(self.config.base_url, f"{self._SONG_DETAIL_PATH}?id={song_id}")
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
        except RequestException:
            logger.debug("%s: song_id=%s not available.", self.ARTIST_NAME, song_id)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        title_node = soup.select_one("#mainForm\\:songTitle span")
        if not title_node or not title_node.get_text(strip=True):
            return None

        return self._parse_song_metadata(soup, song_id, url)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _parse_show_metadata(self, soup: BeautifulSoup, show_id: int, source_url: str) -> Dict[str, Any]:
        info_heading = soup.find(lambda tag: tag.name == "div" and tag.get_text(strip=True) == "Show Information")
        info_container = info_heading.find_next("div", class_="grid surface-card shadow-2 p-3") if info_heading else None
        info_pairs = self._extract_label_value_pairs(info_container)

        show_date = info_pairs.get("Show Date")
        venue_name = info_pairs.get("Venue Name")
        city = info_pairs.get("City")
        state = info_pairs.get("State")
        show_type = info_pairs.get("Show Type")

        venue_link = self._find_labeled_anchor(soup, "Venue Name")
        venue_id = self._parse_id_from_link(venue_link, "venue")

        data = {
            "show_id": show_id,
            "show_date": show_date,
            "venue_id": venue_id,
            "venue_name": venue_name,
            "city": city,
            "state": state,
            "country": None,
            "show_type": show_type,
            "source_url": source_url,
        }
        return data

    def _parse_venue(self, soup: BeautifulSoup, show_id: int, source_url: str) -> Optional[Dict[str, Any]]:
        venue_link = self._find_labeled_anchor(soup, "Venue Name")
        venue_id = self._parse_id_from_link(venue_link, "venue")
        if venue_id is None:
            return None

        info_heading = soup.find(lambda tag: tag.name == "div" and tag.get_text(strip=True) == "Show Information")
        info_container = info_heading.find_next("div", class_="grid surface-card shadow-2 p-3") if info_heading else None
        info_pairs = self._extract_label_value_pairs(info_container)
        venue_name = info_pairs.get("Venue Name")
        city = info_pairs.get("City")
        state = info_pairs.get("State")

        data = {
            "venue_id": venue_id,
            "venue_name": venue_name,
            "city": city,
            "state": state,
            "country": None,
            "source_url": urljoin(self.config.base_url, f"{self._SHOW_SEARCH_PATH}?venue={venue_id}"),
        }
        return data

    def _parse_setlist(self, soup: BeautifulSoup, show_id: int) -> List[Dict[str, Any]]:
        setlist_header = soup.find(lambda tag: tag.name == "div" and tag.get_text(strip=True) == "Setlist")
        if not setlist_header:
            return []

        container = setlist_header.find_next("div", class_="grid")
        if not container:
            return []

        rows: List[Dict[str, Any]] = []
        current_set_number = None
        set_index = 0

        for element in container.find_all(["div", "ol"], recursive=False):
            if element.name == "div":
                heading = element.get_text(strip=True)
                if not heading:
                    continue
                is_encore = "encore" in heading.lower()
                if is_encore:
                    current_set_number = 99
                else:
                    set_index += 1
                    current_set_number = set_index
                current_encore = bool(is_encore)
            elif element.name == "ol" and current_set_number is not None:
                song_position = 0
                for li in element.find_all("li", recursive=False):
                    link = li.find("a", href=True)
                    if not link:
                        continue
                    raw_title = link.get_text(strip=True)
                    if not raw_title:
                        continue

                    song_position += 1
                    is_segue = raw_title.endswith((">", "→"))
                    song_name = raw_title.rstrip(">").rstrip("→").strip()

                    song_id = self._parse_id_from_link(link, "id")
                    notes = self._extract_setlist_notes(li)

                    rows.append(
                        {
                            "show_id": show_id,
                            "set_number": current_set_number,
                            "song_position": song_position,
                            "song_name": song_name,
                            "song_id": song_id,
                            "is_segue": is_segue,
                            "encore": current_set_number == 99,
                            "song_notes": notes or None,
                        }
                    )
        return rows

    def _extract_setlist_notes(self, li: Any) -> str:
        notes: List[str] = []
        for tooltip in li.find_all("div", class_="ui-tooltip"):
            text = tooltip.get_text(" ", strip=True)
            if text.startswith("["):
                notes.append(text)
        return "; ".join(notes)

    def _parse_song_metadata(self, soup: BeautifulSoup, song_id: int, source_url: str) -> Dict[str, Any]:
        sections = soup.select("div.grid.surface-card.shadow-2.p-3")
        info_section = sections[0] if sections else None
        stats_section = sections[1] if len(sections) > 1 else None
        info_pairs = self._extract_label_value_pairs(info_section)
        stats_pairs = self._extract_label_value_pairs(stats_section)

        song_title = info_pairs.get("Song Title")
        song_origin = info_pairs.get("Song Origin")
        song_info = info_pairs.get("Song Info")
        written_by = info_pairs.get("Written By")

        shortest_version, shortest_show_id, shortest_date = self._parse_duration_entry(
            stats_section, "Shortest Version"
        )
        longest_version, longest_show_id, longest_date = self._parse_duration_entry(
            stats_section, "Longest Version"
        )

        times_played = self._coerce_int(stats_pairs.get("Total Times Played"))

        longest_gap_shows, longest_gap_start, longest_gap_end = self._parse_gap_streak_entry(
            stats_section, "Longest Gap"
        )
        longest_streak, longest_streak_start, longest_streak_end = self._parse_gap_streak_entry(
            stats_section, "Longest Streak"
        )

        lyrics_node = soup.select_one("#mainForm\\:lyrics")
        lyrics_text = lyrics_node.get_text("\n", strip=True) if lyrics_node else None

        data = {
            "song_id": song_id,
            "song_name": song_title,
            "song_origin": song_origin,
            "song_notes": song_info,
            "written_by": written_by,
            "times_played": times_played,
            "shortest_version_seconds": shortest_version,
            "shortest_version_show_id": shortest_show_id,
            "shortest_version_played_at": shortest_date,
            "longest_version_seconds": longest_version,
            "longest_version_show_id": longest_show_id,
            "longest_version_played_at": longest_date,
            "longest_gap_shows": longest_gap_shows,
            "longest_gap_start_show_id": longest_gap_start,
            "longest_gap_end_show_id": longest_gap_end,
            "longest_streak": longest_streak,
            "longest_streak_start_show_id": longest_streak_start,
            "longest_streak_end_show_id": longest_streak_end,
            "lyrics": lyrics_text,
            "source_url": source_url,
        }
        return data

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _extract_label_value_pairs(self, container: Any) -> Dict[str, str]:
        pairs: Dict[str, str] = {}
        if not container:
            return pairs

        labels = container.find_all("div", class_=re.compile(r"text-xl\s+font-semibold"))
        for label in labels:
            label_text = label.get_text(strip=True)
            if not label_text:
                continue
            sibling = label.find_next_sibling()
            if sibling is None:
                continue
            value_text = sibling.get_text(" ", strip=True)
            pairs[label_text] = value_text
        return pairs

    def _find_labeled_anchor(self, soup: BeautifulSoup, label_text: str) -> Optional[Any]:
        label_node = soup.find(lambda tag: tag.name == "div" and tag.get_text(strip=True) == label_text)
        if not label_node:
            return None
        return label_node.find_next("a", href=True)

    def _parse_id_from_link(self, link: Optional[Any], param: str) -> Optional[int]:
        if not link:
            return None
        href = link.get("href")
        if not href:
            return None
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        value = params.get(param)
        if not value:
            return None
        try:
            return int(value[0])
        except (ValueError, TypeError):
            return None

    def _parse_duration_entry(
        self,
        container: Any,
        label_text: str,
    ) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        if not container:
            return (None, None, None)

        label_node = container.find(lambda tag: tag.name == "div" and tag.get_text(strip=True) == label_text)
        if not label_node:
            return (None, None, None)
        anchor = label_node.find_next("a", href=True)
        if not anchor:
            return (None, None, None)

        text = anchor.get_text(strip=True)
        match = _DURATION_PATTERN.match(text)
        seconds = None
        played_at = None
        if match:
            try:
                minutes = int(match.group("minutes"))
                secs = int(match.group("seconds"))
                seconds = minutes * 60 + secs
            except ValueError:
                seconds = None
        if "(" in text and ")" in text:
            played_at = text.split("(", 1)[1].rstrip(")")

        show_id = self._parse_id_from_link(anchor, "id")
        return (seconds, show_id, played_at)

    def _parse_gap_streak_entry(
        self,
        container: Any,
        label_text: str,
    ) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        if not container:
            return (None, None, None)

        label_node = container.find(lambda tag: tag.name == "div" and tag.get_text(strip=True) == label_text)
        if not label_node:
            return (None, None, None)

        anchors = label_node.find_all("a", href=True)
        if len(anchors) < 2:
            return (None, None, None)

        numbers = [
            int(token)
            for token in label_node.stripped_strings
            if token.isdigit()
        ]
        value = numbers[0] if numbers else None
        start_show_id = self._parse_id_from_link(anchors[0], "id")
        end_show_id = self._parse_id_from_link(anchors[-1], "id")
        return (value, start_show_id, end_show_id)

    def _coerce_int(self, text: Optional[str]) -> Optional[int]:
        if text is None:
            return None
        cleaned = text.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None

    def _parse_iso_date(self, text: Optional[str]) -> Optional[date]:
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None
