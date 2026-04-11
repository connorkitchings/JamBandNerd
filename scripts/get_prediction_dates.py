#!/usr/bin/env python3
"""
Gets the list of reference_date values for a band's prediction table.
Used by the backfill workflow to determine which dates to regenerate.
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


def get_prediction_dates(band: str, model: str, limit: int = 100) -> list[str]:
    """
    Returns a list of reference_date strings for a band's prediction table.
    """
    client = get_supabase_client()
    table_name = f"predictions_{model}"

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
            return []

        dates = pd.Series(
            [row["reference_date"] for row in resp.data if row.get("reference_date")]
        )
        unique_dates = dates.dropna().unique().tolist()
        return sorted(unique_dates, reverse=True)

    except Exception as e:
        print(f"Error fetching prediction dates: {e}", file=sys.stderr)
        return []


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
        help="The model name.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of dates to return.",
    )
    args = parser.parse_args()
    dates = get_prediction_dates(args.band, args.model, args.limit)
    print(json.dumps(dates))
