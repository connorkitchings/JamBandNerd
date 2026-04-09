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

FOCUS_BANDS = ("goose", "phish", "billy")
NOTEBOOK_GAP_CLOSE_THRESHOLD = 0.005


def _load_report(path: Path) -> dict:
    return json.loads(path.read_text())


def _extract_model_metrics(
    report: dict, window: str, model_slug: str
) -> dict[str, float] | None:
    windows = report.get("windows", {})
    window_data = windows.get(window)
    if not window_data:
        return None
    cross = window_data.get("cross_band_summary", {})
    if model_slug not in cross:
        return None
    metrics = cross[model_slug].get("metrics", {})
    return {
        "recall_k10": metrics.get("k10", {}).get("recall", float("nan")),
        "recall_k25": metrics.get("k25", {}).get("recall", float("nan")),
        "recall_k50": metrics.get("k50", {}).get("recall", float("nan")),
        "hit_rate_k10": metrics.get("k10", {}).get("hit_rate", float("nan")),
        "bands_evaluated": cross[model_slug].get("bands_evaluated", 0),
        "shows_evaluated": cross[model_slug].get("shows_evaluated", 0),
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


def _get_overrides_dict(report: dict) -> dict:
    overrides = report.get("experiment_metadata", {}).get("candidate_overrides")
    return overrides if isinstance(overrides, dict) else {}


def _extract_band_recall(
    report: dict, window: str, band: str, model_slug: str, k: str
) -> float | None:
    metrics = (
        report.get("windows", {})
        .get(window, {})
        .get("metrics_by_band", {})
        .get(band, {})
        .get(model_slug, {})
        .get("metrics", {})
    )
    if k not in metrics:
        return None
    return metrics[k].get("recall")


def _count_focus_band_improvements(
    report: dict,
    baseline_report: dict | None,
    *,
    window: str,
    focus_bands: tuple[str, ...] = FOCUS_BANDS,
    threshold: float = NOTEBOOK_GAP_CLOSE_THRESHOLD,
) -> tuple[int, str]:
    if baseline_report is None:
        return 0, "—"

    improvements: list[str] = []
    wins = 0
    candidate_slug = report.get("candidate_model", {}).get("slug")
    baseline_slug = baseline_report.get("candidate_model", {}).get("slug")
    if not candidate_slug or not baseline_slug:
        return 0, "—"

    for band in focus_bands:
        baseline_candidate_k10 = _extract_band_recall(
            baseline_report, window, band, baseline_slug, "k10"
        )
        baseline_candidate_k25 = _extract_band_recall(
            baseline_report, window, band, baseline_slug, "k25"
        )
        baseline_notebook_k10 = _extract_band_recall(
            baseline_report, window, band, "notebook", "k10"
        )
        baseline_notebook_k25 = _extract_band_recall(
            baseline_report, window, band, "notebook", "k25"
        )
        candidate_k10 = _extract_band_recall(
            report, window, band, candidate_slug, "k10"
        )
        candidate_k25 = _extract_band_recall(
            report, window, band, candidate_slug, "k25"
        )
        notebook_k10 = _extract_band_recall(report, window, band, "notebook", "k10")
        notebook_k25 = _extract_band_recall(report, window, band, "notebook", "k25")
        values = [
            baseline_candidate_k10,
            baseline_candidate_k25,
            baseline_notebook_k10,
            baseline_notebook_k25,
            candidate_k10,
            candidate_k25,
            notebook_k10,
            notebook_k25,
        ]
        if any(value is None for value in values):
            continue

        baseline_gap_k10 = baseline_candidate_k10 - baseline_notebook_k10
        baseline_gap_k25 = baseline_candidate_k25 - baseline_notebook_k25
        candidate_gap_k10 = candidate_k10 - notebook_k10
        candidate_gap_k25 = candidate_k25 - notebook_k25
        close_delta_k10 = candidate_gap_k10 - baseline_gap_k10
        close_delta_k25 = candidate_gap_k25 - baseline_gap_k25
        if close_delta_k10 >= threshold or close_delta_k25 >= threshold:
            wins += 1
        improvements.append(f"{band}({close_delta_k10:+.4f}/{close_delta_k25:+.4f})")

    return wins, ", ".join(improvements) if improvements else "—"


def _categorize_label(label: str) -> str:
    if label.startswith("threshold_"):
        return "threshold"
    if label.startswith("recency_"):
        return "recency"
    if label.startswith("gap_") or label.startswith("freq_") or label == "no_venue":
        return "feature_subset"
    if label.startswith("reg_"):
        return "regularization"
    if label.startswith("weight_"):
        return "weighting"
    return "other"


def _merge_overrides(*rows: dict) -> dict:
    merged: dict = {}
    for row in rows:
        merged.update(row.get("overrides_dict", {}))
    return merged


def _pick_best_by_category(rows: list[dict], category: str) -> dict | None:
    candidates = [row for row in rows if row["category"] == category]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            row["qualifies_for_batch2"],
            row["delta_k10"],
            row["delta_k25"],
            row["focus_band_wins"],
        ),
    )


