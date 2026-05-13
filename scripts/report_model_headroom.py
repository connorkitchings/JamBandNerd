"""Summarize single-model production baselines and next model work.

This report is intentionally offline-only: it reads existing backtest summary
JSON and per-show JSONL artifacts, then ranks the next model action by the
current branch strategy.

Usage:
    uv run python scripts/report_model_headroom.py --backtests-dir backtests
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jambandnerd.models.metadata import BAND_METADATA


@dataclass(frozen=True)
class BaselineSpec:
    band: str
    model_version: str
    previous_baseline: str | None
    recommendation: str
    rationale: str


@dataclass(frozen=True)
class WorstShow:
    show_id: str
    target_show_date: str
    actual_song_count: int
    f1_25: float
    recall_50: float


@dataclass(frozen=True)
class BandHeadroom:
    band: str
    model_version: str
    summary_found: bool
    n_shows: int | None
    dual: float | None
    p10: float | None
    p25: float | None
    r50: float | None
    f1_25: float | None
    previous_baseline: str | None
    delta_dual: float | None
    delta_f1_25: float | None
    candidate_miss_proxy: float | None
    worst_shows: list[WorstShow]
    recommendation: str
    rationale: str


BASELINES: tuple[BaselineSpec, ...] = tuple(
    BaselineSpec(
        band=metadata.band,
        model_version=metadata.model_version,
        previous_baseline={
            "goose": "goose_notebook_1yr",
            "phish": "phish_fast_gbm_v2",
            "wsp": "wsp_fast_gbm_v1",
            "billy": "billy_fast_gbm_v3",
            "um": "um_fast_gbm_v1",
        }.get(metadata.band),
        recommendation={
            "goose": "architecture_spike_if_diagnostics_support",
            "phish": "cleanup_ablation",
            "wsp": "hold_upstream_recovery",
            "billy": "hold_upstream_recovery",
            "um": "hold_monitor_prod_drift",
        }[metadata.band],
        rationale={
            "goose": (
                "Current ranker is only narrowly ahead of the Notebook floor; "
                "avoid more feature/HP sweeps unless diagnostics show a miss pattern."
            ),
            "phish": (
                "Only band with a documented cleanup path after show-type failed "
                "promotion."
            ),
            "wsp": (
                "Current WSP V2 is at local optimum and live validation is blocked "
                "by recent Everyday Companion source gaps."
            ),
            "billy": (
                "Current Billy V10 is at local optimum and live validation is "
                "blocked by bmfsdb.com reachability."
            ),
            "um": (
                "Current UM V2 cleared the Phase B gain; hold unless production "
                "schema-sync fixes reveal drift."
            ),
        }[metadata.band],
    )
    for metadata in BAND_METADATA
)


def _summary_path(backtests_dir: Path, band: str, model_version: str) -> Path:
    return backtests_dir / f"{band}_{model_version}_summary.json"


def _per_show_path(backtests_dir: Path, band: str, model_version: str) -> Path:
    return backtests_dir / f"{band}_{model_version}_100shows.jsonl"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _metric(payload: dict[str, Any] | None, name: str) -> float | None:
    if not payload or name not in payload:
        return None
    return float(payload[name])


def _delta(
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    metric: str,
) -> float | None:
    current_value = _metric(current, metric)
    previous_value = _metric(previous, metric)
    if current_value is None or previous_value is None:
        return None
    return current_value - previous_value


def _load_worst_shows(path: Path, *, limit: int = 3) -> list[WorstShow]:
    if not path.exists():
        return []

    rows: list[WorstShow] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        metrics = row.get("metrics", {})
        k25 = metrics.get("k25", {})
        k50 = metrics.get("k50", {})
        rows.append(
            WorstShow(
                show_id=str(row.get("show_id", "")),
                target_show_date=str(row.get("target_show_date", "")),
                actual_song_count=int(row.get("actual_song_count", 0)),
                f1_25=float(k25.get("f1", 0.0)),
                recall_50=float(k50.get("recall", 0.0)),
            )
        )
    return sorted(rows, key=lambda row: (row.f1_25, row.recall_50))[:limit]


def build_report(backtests_dir: Path) -> list[BandHeadroom]:
    rows: list[BandHeadroom] = []
    for spec in BASELINES:
        current = _load_json(
            _summary_path(backtests_dir, spec.band, spec.model_version)
        )
        previous = (
            _load_json(_summary_path(backtests_dir, spec.band, spec.previous_baseline))
            if spec.previous_baseline
            else None
        )
        r50 = _metric(current, "r50")
        rows.append(
            BandHeadroom(
                band=spec.band,
                model_version=spec.model_version,
                summary_found=current is not None,
                n_shows=int(current["n_shows"]) if current else None,
                dual=_metric(current, "dual_score"),
                p10=_metric(current, "p10"),
                p25=_metric(current, "p25"),
                r50=r50,
                f1_25=_metric(current, "f1_25"),
                previous_baseline=spec.previous_baseline,
                delta_dual=_delta(current, previous, "dual_score"),
                delta_f1_25=_delta(current, previous, "f1_25"),
                candidate_miss_proxy=(1.0 - r50 if r50 is not None else None),
                worst_shows=_load_worst_shows(
                    _per_show_path(backtests_dir, spec.band, spec.model_version)
                ),
                recommendation=spec.recommendation,
                rationale=spec.rationale,
            )
        )
    return rows


def _fmt(value: float | int | None, *, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def render_markdown(rows: list[BandHeadroom]) -> str:
    lines = [
        "# Model headroom report",
        "",
        "Production baselines are frozen to the single-model-per-band registry. "
        "This report ranks follow-up work without promoting experiments.",
        "",
        "## Baseline scorecard",
        "",
        "| band | model_version | n | dual | p@10 | p@25 | r@50 | F1@25 | delta dual | delta F1@25 | miss proxy | recommendation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {band} | `{model}` | {n} | {dual} | {p10} | {p25} | {r50} | "
            "{f1} | {delta_dual} | {delta_f1} | {miss} | `{rec}` |".format(
                band=row.band,
                model=row.model_version,
                n=_fmt(row.n_shows),
                dual=_fmt(row.dual),
                p10=_fmt(row.p10),
                p25=_fmt(row.p25),
                r50=_fmt(row.r50),
                f1=_fmt(row.f1_25),
                delta_dual=_fmt(row.delta_dual),
                delta_f1=_fmt(row.delta_f1_25),
                miss=_fmt(row.candidate_miss_proxy),
                rec=row.recommendation,
            )
        )

    lines.extend(["", "## Worst-show segments", ""])
    for row in rows:
        lines.append(f"### {row.band}")
        lines.append("")
        if not row.summary_found:
            lines.append(
                f"- Missing `{row.band}_{row.model_version}_summary.json`; run the "
                "registered baseline backtest before interpreting headroom."
            )
        else:
            lines.append(f"- {row.rationale}")
        if row.worst_shows:
            lines.append("")
            lines.append("| show_id | target_show_date | actual songs | F1@25 | r@50 |")
            lines.append("| --- | --- | ---: | ---: | ---: |")
            for worst in row.worst_shows:
                lines.append(
                    "| `{}` | {} | {} | {:.4f} | {:.4f} |".format(
                        worst.show_id,
                        worst.target_show_date,
                        worst.actual_song_count,
                        worst.f1_25,
                        worst.recall_50,
                    )
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(
    *,
    backtests_dir: Path,
    out_dir: Path,
) -> tuple[Path, Path]:
    rows = build_report(backtests_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = out_dir / "model_headroom_report.md"
    json_path = out_dir / "model_headroom_report.json"

    markdown_path.write_text(render_markdown(rows))
    json_path.write_text(
        json.dumps([asdict(row) for row in rows], indent=2, sort_keys=True) + "\n"
    )
    return markdown_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backtests-dir", default="backtests")
    parser.add_argument("--out-dir", default="diagnostics")
    args = parser.parse_args()

    markdown_path, json_path = write_report(
        backtests_dir=Path(args.backtests_dir),
        out_dir=Path(args.out_dir),
    )
    print(f"Wrote model headroom markdown to {markdown_path}")
    print(f"Wrote model headroom JSON to {json_path}")


if __name__ == "__main__":
    main()
