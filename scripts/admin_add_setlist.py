#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import List, Dict

import pandas as pd

# Import DB client from the project
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

    import re

    for line in lines:
        set_number = None
        encore = False
        songs_part = None

        m = re.match(r"^Set\s*(\d+)\s+(.*)$", line, flags=re.IGNORECASE)
        if m:
            set_number = int(m.group(1))
            songs_part = m.group(2)
        else:
            m2 = re.match(r"^Encore\s+(.*)$", line, flags=re.IGNORECASE)
            if m2:
                set_number = 99
                encore = True
                songs_part = m2.group(1)

        if set_number is None or songs_part is None:
            # skip lines that don't match the expected patterns
            continue

        # Split by commas into items; within each item, '>' denotes segues
        items = [s.strip() for s in songs_part.split(',') if s.strip()]
        pos = 1
        for item in items:
            parts = [p.strip() for p in item.split('>') if p.strip()]
            for i, part in enumerate(parts):
                song_name = (
                    part.replace("\u2019", "'")  # normalize curly apostrophes
                        .replace("\u2018", "'")
                        .strip()
                )
                rows.append({
                    "set_number": set_number,
                    "song_position": pos,
                    "song_name": song_name,
                    "is_segue": i < (len(parts) - 1),
                    "song_notes": "",
                })
                pos += 1

    return rows


def ensure_show(client, band: str, show_date: str, venue_name: str, city: str, state: str) -> str:
    """Ensure a show exists in {band}_shows_raw, return show_id.

    Strategy: if a show with this date+venue exists, reuse it; otherwise, generate a
    deterministic show_id hash from date|venue and upsert a new row.
    """
    shows_tbl = f"{band}_shows_raw"

    # Try to find an existing show by show_date and venue_name
    try:
        resp = (
            client.table(shows_tbl)
            .select("*")
            .eq("show_date", show_date)
            .eq("venue_name", venue_name)
            .limit(1)
            .execute()
        )
        if resp.data:
            return str(resp.data[0]["show_id"])  # type: ignore[index]
    except Exception:
        pass

    # Create deterministic show_id from date|venue
    show_id = str(int(hashlib.md5(f"{show_date}|{venue_name}".encode()).hexdigest()[:8], 16))

    row = {
        "show_id": show_id,
        "show_date": show_date,
        "venue_name": venue_name,
        "city": city,
        "state": state,
        "source_hash": None,
    }
    client.table(shows_tbl).upsert(row, on_conflict="show_id").execute()
    return show_id


def upsert_setlist(client, band: str, show_id: str, rows: List[Dict]) -> None:
    sets_tbl = f"{band}_setlists_raw"
    # Attach show_id and upsert in chunks
    payload = []
    for r in rows:
        item = {
            "show_id": show_id,
            "set_number": r["set_number"],
            "song_position": r["song_position"],
            "song_name": r["song_name"],
        }
        # Include optional fields if table has them; harmless if extra
        if "is_segue" in r:
            item["is_segue"] = r["is_segue"]
        if "song_notes" in r:
            item["song_notes"] = r["song_notes"]
        payload.append(item)

    # Chunked upsert
    for i in range(0, len(payload), 500):
        chunk = payload[i : i + 500]
        client.table(sets_tbl).upsert(chunk, on_conflict="show_id,set_number,song_position").execute()


def main() -> None:
    parser = argparse.ArgumentParser(description="Admin tool to add a manual setlist to raw tables.")
    parser.add_argument("--band", choices=["wsp", "goose", "phish"], required=True)
    parser.add_argument("--date", required=True, help="Show date YYYY-MM-DD")
    parser.add_argument("--venue", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--file", required=True, help="Path to a text file containing the setlist lines")

    args = parser.parse_args()

    # For now, we implement robust raw-table upserts for WSP only; Goose/Phish could be extended.
    if args.band != "wsp":
        print("This tool currently supports manual inserts for WSP only.")
        sys.exit(1)

    setlist_path = Path(args.file)
    if not setlist_path.exists():
        print(f"Setlist file not found: {setlist_path}")
        sys.exit(1)

    setlist_text = setlist_path.read_text(encoding="utf-8")
    rows = parse_setlist_text(setlist_text)
    if not rows:
        print("Parsed 0 setlist rows from the file; aborting.")
        sys.exit(1)

    client = get_supabase_client()
    show_id = ensure_show(client, args.band, args.date, args.venue, args.city, args.state)
    upsert_setlist(client, args.band, show_id, rows)

    print(f"OK - inserted/updated {len(rows)} rows for {args.band} {args.date} (show_id={show_id})")


if __name__ == "__main__":
    main()