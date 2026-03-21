#!/usr/bin/env python3
"""Quick debug script to check recent_avg_gap in predictions."""

from __future__ import annotations

import argparse
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from supabase import create_client


def check_recent_avg_gap(band: str, model: str, date: str) -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    client = create_client(url, key)
    table = f"predictions_{model}"

    resp = (
        client.table(table)
        .select("predictions")
        .eq("band", band)
        .eq("reference_date", date)
        .limit(1)
        .execute()
    )

    if not resp.data:
        print(f"No predictions found for {band}/{model} on {date}")
        return

    preds = resp.data[0]["predictions"]
    for p in preds[:3]:
        print(
            f"  rank={p.get('rank')}: {p.get('song_name')} "
            f"recent_avg_gap={p.get('recent_avg_gap')}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--band", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    check_recent_avg_gap(args.band, args.model, args.date)
