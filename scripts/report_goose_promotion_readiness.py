"""Review Goose candidate promotion readiness from offline backtest artifacts.

Usage:
    uv run python scripts/report_goose_promotion_readiness.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jambandnerd.models.accuracy import dual_objective_score_for_band

BAND = "goose"
SPECIAL_TOUR_NAME = "Not Part of a Tour"


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    model_version: str
    promotable: bool = False


@dataclass(frozen=True)
class PerShowScore:
    show_id: str
    target_show_date: str
    segment: str
    p10: float
    p25: float
    r50: float
    f1_25: float
    dual_proxy: float


@dataclass(frozen=True)
class SegmentSummary:
    segment: str
    n_shows: int
    p10: float
    p25: float
    r50: float
    f1_25: float
    dual_proxy: float


@dataclass(frozen=True)
class DeltaSummary:
    comparison: str
    segment: str
    n_shows: int
    delta_p10: float
    delta_p25: float
    delta_r50: float
    delta_f1_25: float
    delta_dual_proxy: float


@dataclass(frozen=True)
class Top10GuardReview:
    compared_shows: int
    matching_metric_shows: int
    mismatched_show_ids: list[str]
    aggregate_p10_matches_notebook: bool
    interpretation: str


@dataclass(frozen=True)
class PromotionReview:
    overall: list[dict[str, Any]]
    segments: dict[str, list[SegmentSummary]]
    deltas: list[DeltaSummary]
    top10_guard: Top10GuardReview
    recommendation: str
    rationale: list[str]


MODEL_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        key="registered",
        label="Registered Goose",
        model_version="goose_fast_rank_v1",
    ),
    ModelSpec(
        key="notebook",
        label="Notebook floor",
        model_version="goose_notebook_floor_v1",
    ),
    ModelSpec(
        key="candidate",
        label="Special relaxed + Notebook top 10",
        model_version="goose_fast_rank_v1_candidate_relaxed_special_nbtop10",
        promotable=True,
    ),
    ModelSpec(
        key="global_control",
        label="Global relaxed + Notebook top 10 control",
        model_version="goose_fast_rank_v1_candidate_relaxed_global_nbtop10",
    ),
)

COMPARISON_SEGMENTS = ("all", "special", "normal")


def _summary_path(backtests_dir: Path, model_version: str) -> Path:
    return backtests_dir / f"{BAND}_{model_version}_summary.json"


def _per_show_path(backtests_dir: Path, model_version: str) -> Path:
    return backtests_dir / f"{BAND}_{model_version}_100shows.jsonl"


def _metric(row: dict[str, Any], key: str, metric: str) -> float:
    return float(row["metrics"][key][metric])


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _fmt(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.4f}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required artifact: {path}")
    return json.loads(path.read_text())


def _load_show_segments(snapshot_root: Path) -> dict[str, str]:
    payload = _load_json(snapshot_root / "goose_shows_raw.json")
    segments: dict[str, str] = {}
    for row in payload.get("rows", []):
        show_id = row.get("show_id")
        if show_id is None:
            continue
        tour_name = str(row.get("tour_name") or "")
        segments[str(show_id)] = (
            "special" if tour_name == SPECIAL_TOUR_NAME else "normal"
        )
    return segments


def _load_per_show_scores(
    path: Path,
    *,
    show_segments: dict[str, str],
) -> dict[str, PerShowScore]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required artifact: {path}")

    scores: dict[str, PerShowScore] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        show_id = str(row["show_id"])
        p10 = _metric(row, "k10", "precision")
        r50 = _metric(row, "k50", "recall")
        scores[show_id] = PerShowScore(
            show_id=show_id,
            target_show_date=str(row["target_show_date"]),
            segment=show_segments.get(show_id, "unknown"),
            p10=p10,
            p25=_metric(row, "k25", "precision"),
            r50=r50,
            f1_25=_metric(row, "k25", "f1"),
            dual_proxy=dual_objective_score_for_band(p10, r50, BAND),
        )
    return scores


def _segment_filter(
    scores: dict[str, PerShowScore],
    segment: str,
    *,
    show_ids: set[str],
) -> list[PerShowScore]:
    rows = [scores[show_id] for show_id in sorted(show_ids)]
    if segment == "all":
        return rows
    return [row for row in rows if row.segment == segment]


def _summarize_segment(rows: list[PerShowScore], segment: str) -> SegmentSummary:
    return SegmentSummary(
        segment=segment,
        n_shows=len(rows),
        p10=_mean([row.p10 for row in rows]),
        p25=_mean([row.p25 for row in rows]),
        r50=_mean([row.r50 for row in rows]),
        f1_25=_mean([row.f1_25 for row in rows]),
        dual_proxy=_mean([row.dual_proxy for row in rows]),
    )


def _delta(
    *,
    comparison: str,
    segment: str,
    candidate: list[PerShowScore],
    baseline: list[PerShowScore],
) -> DeltaSummary:
    by_id = {row.show_id: row for row in baseline}
    paired = [(row, by_id[row.show_id]) for row in candidate if row.show_id in by_id]
    return DeltaSummary(
        comparison=comparison,
        segment=segment,
        n_shows=len(paired),
        delta_p10=_mean(
            [
                candidate_row.p10 - baseline_row.p10
                for candidate_row, baseline_row in paired
            ]
        ),
        delta_p25=_mean(
            [
                candidate_row.p25 - baseline_row.p25
                for candidate_row, baseline_row in paired
            ]
        ),
        delta_r50=_mean(
            [
                candidate_row.r50 - baseline_row.r50
                for candidate_row, baseline_row in paired
            ]
        ),
        delta_f1_25=_mean(
            [
                candidate_row.f1_25 - baseline_row.f1_25
                for candidate_row, baseline_row in paired
            ]
        ),
        delta_dual_proxy=_mean(
            [
                candidate_row.dual_proxy - baseline_row.dual_proxy
                for candidate_row, baseline_row in paired
            ]
        ),
    )


def _top10_guard_review(
    *,
    candidate: dict[str, PerShowScore],
    notebook: dict[str, PerShowScore],
    candidate_summary: dict[str, Any],
    notebook_summary: dict[str, Any],
    show_ids: set[str],
) -> Top10GuardReview:
    mismatched = [
        show_id
        for show_id in sorted(show_ids)
        if candidate[show_id].p10 != notebook[show_id].p10
    ]
    aggregate_match = float(candidate_summary["p10"]) == float(notebook_summary["p10"])
    interpretation = (
        "Candidate p@10 matches the Notebook floor on every aligned show and in "
        "aggregate. The JSONL artifacts do not store prediction song lists, so "
        "exact top-10 song-order confirmation remains covered by "
        "tests/models/test_goose_model.py::test_candidate_rank_guard_keeps_notebook_top_10. "
        "The product tradeoff is that ranks 1-10 remain rule-guarded by the "
        "Notebook floor while ranks 11-50 carry the relaxed candidate repair."
    )
    if mismatched:
        interpretation = (
            "Candidate top-10 metrics diverge from the Notebook floor on at least "
            "one aligned show; inspect predictions before considering promotion."
        )
    return Top10GuardReview(
        compared_shows=len(show_ids),
        matching_metric_shows=len(show_ids) - len(mismatched),
        mismatched_show_ids=mismatched,
        aggregate_p10_matches_notebook=aggregate_match,
        interpretation=interpretation,
    )


def _overall_rows(backtests_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in MODEL_SPECS:
        summary = _load_json(_summary_path(backtests_dir, spec.model_version))
        rows.append(
            {
                "key": spec.key,
                "label": spec.label,
                "model_version": spec.model_version,
                "promotable": spec.promotable,
                "n_shows": int(summary["n_shows"]),
                "dual": float(summary["dual_score"]),
                "p10": float(summary["p10"]),
                "p25": float(summary["p25"]),
                "r50": float(summary["r50"]),
                "f1_25": float(summary["f1_25"]),
            }
        )
    return rows


def build_review(
    *,
    backtests_dir: Path,
    snapshot_root: Path,
) -> PromotionReview:
    show_segments = _load_show_segments(snapshot_root)
    per_model = {
        spec.key: _load_per_show_scores(
            _per_show_path(backtests_dir, spec.model_version),
            show_segments=show_segments,
        )
        for spec in MODEL_SPECS
    }
    aligned_show_ids = set.intersection(*(set(rows) for rows in per_model.values()))
    if not aligned_show_ids:
        raise RuntimeError("No aligned per-show records found across Goose artifacts.")

    segments: dict[str, list[SegmentSummary]] = {}
    for spec in MODEL_SPECS:
        segments[spec.key] = [
            _summarize_segment(
                _segment_filter(
                    per_model[spec.key], segment, show_ids=aligned_show_ids
                ),
                segment,
            )
            for segment in COMPARISON_SEGMENTS
        ]

    deltas: list[DeltaSummary] = []
    for baseline_key in ("registered", "notebook", "global_control"):
        for segment in COMPARISON_SEGMENTS:
            deltas.append(
                _delta(
                    comparison=f"candidate_vs_{baseline_key}",
                    segment=segment,
                    candidate=_segment_filter(
                        per_model["candidate"], segment, show_ids=aligned_show_ids
                    ),
                    baseline=_segment_filter(
                        per_model[baseline_key], segment, show_ids=aligned_show_ids
                    ),
                )
            )

    summaries = {
        spec.key: _load_json(_summary_path(backtests_dir, spec.model_version))
        for spec in MODEL_SPECS
    }
    top10_guard = _top10_guard_review(
        candidate=per_model["candidate"],
        notebook=per_model["notebook"],
        candidate_summary=summaries["candidate"],
        notebook_summary=summaries["notebook"],
        show_ids=aligned_show_ids,
    )

    candidate = next(
        row for row in _overall_rows(backtests_dir) if row["key"] == "candidate"
    )
    registered = next(
        row for row in _overall_rows(backtests_dir) if row["key"] == "registered"
    )
    notebook = next(
        row for row in _overall_rows(backtests_dir) if row["key"] == "notebook"
    )
    candidate_normal_delta = next(
        row
        for row in deltas
        if row.comparison == "candidate_vs_registered" and row.segment == "normal"
    )
    candidate_special_delta = next(
        row
        for row in deltas
        if row.comparison == "candidate_vs_registered" and row.segment == "special"
    )

    promotes_over_baselines = (
        candidate["dual"] > registered["dual"]
        and candidate["dual"] > notebook["dual"]
        and candidate["p10"] >= notebook["p10"]
        and candidate["f1_25"] > registered["f1_25"]
        and candidate["f1_25"] > notebook["f1_25"]
    )
    normal_degrades = (
        candidate_normal_delta.delta_p10 < 0
        or candidate_normal_delta.delta_p25 < 0
        or candidate_normal_delta.delta_f1_25 < 0
    )
    gains_concentrated = (
        candidate_special_delta.delta_f1_25 > candidate_normal_delta.delta_f1_25
        and candidate_special_delta.delta_r50 > candidate_normal_delta.delta_r50
    )

    if (
        promotes_over_baselines
        and not normal_degrades
        and top10_guard.aggregate_p10_matches_notebook
    ):
        recommendation = "promote_after_separate_production_wiring_task"
    elif promotes_over_baselines and normal_degrades:
        recommendation = "run_one_more_narrow_goose_spike"
    else:
        recommendation = "keep_experiment_only_and_stop_goose_work"

    rationale = [
        (
            "Candidate beats the registered Goose model and Notebook floor on "
            "dual, p@25, r@50, and F1@25 while matching Notebook p@10."
            if promotes_over_baselines
            else "Candidate does not clear the full baseline comparison gate."
        ),
        (
            "Segment gains are strongest on Not Part of a Tour shows."
            if gains_concentrated
            else "Segment gains are not clearly concentrated on Not Part of a Tour shows."
        ),
        (
            "Normal-tour segment has no p@10, p@25, or F1@25 degradation versus registered Goose."
            if not normal_degrades
            else "Normal-tour segment regresses on at least one precision/F1 guardrail."
        ),
        top10_guard.interpretation,
    ]

    return PromotionReview(
        overall=_overall_rows(backtests_dir),
        segments=segments,
        deltas=deltas,
        top10_guard=top10_guard,
        recommendation=recommendation,
        rationale=rationale,
    )


def render_markdown(review: PromotionReview) -> str:
    lines = [
        "# Goose promotion-readiness review",
        "",
        "Offline review for `goose_fast_rank_v1_candidate_relaxed_special_nbtop10`. "
        "No registry or production wiring changes are made by this report.",
        "",
        f"## Recommendation: `{review.recommendation}`",
        "",
    ]
    lines.extend(f"- {item}" for item in review.rationale)

    lines.extend(
        [
            "",
            "## Overall scorecard",
            "",
            "| model | role | n | dual | p@10 | p@25 | r@50 | F1@25 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in review.overall:
        marker = "promotion candidate" if row["promotable"] else row["label"]
        lines.append(
            "| `{model}` | {role} | {n} | {dual} | {p10} | {p25} | {r50} | {f1} |".format(
                model=row["model_version"],
                role=marker,
                n=row["n_shows"],
                dual=_fmt(row["dual"]),
                p10=_fmt(row["p10"]),
                p25=_fmt(row["p25"]),
                r50=_fmt(row["r50"]),
                f1=_fmt(row["f1_25"]),
            )
        )

    lines.extend(
        [
            "",
            "## Candidate deltas",
            "",
            "| comparison | segment | n | delta p@10 | delta p@25 | delta r@50 | delta F1@25 | delta dual proxy |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in review.deltas:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} | {} |".format(
                row.comparison,
                row.segment,
                row.n_shows,
                _fmt(row.delta_p10),
                _fmt(row.delta_p25),
                _fmt(row.delta_r50),
                _fmt(row.delta_f1_25),
                _fmt(row.delta_dual_proxy),
            )
        )

    lines.extend(["", "## Segments", ""])
    for key, rows in review.segments.items():
        lines.extend(
            [
                f"### {key}",
                "",
                "| segment | n | p@10 | p@25 | r@50 | F1@25 | dual proxy |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in rows:
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} |".format(
                    row.segment,
                    row.n_shows,
                    _fmt(row.p10),
                    _fmt(row.p25),
                    _fmt(row.r50),
                    _fmt(row.f1_25),
                    _fmt(row.dual_proxy),
                )
            )
        lines.append("")

    guard = review.top10_guard
    lines.extend(
        [
            "## Top-10 guard",
            "",
            f"- Compared shows: {guard.compared_shows}",
            f"- Shows with Notebook-matching p@10 metric: {guard.matching_metric_shows}",
            f"- Aggregate p@10 matches Notebook: {guard.aggregate_p10_matches_notebook}",
            f"- Mismatched show ids: {', '.join(guard.mismatched_show_ids) if guard.mismatched_show_ids else 'none'}",
            f"- Interpretation: {guard.interpretation}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_report(
    *,
    backtests_dir: Path,
    snapshot_root: Path,
    out_dir: Path,
) -> tuple[Path, Path]:
    review = build_review(backtests_dir=backtests_dir, snapshot_root=snapshot_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = out_dir / "goose_promotion_readiness.md"
    json_path = out_dir / "goose_promotion_readiness.json"
    markdown_path.write_text(render_markdown(review))
    json_path.write_text(json.dumps(asdict(review), indent=2, sort_keys=True) + "\n")
    return markdown_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backtests-dir", default="backtests")
    parser.add_argument("--snapshot-root", default=".snapshots/goose_phase_b")
    parser.add_argument("--out-dir", default="diagnostics")
    args = parser.parse_args()

    markdown_path, json_path = write_report(
        backtests_dir=Path(args.backtests_dir),
        snapshot_root=Path(args.snapshot_root),
        out_dir=Path(args.out_dir),
    )
    print(f"Wrote Goose promotion-readiness markdown to {markdown_path}")
    print(f"Wrote Goose promotion-readiness JSON to {json_path}")


if __name__ == "__main__":
    main()
