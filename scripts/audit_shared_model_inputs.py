"""Audit normalized model-input field availability across active bands."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data
from src.jambandnerd.config.bands import get_active_bands

SHOW_FIELD_CANDIDATES = ("venue_name", "city", "state", "country")


def _serialize_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def write_report_output(output_path: Path, report: dict[str, Any]) -> None:
    payload = _serialize_report(report)
    if not payload.strip():
        raise RuntimeError(f"Refusing to write an empty audit report to {output_path}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temp_path.write_text(payload + "\n")

    written_payload = temp_path.read_text()
    if not written_payload.strip():
        raise RuntimeError(f"Wrote an empty audit payload to {temp_path}.")
    try:
        json.loads(written_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Wrote invalid JSON while saving the audit report to {temp_path}."
        ) from exc

    temp_path.replace(output_path)
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError(
            f"Expected a non-empty audit artifact to exist at {output_path}."
        )


def _field_summary(df: pd.DataFrame, field_name: str) -> dict[str, Any]:
    if field_name not in df.columns:
        return {
            "present": False,
            "non_null_ratio": 0.0,
            "non_null_rows": 0,
            "total_rows": int(len(df)),
        }

    series = df[field_name]
    normalized = series.astype("string").str.strip()
    non_null_mask = normalized.notna() & normalized.ne("")
    non_null_rows = int(non_null_mask.sum())
    total_rows = int(len(df))
    ratio = float(non_null_rows / total_rows) if total_rows else 0.0
    return {
        "present": True,
        "non_null_ratio": ratio,
        "non_null_rows": non_null_rows,
        "total_rows": total_rows,
    }


def audit_bands(bands: list[str]) -> dict[str, Any]:
    per_band: dict[str, Any] = {}
    for band in bands:
        shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
        setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))
        if shows_df.empty or setlists_df.empty:
            per_band[band] = {"status": "missing_data"}
            continue

        prepared_shows, prepared_setlists = prepare_band_data(
            shows_df,
            setlists_df,
            band=band,
        )
        per_band[band] = {
            "status": "ok",
            "show_fields": {
                field_name: _field_summary(prepared_shows, field_name)
                for field_name in SHOW_FIELD_CANDIDATES
            },
            "row_counts": {
                "shows": int(len(prepared_shows)),
                "setlists": int(len(prepared_setlists)),
            },
        }

    universal_show_fields: dict[str, Any] = {}
    for field_name in SHOW_FIELD_CANDIDATES:
        summaries = [
            band_summary["show_fields"][field_name]
            for band_summary in per_band.values()
            if band_summary.get("status") == "ok"
        ]
        universal_show_fields[field_name] = {
            "present_in_all_bands": bool(summaries)
            and all(summary["present"] for summary in summaries),
            "min_non_null_ratio": (
                min(summary["non_null_ratio"] for summary in summaries)
                if summaries
                else 0.0
            ),
        }

    return {
        "bands": per_band,
        "universal_show_fields": universal_show_fields,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit normalized shared model-input field availability."
    )
    parser.add_argument(
        "--band",
        default="all",
        help="Band slug, comma-separated band slugs, or 'all' (default).",
    )
    parser.add_argument("--output", help="Optional path to write the JSON report.")
    args = parser.parse_args()

    bands = list(get_active_bands()) if args.band == "all" else args.band.split(",")
    report = audit_bands([band.strip() for band in bands if band.strip()])
    output = _serialize_report(report)
    if not output.strip():
        raise RuntimeError("Audit report generation produced an empty JSON payload.")

    if args.output:
        write_report_output(Path(args.output), report)

    print(output)
