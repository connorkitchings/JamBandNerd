"""Convenience wrapper to generate Billy Strings Notebook predictions."""

from __future__ import annotations

import argparse

from scripts.generate_predictions import generate_predictions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Billy Strings Notebook predictions."
    )
    parser.add_argument(
        "--date",
        help="Reference date in YYYY-MM-DD format. Defaults to next scheduled show.",
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=3,
        help="Number of most recent shows to exclude (default: 3).",
    )
    args = parser.parse_args()

    generate_predictions(
        band="billy",
        model="notebook",
        date_str=args.date,
        exclusion_window=args.exclusion_window,
    )


if __name__ == "__main__":
    main()