def _print_batch2_summary(rows: list[dict]) -> None:
    qualified = [row for row in rows if row["qualifies_for_batch2"]]
    if not qualified:
        print()
        print(
            "Batch 2: no single-factor ablation qualifies. Stop here and plan a "
            "feature-engineering pass."
        )
        return

    print()
    print("Batch 2 qualified winners:")
    for row in qualified[:3]:
        print(
            f"- {row['label']}: Δdeal@10={row['delta_k10']:+.4f}, "
            f"Δdeal@25={row['delta_k25']:+.4f}, "
            f"focus wins={row['focus_band_wins']}, "
            f"gapN@10={row['gap_to_notebook_k10']:+.4f}, "
            f"gapN@25={row['gap_to_notebook_k25']:+.4f}"
        )

    threshold = _pick_best_by_category(qualified, "threshold")
    weighting = _pick_best_by_category(qualified, "weighting")
    regularization = _pick_best_by_category(qualified, "regularization")
    recency = _pick_best_by_category(qualified, "recency")
    feature_subset = _pick_best_by_category(qualified, "feature_subset")

    suggestions: list[tuple[str, dict]] = []
    if threshold and weighting:
        suggestions.append(
            (
                f"{threshold['label']} + {weighting['label']}",
                _merge_overrides(threshold, weighting),
            )
        )
    if threshold and regularization:
        suggestions.append(
            (
                f"{threshold['label']} + {regularization['label']}",
                _merge_overrides(threshold, regularization),
            )
        )
    if threshold and recency:
        suggestions.append(
            (
                f"{threshold['label']} + {recency['label']}",
                _merge_overrides(threshold, recency),
            )
        )
    if threshold and feature_subset:
        suggestions.append(
            (
                f"{feature_subset['label']} + {threshold['label']}",
                _merge_overrides(feature_subset, threshold),
            )
        )

    if suggestions:
        print()
        print("Suggested Batch 2 combinations:")
        for label, overrides in suggestions:
            print(f"- {label}: {json.dumps(overrides, sort_keys=True)}")


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
    baseline_report: dict | None = None
    baseline_notebook_metrics: dict[str, float] | None = None
    if baseline_path.exists():
        baseline_report = _load_report(baseline_path)
        baseline_slug = baseline_report.get("candidate_model", {}).get("slug")
        if baseline_slug:
            baseline_metrics = _extract_model_metrics(
                baseline_report, args.window, baseline_slug
            )
        baseline_notebook_metrics = _extract_model_metrics(
            baseline_report, args.window, "notebook"
        )
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
        candidate_slug = report.get("candidate_model", {}).get("slug")
        if not candidate_slug:
            print(
                f"WARNING: missing candidate model slug in {report_file.name}",
                file=sys.stderr,
            )
            continue

        metrics = _extract_model_metrics(report, args.window, candidate_slug)
        notebook_metrics = _extract_model_metrics(report, args.window, "notebook")
        if metrics is None or notebook_metrics is None:
            print(
                f"WARNING: no {args.window} cross-band metrics in {report_file.name}",
                file=sys.stderr,
            )
            continue

        focus_band_wins, focus_band_notes = _count_focus_band_improvements(
            report, baseline_report, window=args.window
        )
        gap_to_notebook_k10 = metrics["recall_k10"] - notebook_metrics["recall_k10"]
        gap_to_notebook_k25 = metrics["recall_k25"] - notebook_metrics["recall_k25"]
        delta_k10 = (
            metrics["recall_k10"] - baseline_metrics["recall_k10"]
            if baseline_metrics
            else float("nan")
        )
        delta_k25 = (
            metrics["recall_k25"] - baseline_metrics["recall_k25"]
            if baseline_metrics
            else float("nan")
        )
        rows.append(
            {
                "file": report_file.stem,
                "label": _get_label(report),
                "overrides": _get_overrides(report),
                "overrides_dict": _get_overrides_dict(report),
                "status": status,
                "recall_k10": metrics["recall_k10"],
                "recall_k25": metrics["recall_k25"],
                "recall_k50": metrics["recall_k50"],
                "hit_rate_k10": metrics["hit_rate_k10"],
                "bands": metrics["bands_evaluated"],
                "shows": metrics["shows_evaluated"],
                "gate": _get_promotion_gate(report, args.window),
                "delta_k10": delta_k10,
                "delta_k25": delta_k25,
                "gap_to_notebook_k10": gap_to_notebook_k10,
                "gap_to_notebook_k25": gap_to_notebook_k25,
                "focus_band_wins": focus_band_wins,
                "focus_band_notes": focus_band_notes,
                "category": _categorize_label(_get_label(report)),
                "qualifies_for_batch2": (
                    delta_k10 > 0
                    and delta_k25 >= 0
                    and _get_promotion_gate(report, args.window)
                    and focus_band_wins >= 2
                ),
            }
        )

    if not rows:
        print("No complete results to display.")
        return

    rows.sort(
        key=lambda row: (
            row["qualifies_for_batch2"],
            row["delta_k10"],
            row["delta_k25"],
            row["focus_band_wins"],
            row["recall_k10"],
        ),
        reverse=True,
    )

    if baseline_metrics:
        print(
            f"Baseline (deal_v2, {args.window}): "
            f"recall@10={baseline_metrics['recall_k10']:.4f}  "
            f"recall@25={baseline_metrics['recall_k25']:.4f}  "
            f"recall@50={baseline_metrics['recall_k50']:.4f}"
        )
        if baseline_notebook_metrics:
            print(
                f"Notebook anchor ({args.window}): "
                f"recall@10={baseline_notebook_metrics['recall_k10']:.4f}  "
                f"recall@25={baseline_notebook_metrics['recall_k25']:.4f}"
            )
        print()

    header = (
        "| label | overrides | recall@10 | Δdeal@10 | gapN@10 | recall@25 | "
        "Δdeal@25 | gapN@25 | focus wins | batch2 | gate | status |"
    )
    sep = (
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | "
        ":---: | --- |"
    )
    print(header)
    print(sep)
    for row in rows:
        delta_k10 = f"{row['delta_k10']:+.4f}" if not _is_nan(row["delta_k10"]) else "—"
        delta_k25 = f"{row['delta_k25']:+.4f}" if not _is_nan(row["delta_k25"]) else "—"
        gate_icon = "✓" if row["gate"] else "✗"
        batch2_icon = "✓" if row["qualifies_for_batch2"] else "✗"
        print(
            f"| {row['label']} | {row['overrides']} "
            f"| {row['recall_k10']:.4f} | {delta_k10} "
            f"| {row['gap_to_notebook_k10']:+.4f} "
            f"| {row['recall_k25']:.4f} | {delta_k25} "
            f"| {row['gap_to_notebook_k25']:+.4f} "
            f"| {row['focus_band_wins']} "
            f"| {batch2_icon} | {gate_icon} | {row['status']} |"
        )

    print()
    print(
        "Focus-band notebook-gap deltas use "
        f"{NOTEBOOK_GAP_CLOSE_THRESHOLD:.3f} as the material-close threshold."
    )
    for row in rows:
        print(f"- {row['label']}: {row['focus_band_notes']}")

    _print_batch2_summary(rows)


def _is_nan(value: float) -> bool:
    return value != value


if __name__ == "__main__":
    main()
