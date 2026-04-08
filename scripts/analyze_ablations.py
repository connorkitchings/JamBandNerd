"""Summarize ablation experiment results as a markdown comparison table.

Usage:
    uv run python scripts/analyze_ablations.py \\
        --batch-dir docs/reports/model_baselines/ablations/batch1 \\
        [--baseline docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json] \\
        [--window last_50]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_report(path: Path) -> dict:
    return json.loads(path.read_text())


def _extract_cross_band_metrics(report: dict, window: str) -> dict[str, float] | None:
    windows = report.get("windows", {})
    window_data = windows.get(window)
    if not window_data:
        return None
    cross = window_data.get("cross_band_summary", {})
    candidate_slug = report.get("candidate_model", {}).get("slug")
    if not candidate_slug or candidate_slug not in cross:
        return None
    metrics = cross[candidate_slug].get("metrics", {})
    return {
        "recall_k10": metrics.get("k10", {}).get("recall", float("nan")),
        "recall_k25": metrics.get("k25", {}).get("recall", float("nan")),
        "recall_k50": metrics.get("k50", {}).get("recall", float("nan")),
        "hit_rate_k10": metrics.get("k10", {}).get("hit_rate", float("nan")),
        "bands_evaluated": cross[candidate_slug].get("bands_evaluated", 0),
        "shows_evaluated": cross[candidate_slug].get("shows_evaluated", 0),
    }


def _get_promotion_gate(report: dict, window: str) -> bool:
    return (
        report.get("windows", {})
        .get(window, {})
        .get("promotion_gate", {})
        .get("passes", False)
    )


def _get_label(report: dict) -> str:
    return report.get("experiment_metadata", {}).get("feature_set_label", "unknown")


def _get_overrides(report: dict) -> str:
    overrides = report.get("experiment_metadata", {}).get("candidate_overrides")
    if not overrides:
        return "(none)"
    return ", ".join(f"{k}={v}" for k, v in sorted(overrides.items()))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a markdown comparison table for a batch of ablation reports."
    )
    parser.add_argument(
        "--batch-dir",
        required=True,
        help="Directory containing ablation JSON report files.",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help=(
            "Path to the canonical baseline JSON report to compute deltas against. "
            "Defaults to docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json."
        ),
    )
    parser.add_argument(
        "--window",
        default="last_50",
        help="Evaluation window label to compare (default: last_50).",
    )
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    if not batch_dir.is_dir():
        print(f"ERROR: batch directory not found: {batch_dir}", file=sys.stderr)
        sys.exit(1)

    baseline_path = Path(
        args.baseline
        or "docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json"
    )

    baseline_metrics: dict[str, float] | None = None
    if baseline_path.exists():
        baseline_report = _load_report(baseline_path)
        baseline_metrics = _extract_cross_band_metrics(baseline_report, args.window)
    else:
        print(
            f"WARNING: baseline not found at {baseline_path} — deltas will be omitted.",
            file=sys.stderr,
        )

    report_files = sorted(batch_dir.glob("*.json"))
    if not report_files:
        print(f"No JSON files found in {batch_dir}.", file=sys.stderr)
        sys.exit(0)

    rows: list[dict] = []
    for report_file in report_files:
        try:
            report = _load_report(report_file)
        except Exception as exc:
            print(f"WARNING: skipping {report_file.name}: {exc}", file=sys.stderr)
            continue

        status = report.get("report_status", "unknown")
        metrics = _extract_cross_band_metrics(report, args.window)
        if metrics is None:
            print(
                f"WARNING: no {args.window} cross-band metrics in {report_file.name}",
                file=sys.stderr,
            )
            continue

        rows.append(
            {
                "file": report_file.stem,
                "label": _get_label(report),
                "overrides": _get_overrides(report),
                "status": status,
                "recall_k10": metrics["recall_k10"],
                "recall_k25": metrics["recall_k25"],
                "recall_k50": metrics["recall_k50"],
                "hit_rate_k10": metrics["hit_rate_k10"],
                "bands": metrics["bands_evaluated"],
                "shows": metrics["shows_evaluated"],
                "gate": _get_promotion_gate(report, args.window),
                "delta_k10": (
                    metrics["recall_k10"] - baseline_metrics["recall_k10"]
                    if baseline_metrics
                    else float("nan")
                ),
                "delta_k25": (
                    metrics["recall_k25"] - baseline_metrics["recall_k25"]
                    if baseline_metrics
                    else float("nan")
                ),
            }
        )

    if not rows:
        print("No complete results to display.")
        return

    rows.sort(key=lambda r: r["recall_k10"], reverse=True)

    if baseline_metrics:
        print(
            f"Baseline (deal_v2, {args.window}): "
            f"recall@10={baseline_metrics['recall_k10']:.4f}  "
            f"recall@25={baseline_metrics['recall_k25']:.4f}  "
            f"recall@50={baseline_metrics['recall_k50']:.4f}"
        )
        print()

    header = (
        "| label | overrides | recall@10 | Δ@10 | recall@25 | Δ@25 | "
        "recall@50 | hit@10 | gate | bands | status |"
    )
    sep = "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | ---: | --- |"
    print(header)
    print(sep)
    for row in rows:
        delta_k10 = f"{row['delta_k10']:+.4f}" if not _is_nan(row["delta_k10"]) else "—"
        delta_k25 = f"{row['delta_k25']:+.4f}" if not _is_nan(row["delta_k25"]) else "—"
        gate_icon = "✓" if row["gate"] else "✗"
        print(
            f"| {row['label']} | {row['overrides']} "
            f"| {row['recall_k10']:.4f} | {delta_k10} "
            f"| {row['recall_k25']:.4f} | {delta_k25} "
            f"| {row['recall_k50']:.4f} "
            f"| {row['hit_rate_k10']:.4f} "
            f"| {gate_icon} | {row['bands']} | {row['status']} |"
        )


def _is_nan(value: float) -> bool:
    return value != value


if __name__ == "__main__":
    main()
