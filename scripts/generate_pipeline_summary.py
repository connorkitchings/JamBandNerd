#!/usr/bin/env python3
"""Generate the daily pipeline monitoring summary for GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from typing import Iterable

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import (
    completed_show_window,
    fetch_column_values_for_ids,
    fetch_table_rows,
)
from scripts.get_all_bands import get_bands
from src.jambandnerd.config import BAND_ID_COLUMNS
from src.jambandnerd.db.connection import get_supabase_client


def _parse_bands(*, bands_json: str | None, bands: list[str] | None) -> list[str]:
    if bands_json:
        parsed = json.loads(bands_json)
        if not isinstance(parsed, list) or not all(
            isinstance(item, str) for item in parsed
        ):
            raise ValueError("--bands-json must decode to a JSON string array")
        return parsed
    if bands:
        return bands
    return get_bands()


def _completed_show_end_date(*, today: date | None = None) -> str:
    today = today or date.today()
    return (today - timedelta(days=1)).isoformat()


def _latest_completed_show_with_setlist(
    client, *, band: str, today: date | None = None
):
    id_col = BAND_ID_COLUMNS.get(band, "show_id")
    rows = fetch_table_rows(
        f"{band}_shows_raw",
        select=f"{id_col}, show_date",
        filters=[("lte", "show_date", _completed_show_end_date(today=today))],
        order_by=[("show_date", True)],
        limit=50,
        client=client,
    )
    for row in rows:
        show_id = row.get(id_col)
        if show_id is None:
            continue
        setlist_ids = fetch_column_values_for_ids(
            f"{band}_setlists_raw",
            id_column=id_col,
            ids=[show_id],
            client=client,
        )
        if setlist_ids:
            return row
    return None


def build_data_quality_lines(
    client, *, bands: Iterable[str], days: int = 7, today: date | None = None
) -> list[str]:
    cutoff, end_date = completed_show_window(today=today, days=days)
    lines = ["### Data Quality Check", ""]

    for band in bands:
        id_col = BAND_ID_COLUMNS.get(band, "show_id")
        lines.append(f"**{band.upper()}**:")
        try:
            shows_rows = fetch_table_rows(
                f"{band}_shows_raw",
                filters=[("gte", "show_date", cutoff), ("lte", "show_date", end_date)],
                client=client,
            )
            if not shows_rows:
                lines.append(
                    f"- ℹ️ No recent completed shows found from {cutoff} through {end_date}"
                )
                lines.append("")
                continue

            show_ids_raw = [
                row.get(id_col) for row in shows_rows if row.get(id_col) is not None
            ]
            show_ids = {str(show_id) for show_id in show_ids_raw}
            setlist_ids = fetch_column_values_for_ids(
                f"{band}_setlists_raw",
                id_column=id_col,
                ids=show_ids_raw,
                client=client,
            )
            missing_count = len(show_ids - setlist_ids)

            if missing_count:
                lines.append(
                    f"- ⚠️ {missing_count} recent completed shows are missing setlist data"
                )
            else:
                lines.append("- ✅ All recent completed shows have setlist data")
            lines.append(f"- Window: {cutoff} through {end_date}")
            lines.append(f"- Total completed shows: {len(show_ids)}")
        except Exception as exc:
            lines.append(f"- ❌ Error checking data: {exc}")
        lines.append("")

    return lines


def build_prediction_coverage_lines(
    client, *, bands: Iterable[str], today: date | None = None
) -> list[str]:
    lines = [
        "### Prediction Coverage",
        "",
        "| Band | Notebook Top-50 Hits | Songs Played | Reference Date |",
        "| --- | --- | --- | --- |",
    ]

    for band in bands:
        id_col = BAND_ID_COLUMNS.get(band, "show_id")
        try:
            latest_show = _latest_completed_show_with_setlist(
                client, band=band, today=today
            )
            if not latest_show:
                lines.append(
                    f"| {band.upper()} | n/a | n/a | No completed shows with setlists |"
                )
                continue

            show_id = latest_show.get(id_col)
            reference_date = latest_show.get("show_date", "n/a")
            setlist_rows = fetch_table_rows(
                f"{band}_setlists_raw",
                select="song_name",
                filters=[("eq", id_col, show_id)],
                client=client,
            )
            actual_songs = {
                str(row.get("song_name"))
                for row in setlist_rows
                if row.get("song_name")
            }

            prediction_rows = (
                client.table("predictions_notebook")
                .select("predictions")
                .eq("band", band)
                .eq("reference_date", reference_date)
                .order("predicted_at", desc=True)
                .limit(1)
                .execute()
                .data
                or []
            )
            if not prediction_rows:
                lines.append(
                    f"| {band.upper()} | No predictions | {len(actual_songs)} | {reference_date} |"
                )
                continue

            predictions_payload = prediction_rows[0].get("predictions")
            predictions = (
                json.loads(predictions_payload)
                if isinstance(predictions_payload, str)
                else predictions_payload
            ) or []
            top_hits = sum(
                1
                for entry in predictions[:50]
                if entry.get("song_name") in actual_songs
            )
            lines.append(
                f"| {band.upper()} | {top_hits}/{len(actual_songs)} | {len(actual_songs)} | {reference_date} |"
            )
        except Exception as exc:
            lines.append(
                f"| {band.upper()} | Error | n/a | {str(exc).replace('|', '/')} |"
            )

    return lines


def render_summary(
    client,
    *,
    bands: Iterable[str],
    days: int = 7,
    output: str = "markdown",
    today: date | None = None,
) -> str:
    bands = list(bands)
    sections = [
        build_data_quality_lines(client, bands=bands, days=days, today=today),
        build_prediction_coverage_lines(client, bands=bands, today=today),
    ]

    if output == "markdown":
        return "\n".join(line for section in sections for line in section)
    if output == "text":
        text_lines: list[str] = []
        for section in sections:
            text_lines.extend(section)
            text_lines.append("")
        return "\n".join(text_lines).strip()
    raise ValueError(f"Unsupported output format: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the daily pipeline monitoring summary"
    )
    parser.add_argument(
        "--bands-json",
        help="JSON array of band slugs, intended for GitHub Actions usage.",
    )
    parser.add_argument(
        "--band",
        dest="bands",
        action="append",
        help="Band to include (repeat for multiple). Defaults to all discovered bands.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Completed-show freshness window in days.",
    )
    parser.add_argument(
        "--output",
        choices=["markdown", "text"],
        default="markdown",
        help="Render format for the summary body.",
    )
    args = parser.parse_args()

    bands = _parse_bands(bands_json=args.bands_json, bands=args.bands)
    client = get_supabase_client()
    print(render_summary(client, bands=bands, days=args.days, output=args.output))


if __name__ == "__main__":
    main()
