#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path to allow src imports
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Import from shared module
from src.jambandnerd.utils.setlist_parser import (
    add_setlist,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Admin tool to add a manual setlist to raw tables."
    )
    parser.add_argument("--band", choices=["wsp", "goose", "phish"], required=True)
    parser.add_argument("--date", required=True, help="Show date YYYY-MM-DD")
    parser.add_argument("--venue", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument(
        "--file", required=True, help="Path to a text file containing the setlist lines"
    )

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
    show_id = add_setlist(
        args.band, args.date, args.venue, args.city, args.state, setlist_text
    )

    print(
        f"OK - inserted/updated setlist for {args.band} {args.date} (show_id={show_id})"
    )


if __name__ == "__main__":
    main()
