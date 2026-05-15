from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.report_goose_promotion_readiness as report


def _write_summary(
    directory: Path,
    *,
    model_version: str,
    p10: float,
    p25: float,
    r50: float,
    f1_25: float,
    dual: float,
) -> None:
    payload = {
        "band": "goose",
        "model_version": model_version,
        "n_shows": 2,
        "p10": p10,
        "p25": p25,
        "p50": 0.15,
        "r10": 0.20,
        "r25": 0.40,
        "r50": r50,
        "f1_10": 0.24,
        "f1_25": f1_25,
        "f1_50": 0.25,
        "ndcg_10": 0.30,
        "ndcg_25": 0.36,
        "ndcg_50": 0.42,
        "weighted_score": 0.22,
        "dual_score": dual,
        "dual_f1_score": 0.24,
    }
    path = directory / f"goose_{model_version}_summary.json"
    path.write_text(json.dumps(payload))


def _record(
    show_id: str,
    *,
    date: str,
    p10: float,
    p25: float,
    r50: float,
    f1_25: float,
) -> dict:
    return {
        "show_id": show_id,
        "target_show_date": date,
        "reference_date": date,
        "actual_song_count": 10,
        "prediction_count": 50,
        "metrics": {
            "k10": {
                "hit": 1.0,
                "matches": p10 * 10,
                "precision": p10,
                "recall": p10,
                "f1": p10,
                "ndcg": p10,
            },
            "k25": {
                "hit": 1.0,
                "matches": p25 * 25,
                "precision": p25,
                "recall": p25,
                "f1": f1_25,
                "ndcg": p25,
            },
            "k50": {
                "hit": 1.0,
                "matches": r50 * 10,
                "precision": r50 / 5,
                "recall": r50,
                "f1": r50 / 3,
                "ndcg": r50,
            },
        },
    }


def _write_jsonl(directory: Path, model_version: str, rows: list[dict]) -> None:
    path = directory / f"goose_{model_version}_100shows.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def _write_fixture_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    (snapshot_root / "goose_shows_raw.json").write_text(
        json.dumps(
            {
                "rows": [
                    {"show_id": "special", "tour_name": "Not Part of a Tour"},
                    {"show_id": "normal", "tour_name": "Spring Tour"},
                ]
            }
        )
    )

    versions = {
        "registered": "goose_fast_rank_v1",
        "notebook": "goose_notebook_floor_v1",
        "candidate": "goose_fast_rank_v1_candidate_relaxed_special_nbtop10",
        "global": "goose_fast_rank_v1_candidate_relaxed_global_nbtop10",
    }
    _write_summary(
        tmp_path,
        model_version=versions["registered"],
        p10=0.25,
        p25=0.20,
        r50=0.50,
        f1_25=0.25,
        dual=0.40,
    )
    _write_summary(
        tmp_path,
        model_version=versions["notebook"],
        p10=0.30,
        p25=0.21,
        r50=0.51,
        f1_25=0.26,
        dual=0.41,
    )
    _write_summary(
        tmp_path,
        model_version=versions["candidate"],
        p10=0.30,
        p25=0.24,
        r50=0.60,
        f1_25=0.30,
        dual=0.45,
    )
    _write_summary(
        tmp_path,
        model_version=versions["global"],
        p10=0.30,
        p25=0.25,
        r50=0.65,
        f1_25=0.32,
        dual=0.48,
    )

    _write_jsonl(
        tmp_path,
        versions["registered"],
        [
            _record(
                "special", date="2025-01-01", p10=0.20, p25=0.16, r50=0.30, f1_25=0.20
            ),
            _record(
                "normal", date="2025-01-02", p10=0.30, p25=0.24, r50=0.70, f1_25=0.30
            ),
        ],
    )
    _write_jsonl(
        tmp_path,
        versions["notebook"],
        [
            _record(
                "special", date="2025-01-01", p10=0.30, p25=0.18, r50=0.35, f1_25=0.22
            ),
            _record(
                "normal", date="2025-01-02", p10=0.30, p25=0.24, r50=0.67, f1_25=0.30
            ),
        ],
    )
    _write_jsonl(
        tmp_path,
        versions["candidate"],
        [
            _record(
                "special", date="2025-01-01", p10=0.30, p25=0.28, r50=0.60, f1_25=0.34
            ),
            _record(
                "normal", date="2025-01-02", p10=0.30, p25=0.24, r50=0.70, f1_25=0.30
            ),
        ],
    )
    _write_jsonl(
        tmp_path,
        versions["global"],
        [
            _record(
                "special", date="2025-01-01", p10=0.30, p25=0.30, r50=0.62, f1_25=0.36
            ),
            _record(
                "normal", date="2025-01-02", p10=0.30, p25=0.26, r50=0.80, f1_25=0.32
            ),
        ],
    )
    return tmp_path, snapshot_root


def test_build_review_segments_candidate_deltas_and_guard(tmp_path) -> None:
    backtests_dir, snapshot_root = _write_fixture_artifacts(tmp_path)

    review = report.build_review(
        backtests_dir=backtests_dir,
        snapshot_root=snapshot_root,
    )

    assert review.recommendation == "promote_after_separate_production_wiring_task"
    assert review.top10_guard.compared_shows == 2
    assert review.top10_guard.mismatched_show_ids == []

    special_delta = next(
        row
        for row in review.deltas
        if row.comparison == "candidate_vs_registered" and row.segment == "special"
    )
    normal_delta = next(
        row
        for row in review.deltas
        if row.comparison == "candidate_vs_registered" and row.segment == "normal"
    )

    assert special_delta.delta_f1_25 == pytest.approx(0.14)
    assert normal_delta.delta_f1_25 == pytest.approx(0.0)
    assert special_delta.delta_r50 > normal_delta.delta_r50


def test_write_report_outputs_markdown_and_json(tmp_path) -> None:
    backtests_dir, snapshot_root = _write_fixture_artifacts(tmp_path)
    out_dir = tmp_path / "diagnostics"

    markdown_path, json_path = report.write_report(
        backtests_dir=backtests_dir,
        snapshot_root=snapshot_root,
        out_dir=out_dir,
    )

    markdown = markdown_path.read_text()
    payload = json.loads(json_path.read_text())

    assert "Goose promotion-readiness review" in markdown
    assert "candidate_vs_registered" in markdown
    assert payload["recommendation"] == "promote_after_separate_production_wiring_task"
