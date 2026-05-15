from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.report_model_headroom as report


def _write_summary(
    directory: Path,
    *,
    band: str,
    model_version: str,
    dual: float,
    f1_25: float,
) -> None:
    payload = {
        "band": band,
        "model_version": model_version,
        "n_shows": 100,
        "p10": 0.30,
        "p25": 0.25,
        "r50": 0.55,
        "f1_25": f1_25,
        "dual_score": dual,
    }
    (directory / f"{band}_{model_version}_summary.json").write_text(json.dumps(payload))


def test_build_report_uses_frozen_band_baselines(tmp_path) -> None:
    _write_summary(
        tmp_path,
        band="phish",
        model_version="phish_fast_gbm_v2_feat_notebook_rank_venue_run",
        dual=0.419,
        f1_25=0.283,
    )
    _write_summary(
        tmp_path,
        band="phish",
        model_version="phish_fast_gbm_v2",
        dual=0.405,
        f1_25=0.270,
    )

    rows = report.build_report(tmp_path)
    phish = next(row for row in rows if row.band == "phish")
    goose = next(row for row in rows if row.band == "goose")

    assert phish.model_version == "phish_fast_gbm_v2_feat_notebook_rank_venue_run"
    assert phish.recommendation == "cleanup_ablation"
    assert phish.delta_dual == pytest.approx(0.014)
    assert phish.candidate_miss_proxy == pytest.approx(0.45)
    assert not goose.summary_found


def test_worst_show_rows_are_sorted_by_f1_then_recall(tmp_path) -> None:
    jsonl_path = (
        tmp_path / "phish_phish_fast_gbm_v2_feat_notebook_rank_venue_run_100shows.jsonl"
    )
    rows = [
        {
            "show_id": "later",
            "target_show_date": "2025-01-02",
            "actual_song_count": 20,
            "metrics": {"k25": {"f1": 0.2}, "k50": {"recall": 0.4}},
        },
        {
            "show_id": "worst",
            "target_show_date": "2025-01-01",
            "actual_song_count": 5,
            "metrics": {"k25": {"f1": 0.1}, "k50": {"recall": 0.6}},
        },
        {
            "show_id": "tie-break",
            "target_show_date": "2025-01-03",
            "actual_song_count": 18,
            "metrics": {"k25": {"f1": 0.2}, "k50": {"recall": 0.3}},
        },
    ]
    jsonl_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    worst = report._load_worst_shows(jsonl_path)

    assert [row.show_id for row in worst] == ["worst", "tie-break", "later"]


def test_write_report_outputs_markdown_and_json(tmp_path) -> None:
    _write_summary(
        tmp_path,
        band="phish",
        model_version="phish_fast_gbm_v2_feat_notebook_rank_venue_run",
        dual=0.419,
        f1_25=0.283,
    )
    out_dir = tmp_path / "out"

    markdown_path, json_path = report.write_report(
        backtests_dir=tmp_path,
        out_dir=out_dir,
    )

    assert markdown_path.exists()
    assert json_path.exists()
    assert "Model headroom report" in markdown_path.read_text()
    assert json.loads(json_path.read_text())[1]["band"] == "phish"
