"""Compatibility wrapper around the generic model comparison workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.compare_models import generate_report as generate_comparison_report
from src.jambandnerd.config.bands import get_active_bands


def load_legacy_reference() -> dict[str, float] | None:
    session_log = Path("session_logs/2026-03-27/50_show_backfill.md")
    if not session_log.exists():
        return None

    text = session_log.read_text()
    matches = re.findall(r"\|\s*(Notebook|CK\+|Deal)\s*\|\s*([0-9.]+)\s*\|", text)
    if not matches:
        return None

    return {
        label.lower().replace("+", "plus"): float(value) for label, value in matches
    }


def generate_report(band: str, shows: int) -> dict[str, Any]:
    window_label = f"last_{shows}"
    report = generate_comparison_report(
        candidate_model="deal",
        baseline_models=["ckplus", "notebook"],
        bands=[band],
        windows=[{"label": window_label, "shows": shows}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        include_candidate_diagnostics=True,
    )
    comparison_window = report["windows"][window_label]
    legacy_reference = load_legacy_reference()
    deal_summary = comparison_window["cross_band_summary"]["deal"]["metrics"]["k10"]
    ckplus_summary = comparison_window["cross_band_summary"]["ckplus"]["metrics"]["k10"]
    comparison_window["shows"] = int(
        comparison_window["metrics_by_band"][band]["deal"]["shows_evaluated"]
    )
    comparison_window["metrics"] = comparison_window["metrics_by_band"][band]
    comparison_window["deltas"]["deal_minus_legacy_reference"] = (
        None
        if legacy_reference is None or "deal" not in legacy_reference
        else deal_summary["hit_rate"] - legacy_reference["deal"]
    )
    comparison_window["deltas"]["deal_minus_ckplus"] = (
        deal_summary["hit_rate"] - ckplus_summary["hit_rate"]
    )
    comparison_window["deltas"]["deal_minus_notebook"] = (
        deal_summary["hit_rate"]
        - comparison_window["cross_band_summary"]["notebook"]["metrics"]["k10"][
            "hit_rate"
        ]
    )

    report["comparison_window"] = comparison_window
    report["promotion_gate"] = {
        **comparison_window["promotion_gate"],
        "enabled_for_web": False,
        "beats_legacy_deal_by_0_05": (
            False
            if legacy_reference is None or "deal" not in legacy_reference
            else deal_summary["hit_rate"] >= legacy_reference["deal"] + 0.05
        ),
        "matches_or_beats_ckplus": deal_summary["hit_rate"]
        >= ckplus_summary["hit_rate"],
    }
    report["legacy_reference"] = legacy_reference
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the Deal model and emit a JSON report."
    )
    parser.add_argument("--band", required=True, choices=get_active_bands())
    parser.add_argument("--shows", type=int, default=50)
    parser.add_argument("--output", help="Optional path to write the JSON report.")
    args = parser.parse_args()

    report = generate_report(args.band, args.shows)
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)

    if args.output:
        Path(args.output).write_text(output + "\n")


if __name__ == "__main__":
    main()
