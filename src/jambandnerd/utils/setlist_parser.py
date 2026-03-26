"""Setlist parsing utilities for human-readable setlist text."""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List

from src.jambandnerd.db.connection import get_supabase_client


def parse_setlist_text(text: str) -> List[Dict]:
    """Parse a human-entered setlist text into structured rows.

    Expected lines like:
      Set 1 Song A, Song B > Song C, Song D
      Set 2 ...
      Encore Song X, Song Y

    Returns rows with keys: set_number, song_position, song_name, is_segue, song_notes
    Encore is set_number 99.
    """
    rows: List[Dict] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    for line in lines:
        set_number = None
        songs_part = None

        m = re.match(r"^Set\s*(\d+)\s+(.*)$", line, flags=re.IGNORECASE)
        if m:
            set_number = int(m.group(1))
            songs_part = m.group(2)
        else:
            m2 = re.match(r"^Encore\s+(.*)$", line, flags=re.IGNORECASE)
            if m2:
                set_number = 99
                songs_part = m2.group(1)

        if set_number is None or songs_part is None:
            continue

        items = [s.strip() for s in songs_part.split(",") if s.strip()]
        pos = 1
        for item in items:
            parts = [p.strip() for p in item.split(">") if p.strip()]
            for i, part in enumerate(parts):
                song_name = part.replace("\u2019", "'").replace("\u2018", "'").strip()
                rows.append(
                    {
                        "set_number": set_number,
                        "song_position": pos,
                        "song_name": song_name,
                        "is_segue": i < (len(parts) - 1),
                        "song_notes": "",
                    }
                )
                pos += 1

    return rows


def ensure_show(
    client,
    band: str,
    show_date: str,
    venue_name: str,
    city: str,
    state: str,
) -> str:
    """Ensure a show exists in {band}_shows_raw, return show_id.

    Strategy: if a show with this date+venue exists, reuse it; otherwise, generate a
    deterministic show_id hash from date|venue and upsert a new row.
    """
    shows_tbl = f"{band}_shows_raw"

    try:
        resp = (
            client.table(shows_tbl)
            .select("show_id")
            .eq("show_date", show_date)
            .eq("venue_name", venue_name)
            .limit(1)
            .execute()
        )
        if resp.data:
            return str(resp.data[0]["show_id"])
    except Exception:
        pass

    show_id = str(
        int(hashlib.md5(f"{show_date}|{venue_name}".encode()).hexdigest()[:8], 16)
    )

    row = {
        "show_id": show_id,
        "show_date": show_date,
        "venue_name": venue_name,
        "city": city,
        "state": state,
    }
    if band == "wsp":
        row["source_hash"] = None

    client.table(shows_tbl).upsert(row, on_conflict="show_id").execute()
    return show_id


def upsert_setlist(
    client, band: str, show_id: str, rows: List[Dict], chunk_size: int = 500
) -> None:
    """Upsert setlist rows for a given show."""
    sets_tbl = f"{band}_setlists_raw"
    payload = []
    for r in rows:
        item = {
            "show_id": show_id,
            "set_number": r["set_number"],
            "song_position": r["song_position"],
            "song_name": r["song_name"],
        }
        if "is_segue" in r:
            item["is_segue"] = r["is_segue"]
        if "song_notes" in r:
            item["song_notes"] = r["song_notes"]
        payload.append(item)

    for i in range(0, len(payload), chunk_size):
        chunk = payload[i : i + chunk_size]
        client.table(sets_tbl).upsert(
            chunk, on_conflict="show_id,set_number,song_position"
        ).execute()


def add_setlist(
    band: str,
    show_date: str,
    venue_name: str,
    city: str,
    state: str,
    setlist_text: str,
) -> str:
    """Add a complete setlist (show + setlist rows) to the database.

    Returns the show_id of the created/updated show.
    """
    client = get_supabase_client()
    rows = parse_setlist_text(setlist_text)
    if not rows:
        raise ValueError("Parsed 0 setlist rows from text")

    show_id = ensure_show(client, band, show_date, venue_name, city, state)
    upsert_setlist(client, band, show_id, rows)
    return show_id
