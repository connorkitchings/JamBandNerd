#!/usr/bin/env python3
"""Quick debug script to check prediction payload fields for a band's next show."""

from __future__ import annotations

import argparse
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.config import SETLIST_PREDICTIONS_TABLE
from supabase import create_client


def check_prediction_payload(band: str, date: str) -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    client = create_client(url, key)

    resp = (
        client.table(SETLIST_PREDICTIONS_TABLE)
        .select("target_show_date, reference_date, model_version, predictions")
        .eq("band", band)
        .order("target_show_date", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        print(f"No predictions found for {band}")
        return

    row = resp.data[0]
    print(f"Band: {band}")
    print(f"Target show date: {row.get('target_show_date')}")
    print(f"Reference date: {row.get('reference_date')}")
    print(f"Model version: {row.get('model_version')}")
    print()

    preds = row.get("predictions", [])
    if isinstance(preds, str):
        import json

        preds = json.loads(preds)

    print(f"Top {min(10, len(preds))} predictions:")
    for p in preds[:10]:
        print(
            f"  rank={p.get('rank')}: {p.get('song_name')} "
            f"prob={p.get('probability'):.3f} "
            f"gap={p.get('current_gap')} "
            f"recent_plays_50={p.get('recent_plays_50')} "
            f"LTP={p.get('LTP')}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--band", required=True)
    parser.add_argument("--date", help="Optional target show date (YYYY-MM-DD)")
    args = parser.parse_args()
    check_prediction_payload(args.band, args.date or "")
