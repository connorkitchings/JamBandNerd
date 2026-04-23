#!/usr/bin/env python3
"""Audit raw band data readiness before migration or derived-data rebuilds."""

from __future__ import annotations

import argparse
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.diagnose_band_data import diagnose_band
from src.jambandnerd.config.bands import get_repo_supported_bands


def audit_bands(bands: list[str], *, verbose: bool = False) -> int:
    """Audit one or more bands and return the number of bands with issues."""
    failing_bands = 0

    for band in bands:
        results = diagnose_band(band, verbose=verbose)
        if results["issues"]:
            failing_bands += 1

    print("=" * 60)
    print("Raw Data Audit Summary")
    print("=" * 60)
    print(f"Bands audited: {', '.join(bands)}")
    print(f"Bands with issues: {failing_bands}")
    print(f"Bands clean: {len(bands) - failing_bands}")
    print("=" * 60)

    return failing_bands


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit raw data readiness for one or more bands."
    )
    parser.add_argument(
        "--band",
        choices=[*get_repo_supported_bands(), "all"],
        default="all",
        help="Band to audit (default: all supported bands).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed issue output for each band.",
    )
    args = parser.parse_args()

    bands = list(get_repo_supported_bands()) if args.band == "all" else [args.band]
    failures = audit_bands(bands, verbose=args.verbose)
    if failures:
        raise SystemExit(f"Audit found issues in {failures} band(s)")


if __name__ == "__main__":
    main()
