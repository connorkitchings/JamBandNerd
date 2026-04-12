#!/usr/bin/env python3
"""
Gets the list of reference_date values for a band's prediction table.
Used by the backfill workflow to determine which dates to regenerate.

With --missing-from MODEL, returns dates present in the source table but
absent from the --missing-from model's table. Useful for backfilling a new
model using dates that already exist for an older model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.registry import list_model_slugs


def _fetch_dates(client, table_name: str, band: str, limit: int) -> set[str]:
    """Fetch unique reference_date values for a band from a prediction table."""
    try:
        resp = (
            client.table(table_name)
            .select("reference_date")
            .eq("band", band)
            .order("reference_date", desc=True)
            .limit(limit)
            .execute()
        )
        if not resp.data:
            return set()
        return {
            row["reference_date"]
            for row in resp.data
            if row.get("reference_date")
        }
    except Exception as e:
        print(f"Error fetching dates from {table_name}: {e}", file=sys.stderr)
        return set()


def get_prediction_dates(
    band: str,
    model: str,
    limit: int = 100,
    missing_from: str | None = None,
) -> list[str]:
    """
    Returns a list of reference_date strings for a band's prediction table.

    If missing_from is provided, returns dates in the source model's table that
    are NOT present in the missing_from model's table (dates needing backfill).
    """
    client = get_supabase_client()
    source_table = f"predictions_{model}"

    source_dates = _fetch_dates(client, source_table, band, limit)
    if not source_dates:
        return []

    if missing_from:
        target_table = f"predictions_{missing_from}"
        existing_dates = _fetch_dates(client, target_table, band, limit * 10)
        source_dates -= existing_dates

    return sorted(source_dates, reverse=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Get prediction dates from a band's prediction table."
    )
    parser.add_argument(
        "--band",
        required=True,
        help="The band's slug.",
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=list_model_slugs(),
        help="The source model to pull dates from.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of dates to fetch from the source table.",
    )
    parser.add_argument(
        "--missing-from",
        dest="missing_from",
        choices=list_model_slugs(),
        default=None,
        help=(
            "If set, return only dates from --model that are absent in this model's "
            "table. Used to find dates that need backfilling."
        ),
    )
    args = parser.parse_args()
    dates = get_prediction_dates(args.band, args.model, args.limit, args.missing_from)
    print(json.dumps(dates))
