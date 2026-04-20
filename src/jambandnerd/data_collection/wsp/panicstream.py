"""PanicStream fallback scraper for recent Widespread Panic setlists.

This module discovers recent WSP show pages from PanicStream's year archives
and parses their setlist text into the same raw row contract used by the other
WSP collectors.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup

from jambandnerd.data_collection.config import JAMBANNERD_BOT_UA
from jambandnerd.data_collection.wsp.parser import SONGS_WITH_COMMAS

session = requests.Session()
session.headers.update({"User-Agent": JAMBANNERD_BOT_UA})

PANICSTREAM_YEAR_INDEX = "https://www.panicstream.com/vault/category/{year}/"
PANICSTREAM_SHOW_HREF_SUBSTR = "/vault/widespread-panic-"
COMMA_PLACEHOLDER = "||COMMA||"

NUMBERED_SET_MARKER_PATTERN = re.compile(
    r"(?:(?<=^)|(?<=\s))(?P<label>\d+|E)\.\s",
    flags=re.IGNORECASE,
)
TEXTUAL_SET_PATTERN = re.compile(
    r"(?<!\w)(?P<label>Set\s*\d+|Encore(?:\s*\d+)?)\s*[:.-]\s*"
    r"(?P<content>.*?)(?=(?:(?<!\w)(?:Set\s*\d+|Encore(?:\s*\d+)?)\s*[:.-])|$)",
    flags=re.IGNORECASE | re.DOTALL,
)


def _normalize_token(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _slug_matches_city_state(slug: str, city: str | None, state: str | None) -> bool:
    slug_norm = _normalize_token(slug)
    if city and _normalize_token(city) not in slug_norm:
        return False
    if state and _normalize_token(state) not in slug_norm:
        return False
    return True


def _parse_date_from_slug(slug: str) -> date | None:
    compact_match = re.search(r"widespread-panic-(\d{2})(\d{2})(\d{4})(?:-|$)", slug)
    if compact_match:
        month, day, year = compact_match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            return None

    dashed_match = re.search(r"widespread-panic-(\d{2})-(\d{2})-(\d{4})(?:-|$)", slug)
    if not dashed_match:
        return None

    month, day, year = dashed_match.groups()
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _normalize_set_label(raw_label: str) -> str:
    label = raw_label.upper().replace("SET", "").strip()
    if label in {"E", "ENCORE", "E1", "ENCORE 1"}:
        return "E"
    label = label.replace("ENCORE", "E").replace(" ", "")
    return label or "1"


def _protect_commas(text: str) -> str:
    protected = text
    for song in (*SONGS_WITH_COMMAS, "Bowlegged Woman, Knock Kneed Man"):
        protected = protected.replace(song, song.replace(",", COMMA_PLACEHOLDER))
    return protected


def _restore_commas(text: str) -> str:
    return text.replace(COMMA_PLACEHOLDER, ",")


def _strip_track_number(text: str) -> str:
    return re.sub(
        r"^\s*(?:(?:track\s*)?\d+\s*[\.\):-]\s*)+",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _normalize_song_name(song_name: str) -> str:
    cleaned = song_name.strip()
    lowered = cleaned.lower()

    if lowered == "walkin'":
        return "Walkin' (For Your Love)"

    if lowered in {
        "bowlegged woman knock kneed man",
        "bowlegged woman, knock kneed man",
        "knock kneed man",
    }:
        return "Bowlegged Woman"

    return cleaned


def _clean_song_token(song_text: str) -> str:
    text = unescape(song_text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2019", "'")
    text = text.replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text)
    text = _strip_track_number(text)
    text = text.strip(" -*")
    return _normalize_song_name(text.strip())


def _looks_like_setlist_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text)
    has_set_marker = bool(
        re.search(r"(?:Set\s*1|Encore|(?:(?<=^)|(?<=\s))(?:1|E)\.)", normalized, re.I)
    )
    return has_set_marker and ("," in normalized or ">" in normalized)


def _collect_jsonld_descriptions(raw_json: str) -> list[str]:
    descriptions: list[str] = []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return descriptions

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            description = node.get("description")
            if isinstance(description, str):
                descriptions.append(description)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return descriptions


def extract_setlist_text_candidates(soup: BeautifulSoup) -> list[str]:
    """Return likely setlist text candidates from a PanicStream show page."""
    candidates: list[str] = []

    for attrs in (
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ):
        tag = soup.find("meta", attrs=attrs)
        content = tag.get("content") if tag else None
        if isinstance(content, str) and _looks_like_setlist_text(content):
            candidates.append(content.strip())

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_json = script.string or script.get_text(strip=True)
        if not raw_json:
            continue
        for description in _collect_jsonld_descriptions(raw_json):
            if _looks_like_setlist_text(description):
                candidates.append(description.strip())

    content_area = soup.find(id="content-area")
    if content_area:
        content_text = content_area.get_text(" ", strip=True)
        if _looks_like_setlist_text(content_text):
            candidates.append(content_text)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = re.sub(r"\s+", " ", candidate).strip()
        if normalized and normalized not in seen:
            deduped.append(normalized)
            seen.add(normalized)
    return deduped


def _split_set_segments(setlist_text: str) -> list[tuple[str, str]]:
    normalized = re.sub(r"\s+", " ", unescape(setlist_text)).strip()

    segments: list[tuple[str, str]] = []
    for match in TEXTUAL_SET_PATTERN.finditer(normalized):
        label = _normalize_set_label(match.group("label"))
        content = match.group("content").strip(" :-")
        if content:
            segments.append((label, content))
    if segments:
        return segments

    marker_matches = list(NUMBERED_SET_MARKER_PATTERN.finditer(normalized))
    numbered_segments: list[tuple[str, str]] = []
    if marker_matches and len(marker_matches) <= 4 and marker_matches[0].start() == 0:
        for index, match in enumerate(marker_matches):
            start = match.end()
            end = (
                marker_matches[index + 1].start()
                if index + 1 < len(marker_matches)
                else len(normalized)
            )
            content = normalized[start:end].strip(" :-")
            if content:
                numbered_segments.append(
                    (_normalize_set_label(match.group("label")), content)
                )
    if numbered_segments and len(numbered_segments) <= 4:
        return numbered_segments

    return [("1", normalized)] if normalized else []


def _split_song_chunks(set_content: str) -> Iterable[str]:
    protected = _protect_commas(set_content)
    for chunk in re.split(r",|;|\n", protected):
        chunk = _restore_commas(chunk).strip()
        if chunk:
            yield chunk


def parse_setlist_text(setlist_text: str, show_id: str) -> list[dict[str, Any]]:
    """Parse PanicStream setlist text into normalized WSP raw rows."""
    rows: list[dict[str, Any]] = []

    for set_label, content in _split_set_segments(setlist_text):
        song_position = 1
        for chunk in _split_song_chunks(content):
            normalized_chunk = (
                chunk.replace("→", ">").replace("->", ">").replace("&gt;", ">")
            )
            song_parts = [
                part.strip() for part in normalized_chunk.split(">") if part.strip()
            ]
            for index, song_part in enumerate(song_parts):
                song_name = _clean_song_token(song_part)
                if not song_name:
                    continue
                rows.append(
                    {
                        "show_id": show_id,
                        "set_number": set_label,
                        "song_position": song_position,
                        "song_name": song_name,
                        "is_segue": index < len(song_parts) - 1,
                        "song_notes": "",
                        "source": "panicstream",
                    }
                )
                song_position += 1

    return rows


def parse_show_page_html(html: str, show_id: str) -> list[dict[str, Any]]:
    """Extract and parse PanicStream setlist text from raw show-page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for candidate in extract_setlist_text_candidates(soup):
        rows = parse_setlist_text(candidate, show_id)
        if rows:
            return rows
    return []


def find_show_on_year_index(
    target_date: date,
    city: str | None,
    state: str | None,
) -> str | None:
    """Search the relevant PanicStream year archive for a matching WSP show page."""
    response = session.get(
        PANICSTREAM_YEAR_INDEX.format(year=target_date.year), timeout=30
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    anchors = soup.find_all(
        "a", href=lambda href: href and PANICSTREAM_SHOW_HREF_SUBSTR in href
    )
    for anchor in anchors:
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        slug = href.rstrip("/").split("/")[-1]
        if _parse_date_from_slug(slug) != target_date:
            continue
        if not _slug_matches_city_state(slug, city, state):
            continue
        return href

    return None


def fetch_setlist_from_panicstream(
    show_date: date,
    show_id: str,
    city: str | None,
    state: str | None,
) -> list[dict[str, Any]]:
    """Fetch and parse a WSP setlist from PanicStream."""
    try:
        url = find_show_on_year_index(show_date, city, state)
    except Exception:
        return []

    if not url:
        return []

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except Exception:
        return []

    return parse_show_page_html(response.text, show_id)
