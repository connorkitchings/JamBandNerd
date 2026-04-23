"""Export raw table snapshots for local historical backtest work."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import export_tables_to_snapshot
from src.jambandnerd.config.bands import get_repo_supported_bands


def parse_bands(raw_band: str) -> list[str]:
    """Parse a band selector into an ordered list of band slugs."""

    if raw_band == "all":
        return list(get_repo_supported_bands())

    requested = [band.strip() for band in raw_band.split(",") if band.strip()]
    valid = set(get_repo_supported_bands())
    invalid = [band for band in requested if band not in valid]
    if invalid:
        raise ValueError(f"Unknown band slug(s): {', '.join(sorted(invalid))}")
    return requested


def snapshot_tables_for_band(band: str) -> list[str]:
    """Return the raw tables required to backtest a single band locally."""

    tables = [
        f"{band}_shows_raw",
        f"{band}_setlists_raw",
    ]
    if band == "um":
        tables.append("um_upcoming_shows")
    return tables


def export_backtest_snapshots(
    *,
    bands: list[str],
    snapshot_root: str,
) -> dict[str, object]:
    """Export the raw-table snapshots required for the requested bands."""

    table_names: list[str] = []
    for band in bands:
        for table_name in snapshot_tables_for_band(band):
            if table_name not in table_names:
                table_names.append(table_name)

    return export_tables_to_snapshot(table_names, snapshot_root=snapshot_root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export raw table snapshots for local historical backtests."
    )
    parser.add_argument(
        "--band",
        default="all",
        help="Band slug, comma-separated list, or 'all' (default).",
    )
    parser.add_argument(
        "--snapshot-root",
        required=True,
        help="Directory where local snapshot JSON files should be written.",
    )
    args = parser.parse_args()

    bands = parse_bands(args.band)
    manifest = export_backtest_snapshots(
        bands=bands,
        snapshot_root=args.snapshot_root,
    )
    print(
        f"Exported snapshots for {len(bands)} band(s) to {Path(args.snapshot_root)} "
        f"({len(manifest.get('tables', {}))} table files)."
    )


if __name__ == "__main__":
    main()
