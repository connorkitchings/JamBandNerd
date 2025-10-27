"""Umphrey's McGee data collector."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import RequestException

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)


_MONTH_PATTERN = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}$")


@dataclass
class _ShowMetadata:
    source_url: str
    show_date: date
    venue_name: Optional[str]
    venue_city: Optional[str]
    venue_state: Optional[str]
    venue_country: Optional[str]
    show_notes: Optional[str]

    @property
    def as_payload(self) -> Dict[str, Any]:
        """Convert metadata to a serializable payload."""
        return {
            "source_url": self.source_url,
            "show_date": self.show_date.isoformat(),
            "venue_name": self.venue_name,
            "venue_city": self.venue_city,
            "venue_state": self.venue_state,
            "venue_country": self.venue_country,
            "show_notes": self.show_notes,
        }


class UmCollector(BandCollector):
    """Collect Umphrey's McGee data from allthings.umphreys.com."""

    ARTIST_NAME = "Umphrey's McGee"
    BASE_URL = "https://allthings.umphreys.com"
    EARLIEST_YEAR = 1998  # First year listed in All Things UM archive

    def __init__(self) -> None:
        config = get_collector_config("um")
        super().__init__(config)
        self._shows_by_url: Dict[str, _ShowMetadata] = {}
        self._setlists_by_url: Dict[str, List[Dict[str, Any]]] = {}
        self._parsed_years: set[int] = set()
        logger.info(
            "Initialized UmCollector with rate limit: %s/%ss",
            config.rate_limit_calls,
            config.rate_limit_window,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def collect_songs(self) -> List[Dict[str, Any]]:
        """Scrape the UM song catalog."""

        url = f"{self.BASE_URL}/song/"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch UM songs from %s: %s", url, exc)
            return []

        try:
            target_df = _extract_table(
                html=response.text,
                required_columns={"Song Name", "Original Artist", "Debut Date", "Last Played"},
            )
        except ValueError as exc:
            logger.error("Could not parse UM song table: %s", exc)
            return []

        if target_df.empty:
            logger.warning("UM songs table was empty.")
            return []

        column_map = {
            "Song Name": "song_name",
            "Original Artist": "original_artist",
            "Debut Date": "debut_date",
            "Last Played": "last_played",
            "Times Played Live": "times_played_live",
            "Avg Show Gap": "avg_show_gap",
        }
        df = target_df.rename(columns={k: v for k, v in column_map.items() if k in target_df.columns})

        # Normalize string columns
        df["song_name"] = df["song_name"].astype(str).str.strip()

        if "original_artist" in df.columns:
            df["original_artist"] = df["original_artist"].replace({"—": None, "N/A": None, "": None})

        # Convert dates to ISO format
        for col in ("debut_date", "last_played"):
            if col in df.columns:
                df[col] = (
                    pd.to_datetime(df[col], errors="coerce")
                    .dt.date.apply(lambda d: d.isoformat() if pd.notnull(d) else None)
                )

        # Numeric conversions
        if "times_played_live" in df.columns:
            df["times_played_live"] = pd.to_numeric(df["times_played_live"], errors="coerce").fillna(0).astype(int)
        if "avg_show_gap" in df.columns:
            df["avg_show_gap"] = pd.to_numeric(df["avg_show_gap"], errors="coerce")

        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        logger.info("✅ %s: Collected %s songs.", self.ARTIST_NAME, len(records))
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Scrape UM venue data."""

        url = f"{self.BASE_URL}/venues/"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch UM venues from %s: %s", url, exc)
            return []

        try:
            target_df = _extract_table(
                html=response.text,
                required_columns={"Venue Name", "City", "State", "Country"},
            )
        except ValueError as exc:
            logger.error("Could not parse UM venue table: %s", exc)
            return []

        if target_df.empty:
            logger.warning("UM venue table was empty.")
            return []

        df = target_df.copy()
        df.reset_index(drop=True, inplace=True)
        if "id" in df.columns:
            df.drop(columns=["id"], inplace=True)
        column_map = {
            "Venue Name": "venue_name",
            "City": "venue_city",
            "State": "venue_state",
            "Country": "venue_country",
            "Times Played": "times_played",
            "Last Played": "last_played",
        }
        df.rename(columns={k: v for k, v in column_map.items() if k in df.columns}, inplace=True)

        if "last_played" in df.columns:
            df["last_played"] = (
                pd.to_datetime(df["last_played"], errors="coerce")
                .dt.date.apply(lambda d: d.isoformat() if pd.notnull(d) else None)
            )
        if "times_played" in df.columns:
            df["times_played"] = pd.to_numeric(df["times_played"], errors="coerce").fillna(0).astype(int)

        df["venue_name"] = df["venue_name"].astype(str).str.strip()
        df["venue_city"] = df["venue_city"].astype(str).str.strip()
        df["venue_state"] = df["venue_state"].astype(str).str.strip()
        df["venue_country"] = df["venue_country"].astype(str).str.strip()

        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        logger.info("✅ %s: Collected %s venues.", self.ARTIST_NAME, len(records))
        return records

    def collect_shows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Scrape show metadata for a date range."""

        if end_date and start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        start = start_date or date(self.EARLIEST_YEAR, 1, 1)
        end = end_date or date.today()

        years = range(start.year, end.year + 1)
        for year in years:
            self._ensure_year_loaded(year)

        records: List[Dict[str, Any]] = []
        for show in self._shows_by_url.values():
            if show.show_date < start or show.show_date > end:
                continue

            payload = show.as_payload
            # Add derived fields
            payload.update(
                {
                    "show_year": show.show_date.year,
                    "show_month": show.show_date.month,
                    "show_day": show.show_date.day,
                }
            )
            records.append(payload)

        records.sort(key=lambda item: item["show_date"])
        logger.info("✅ %s: Collected %s shows between %s and %s.", self.ARTIST_NAME, len(records), start, end)
        return records

    def collect_setlists(self, shows_to_process: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return setlist rows for the provided shows."""

        shows_list = list(shows_to_process)
        if not shows_list:
            logger.info("No UM shows supplied for setlist scraping.")
            return []

        results: List[Dict[str, Any]] = []
        for record in shows_list:
            show_id = str(record.get("show_id", "")).strip()
            if not show_id:
                continue
            source_url = record.get("source_url") or record.get("link")
            if not source_url:
                logger.debug("Skipping show_id=%s because no source_url/link present.", show_id)
                continue
            if source_url not in self._setlists_by_url:
                # Attempt a targeted fetch if the URL was not covered by the cached year pages
                parsed = self._fetch_single_show(source_url)
                if not parsed:
                    logger.warning("No setlist found for show_id=%s (%s)", show_id, source_url)
                    continue

            rows = self._setlists_by_url.get(source_url, [])
            metadata = self._shows_by_url.get(source_url)
            if not metadata:
                logger.debug("Setlists cached but metadata missing for %s; refetching.", source_url)
                parsed = self._fetch_single_show(source_url)
                if not parsed:
                    continue
                rows = self._setlists_by_url.get(source_url, [])
                metadata = self._shows_by_url.get(source_url)

            if not metadata:
                continue

            for row in rows:
                results.append(
                    {
                        "show_id": show_id,
                        "source_url": source_url,
                        "show_date": metadata.show_date.isoformat(),
                        "venue_name": metadata.venue_name,
                        "venue_city": metadata.venue_city,
                        "venue_state": metadata.venue_state,
                        "venue_country": metadata.venue_country,
                        "set_label": row["set_label"],
                        "set_sequence": row["set_sequence"],
                        "song_position": row["song_position"],
                        "show_position": row["show_position"],
                        "song_name": row["song_name"],
                        "is_segue": row["is_segue"],
                        "encore": row["encore"],
                        "footnote_symbol": row.get("footnote_symbol"),
                        "footnote_text": row.get("footnote_text"),
                        "song_notes": row.get("song_notes"),
                    }
                )

        logger.info("✅ %s: Collected %s setlist rows.", self.ARTIST_NAME, len(results))
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _ensure_year_loaded(self, year: int) -> None:
        """Ensure a year archive page has been parsed and cached."""

        if year in self._parsed_years:
            return

        url = f"{self.BASE_URL}/setlists/{year}"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code == 404:
                logger.warning("UM setlist archive for %s returned 404; skipping year.", year)
                self._parsed_years.add(year)
                return
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch UM setlists for %s: %s", year, exc)
            return

        soup = BeautifulSoup(response.text, "html.parser")
        sections = soup.select("section.setlist-artist-1")
        if not sections:
            if year > date.today().year:
                logger.info("Skipping UM setlist archive for %s; no sections published yet.", year)
            else:
                logger.warning("No UM setlist sections found for year %s.", year)
            self._parsed_years.add(year)
            return

        added = 0
        for section in sections:
            parsed = self._parse_show_section(section)
            if not parsed:
                continue
            metadata, rows = parsed
            self._shows_by_url[metadata.source_url] = metadata
            self._setlists_by_url[metadata.source_url] = rows
            added += 1

        logger.info("Parsed %s UM shows from %s archive.", added, year)
        self._parsed_years.add(year)

    def _fetch_single_show(self, source_url: str) -> Optional[Tuple[_ShowMetadata, List[Dict[str, Any]]]]:
        """Fetch and parse a single show page when not covered by year cache."""

        try:
            response = self.session.get(source_url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch UM setlist page %s: %s", source_url, exc)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        section = soup.select_one("section.setlist-artist-1")
        if not section:
            logger.warning("Could not locate setlist section on %s", source_url)
            return None

        parsed = self._parse_show_section(section, explicit_url=source_url)
        if not parsed:
            return None
        metadata, rows = parsed
        self._shows_by_url[metadata.source_url] = metadata
        self._setlists_by_url[metadata.source_url] = rows
        return parsed

    def _parse_show_section(
        self,
        section: Tag,
        *,
        explicit_url: Optional[str] = None,
    ) -> Optional[Tuple[_ShowMetadata, List[Dict[str, Any]]]]:
        """Parse a show section from the archive page."""

        container = section.find("div", class_="setlist")
        if not container:
            return None

        header = container.find("div", class_="setlist-date-long")
        body = container.find("div", class_="setlist-body")
        if not header or not body:
            return None

        date_anchor = _find_date_anchor(header)
        if not date_anchor:
            return None

        relative_url = date_anchor.get("href") or ""
        source_url = explicit_url or urljoin(self.BASE_URL, relative_url)

        date_text = date_anchor.get_text(strip=True)
        try:
            show_date = datetime.strptime(date_text, "%B %d, %Y").date()
        except ValueError:
            logger.warning("Could not parse UM show date from '%s' (%s)", date_text, source_url)
            return None

        venue_anchor = header.find("a", class_="venue")
        venue_name = venue_anchor.get_text(strip=True) if venue_anchor else None

        city_anchor = header.find("a", href=_href_contains("/venues/city/"))
        state_anchor = header.find("a", href=_href_contains("/venues/state/"))
        country_anchor = header.find("a", href=_href_contains("/venues/country/"))

        venue_city = city_anchor.get_text(strip=True) if city_anchor else None
        venue_state = state_anchor.get_text(strip=True) if state_anchor else None
        venue_country = country_anchor.get_text(strip=True) if country_anchor else None

        footnotes_map = _parse_footnotes(container)
        show_notes = _parse_show_notes(container)
        setlist_rows = _parse_setlist_body(body, footnotes_map)

        metadata = _ShowMetadata(
            source_url=source_url,
            show_date=show_date,
            venue_name=venue_name,
            venue_city=venue_city,
            venue_state=venue_state,
            venue_country=venue_country,
            show_notes=show_notes,
        )

        return metadata, setlist_rows


# ----------------------------------------------------------------------
# Pure helper functions
# ----------------------------------------------------------------------

def _extract_table(html: str, required_columns: set[str]) -> pd.DataFrame:
    """Extract the first table containing all required columns."""
    buffer = StringIO(html)
    tables = pd.read_html(buffer)
    for table in tables:
        if required_columns.issubset(set(table.columns)):
            return table
    raise ValueError(f"No table contained required columns: {sorted(required_columns)}")


def _find_date_anchor(header: Tag) -> Optional[Tag]:
    """Find the anchor containing the show date."""

    for anchor in header.find_all("a"):
        text = anchor.get_text(strip=True)
        if text and _MONTH_PATTERN.match(text):
            return anchor
    return None


def _href_contains(fragment: str):
    """Return a predicate for BeautifulSoup's find to match href fragments."""

    def _matcher(href: Optional[str]) -> bool:
        return bool(href and fragment in href)

    return _matcher


def _parse_footnotes(container: Tag) -> Dict[str, str]:
    """Parse the footnotes section of a setlist."""

    mapping: Dict[str, str] = {}
    footnotes = container.find("p", class_="setlist-footnotes")
    if not footnotes:
        return mapping

    for segment in footnotes.stripped_strings:
        if segment.lower().startswith("footnotes"):
            continue
        match = re.match(r"\[([^\]]+)\]\s*(.+)", segment)
        if not match:
            continue
        key, text = match.groups()
        mapping[key.strip()] = text.strip()
    return mapping


def _parse_show_notes(container: Tag) -> Optional[str]:
    """Extract show notes text if present."""

    label = container.find("b", class_="shownotes-label")
    if not label or not label.parent:
        return None

    parent = label.parent
    text = parent.get_text(" ", strip=True)
    label_text = label.get_text(strip=True)
    if label_text:
        text = text.replace(label_text, "", 1).strip(" :")
    return text or None


def _parse_setlist_body(body: Tag, footnotes_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse setlist paragraphs into structured rows."""

    rows: List[Dict[str, Any]] = []
    show_position = 0
    set_sequence = 0
    encore_counter = 0

    for paragraph in body.find_all("p"):
        set_label_tag = paragraph.find("b")
        song_spans = paragraph.find_all("span", class_="setlist-songbox")
        if not set_label_tag or not song_spans:
            continue

        raw_label = set_label_tag.get_text(strip=True).rstrip(":")
        normalized_label, encore_counter = _normalize_set_label(raw_label, encore_counter)
        set_sequence += 1
        song_position = 0

        for span in song_spans:
            song_position += 1
            show_position += 1

            anchor = span.find("a")
            if anchor:
                song_name = anchor.get_text(strip=True)
            else:
                raw_text = span.get_text(" ", strip=True)
                raw_text = re.sub(r"\[[^\]]+\]", "", raw_text)  # Remove inline footnote markers
                raw_text = raw_text.replace(">", " ").replace(",", " ")
                song_name = re.sub(r"\s+", " ", raw_text).strip()

            footnote_symbol = None
            footnote_text = None
            sup = span.find("sup")
            if sup:
                footnote_symbol = sup.get_text(strip=True).strip("[]")
                if footnote_symbol:
                    footnote_text = footnotes_map.get(footnote_symbol)

            is_segue = _span_contains_segue(span)
            rows.append(
                {
                    "set_label": normalized_label,
                    "set_sequence": set_sequence,
                    "song_position": song_position,
                    "show_position": show_position,
                    "song_name": song_name,
                    "is_segue": is_segue,
                    "encore": normalized_label.startswith("E"),
                    "footnote_symbol": footnote_symbol,
                    "footnote_text": footnote_text,
                    "song_notes": footnote_text,
                }
            )
    return rows


def _normalize_set_label(raw_label: str, encore_counter: int) -> Tuple[str, int]:
    """Normalize set labels to consistent tokens."""

    label = raw_label.lower()
    if label == "one set":
        return "1", encore_counter
    if label.startswith("set"):
        number = label.replace("set", "").strip()
        return number or "1", encore_counter
    if "encore" in label:
        encore_counter += 1
        digits = re.sub(r"\D", "", raw_label)
        if digits:
            return f"E{digits}", encore_counter
        return ("E" if encore_counter == 1 else f"E{encore_counter}"), encore_counter
    if "soundcheck" in label:
        return "SC", encore_counter
    return raw_label, encore_counter


def _span_contains_segue(span: Tag) -> bool:
    """Determine whether a song span indicates a segue (contains '>')."""

    for child in span.contents:
        if isinstance(child, NavigableString) and ">" in child:
            return True
    return False
