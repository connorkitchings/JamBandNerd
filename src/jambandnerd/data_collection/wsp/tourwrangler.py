"""TourWrangler backup scraper for Widespread Panic setlists.

This module provides helper functions to discover and parse Widespread Panic
setlists from TourWrangler to be used as a fallback when Everyday Companion
is missing recent historical show setlists.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from jambandnerd.data_collection.config import JAMBANNERD_BOT_UA

session = requests.Session()
session.headers.update(
    {
        "User-Agent": JAMBANNERD_BOT_UA,
    }
)

TW_SETLISTS_INDEX = "https://www.tourwrangler.com/artists/widespread-panic/setlists/"
TW_SHOW_HREF_SUBSTR = "/artists/widespread-panic/shows/"

# Known artist-credit markers that appear after songs and should be removed
ARTIST_MARKERS = {
    "widespread panic",
    "junior kimbrough",
    "drivin’ n’ cryin’",
    "drivin' n' cryin'",
    "warren zevon",
    "brute.",
    "talking heads",
    "buffalo springfield",
    "bloodkin",
    "nrbq",
    "bobby rush",
    "beanland",
    "murray mclauchlan",
    "the jimi hendrix experience",
    "traditional",
    "j.j. cale",
    "sonny boy williamson",
    "tom waits",
    "tom petty",
    "neil young",
    "jerry joseph",
    "van morrison",
}


# Build a regex replacer for artist markers that does not rely on \b at the end of punctuation
def _strip_artist_markers(s: str) -> str:
    out = s
    for marker in ARTIST_MARKERS:
        pat = re.compile(rf"\s*,\s*{re.escape(marker)}", re.IGNORECASE)
        out = pat.sub("", out)
    # Also handle 'Widespread Panic' capitalized variants
    out = re.sub(r"\s*,\s*Widespread\s+Panic", "", out, flags=re.IGNORECASE)
    return out


# Segment terminators that indicate end of useful setlist content
STOP_WORDS = [
    "liner notes",
    "videos",
    "more by",
    "you might also like",
]


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_date_from_slug(slug: str) -> Optional[date]:
    """Parse a date from a TourWrangler show slug like 'october-4-2025-...'."""
    # expect tokens like ['october','4','2025', ...]
    parts = slug.strip("/").split("-")
    # find first token that can be a 4-digit year
    year_idx = None
    for i, tok in enumerate(parts):
        if tok.isdigit() and len(tok) == 4:
            year_idx = i
            break
    if year_idx is None or year_idx < 2:
        return None
    try:
        month_name = parts[year_idx - 2].lower()
        day_str = parts[year_idx - 1]
        # day may include ordinal or punctuation; keep digits only
        day_digits = re.sub(r"[^0-9]", "", day_str)
        month = MONTHS.get(month_name)
        if not month or not day_digits:
            return None
        return date(int(parts[year_idx]), month, int(day_digits))
    except Exception:
        return None


def _normalize_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _slug_matches_city_state(
    slug: str, city: Optional[str], state: Optional[str]
) -> bool:
    if not city and not state:
        return True
    slug_norm = _normalize_token(slug)
    ok = True
    if city:
        ok = ok and (_normalize_token(city) in slug_norm)
    if state:
        ok = ok and (_normalize_token(state) in slug_norm)
    return ok


def _normalize_song_name(song_name: str) -> str:
    """Strip whitespace from a song name."""
    return song_name.strip()


def _remove_parenthesized_text(text: str) -> str:
    """Remove parenthesized text from a string."""
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def _clean_song_text(text: str) -> str:
    # remove bracketed references like [ 1 ] or [1]
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    # remove stray bracket tokens
    text = text.replace("[", " ").replace("]", " ")
    # collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_segue(song_chunk: str) -> List[Tuple[str, bool]]:
    """Split a song chunk on '>' segues and mark is_segue for all but the last."""
    parts = [p.strip() for p in song_chunk.split(">") if p.strip()]
    out: List[Tuple[str, bool]] = []
    for i, p in enumerate(parts):
        out.append((_clean_song_text(p.rstrip("*")), i < len(parts) - 1))
    return out


def _parse_sets_from_text(block_text: str, show_id: str) -> List[Dict[str, Any]]:
    """Parse a text block that includes 'Set 1', 'Set 2', 'Encore' sections.

    Handles formats like:
      'Set 1: Song A , Song B , Song C > Song D\nSet 2: ...\nEncore ...'
    and more free-form text if present.
    """
    # Normalize whitespace and quotes
    text = block_text.replace("\u00a0", " ")  # non-breaking space
    text = text.replace("\u2019", "'")

    # Build segments
    segments: List[Tuple[str, str]] = []  # (set_key, content)

    # Use regex to find headers and their spans across entire page
    pattern = re.compile(
        r"(Set\s*([0-9]+)|Encore)\s*:?(.*?)(?=(Set\s*[0-9]+|Encore|$))",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        header = m.group(1)
        content = m.group(3).strip()
        header_l = header.lower()
        if header_l.startswith("encore"):
            set_key = "E"
        else:
            # extract number
            num = re.sub(r"[^0-9]", "", header)
            set_key = num if num else "1"

        # Trim content at any STOP_WORDS to avoid contamination from page chrome
        content_l = content.lower()
        cut_idx = None
        for sw in STOP_WORDS:
            i = content_l.find(sw)
            if i != -1:
                cut_idx = i if cut_idx is None else min(cut_idx, i)
        if cut_idx is not None:
            content = content[:cut_idx]

        # Replace known artist markers with commas to break tokens cleanly
        content = _strip_artist_markers(content)

        segments.append((set_key, content))

    def looks_like_non_song(token: str) -> bool:
        t = token.strip()
        if not t:
            return True
        tl = t.lower()
        # drop lone brackets or bracket-only remnants
        if tl in {"[", "]"}:
            return True
        # pure numeric tokens (likely footnote numbers)
        if re.fullmatch(r"\d+", tl) and len(tl) <= 2:
            return True
        # pure year
        if re.fullmatch(r"[12][0-9]{3}", tl):
            return True
        # month day ordinal
        if re.fullmatch(
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(st|nd|rd|th)?",
            tl,
        ):
            return True
        # punctuation-only or dash
        if re.fullmatch(r"[-—–]+", tl):
            return True
        # obvious non-song site chrome
        if tl in {"videos", "liner notes", "stream", "mark as attended"}:
            return True
        # mostly numeric tokens
        if len(re.findall(r"\b\d+\b", tl)) > 3 and len(tl) < 10:
            return True
        # extremely long lines not typical for song titles
        if len(t) > 80:
            return True
        # explicit artist-credit spillover that should not persist as songs
        if tl in ARTIST_MARKERS:
            return True

        # Detect artist names: tokens with "&" or "and" often indicate artist credits
        # e.g., "Neil Young & Crazy Horse", "Simon and Garfunkel"
        if " & " in t or " and " in tl:
            return True

        # Detect full names (First Last or First Middle Last) that are likely artists
        # Pattern: 2-3 capitalized words, each starting with capital letter
        words = t.split()
        if 2 <= len(words) <= 3:
            # Check if all words are capitalized (title case) - typical for artist names
            if all(
                word[0].isupper() and word[1:].islower()
                for word in words
                if len(word) > 0
            ):
                # Additional check: if it contains common artist name patterns
                # like initials (J.J., B.B.) or common first names
                if any("." in word for word in words):  # Has initials like "J.J."
                    return True

        return False

    rows: List[Dict[str, Any]] = []
    for set_key, content in segments:
        # Split on commas and newlines first
        raw_pieces = [p.strip() for p in re.split(r",|\n", content) if p.strip()]
        # If still single blob with many ' > ', keep as one piece to split by segue
        pieces = (
            raw_pieces
            if not (len(raw_pieces) == 1 and ">" in raw_pieces[0])
            else [raw_pieces[0]]
        )

        song_pos = 1
        for piece in pieces:
            # split on segues
            for song_name, is_segue in _split_segue(piece):
                if not song_name:
                    continue
                # Token-level cleanup: strip artist markers and brackets again
                token = _strip_artist_markers(song_name)
                token = _remove_parenthesized_text(token)
                token = _clean_song_text(token)
                cleaned = _normalize_song_name(token.strip())
                # Drop non-song tokens (now includes artist name detection)
                if looks_like_non_song(cleaned):
                    continue
                rows.append(
                    {
                        "show_id": show_id,
                        "set_number": set_key,
                        "song_position": song_pos,
                        "song_name": cleaned,
                        "is_segue": is_segue,
                        "song_notes": "",
                    }
                )
                song_pos += 1
    return rows


def find_show_on_index(
    target_date: date, city: Optional[str], state: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Search the TourWrangler setlists index for a show matching the target date.

    Returns (url, text_block) if found, otherwise (None, None)."""
    resp = session.get(TW_SETLISTS_INDEX, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    anchors = soup.find_all("a", href=lambda h: h and TW_SHOW_HREF_SUBSTR in h)
    target_url: Optional[str] = None
    target_text: Optional[str] = None

    for a in anchors:
        href = a["href"]
        # absolute or relative
        url = href if href.startswith("http") else f"https://www.tourwrangler.com{href}"
        # extract slug component
        try:
            slug = url.split("/shows/")[-1].strip("/")
        except Exception:
            continue
        d = _parse_date_from_slug(slug)
        if not d or d != target_date:
            continue
        # If city/state provided, ensure the slug contains them to disambiguate
        if not _slug_matches_city_state(slug, city, state):
            continue
        target_url = url
        # try to capture nearby text for parsing sets on index card
        card_text = a.get_text(" ", strip=True)
        # Sometimes the link text is just venue; climb to parent for more text
        if len(card_text.split()) < 5 and a.parent is not None:
            card_text = a.parent.get_text(" ", strip=True)
        target_text = card_text
        break

    return target_url, target_text


def parse_show_page(url: str, show_id: str) -> List[Dict[str, Any]]:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    page_text = soup.get_text("\n", strip=True)
    return _parse_sets_from_text(page_text, show_id)


def fetch_setlist_from_tourwrangler(
    show_date: date,
    show_id: str,
    city: Optional[str],
    state: Optional[str],
) -> List[Dict[str, Any]]:
    """Try to obtain a setlist for a given show from TourWrangler.

    Strategy:
      1) Find the show link on the setlists index by date (and city/state to disambiguate).
      2) Try to parse the sets from the index card text if present.
      3) Fallback to fetching the show page and parsing its text.
    """
    try:
        url, text_block = find_show_on_index(show_date, city, state)
    except Exception:
        url, text_block = None, None

    rows: List[Dict[str, Any]] = []

    if text_block:
        rows = _parse_sets_from_text(text_block, show_id)
        # If the index card parsing yielded nothing but we have a URL, try the page
        if not rows and url:
            try:
                rows = parse_show_page(url, show_id)
            except Exception:
                rows = []
    elif url:
        try:
            rows = parse_show_page(url, show_id)
        except Exception:
            rows = []

    return rows
