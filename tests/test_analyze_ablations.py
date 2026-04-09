from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import analyze_ablations as module


def _report(
    *,
    label: str,
    candidate_cross: tuple[float, float],
    notebook_cross: tuple[float, float],
    band_values: dict[str, tuple[tuple[float, float], tuple[float, float]]],
    overrides: dict | None = None,
    gate: bool = True,
) -> dict:
    candidate_k10, candidate_k25 = candidate_cross
    notebook_k10, notebook_k25 = notebook_cross
    metrics_by_band = {}
    for band, values in band_values.items():
        candidate_band, notebook_band = values
        metrics_by_band[band] = {
            "deal": {
                "metrics": {
                    "k10": {"recall": candidate_band[0]},
                    "k25": {"recall": candidate_band[1]},
                }
            },
            "notebook": {
                "metrics": {
                    "k10": {"recall": notebook_band[0]},
                    "k25": {"recall": notebook_band[1]},
                }
            },
        }

    return {
        "candidate_model": {"slug": "deal", "version": "deal_v2"},
        "experiment_metadata": {
            "feature_set_label": label,
            "candidate_overrides": overrides or {},
        },
        "report_status": "complete",
        "windows": {
            "last_50": {
                "cross_band_summary": {
                    "deal": {
                        "metrics": {
                            "k10": {"recall": candidate_k10, "hit_rate": 0.88},
                            "k25": {"recall": candidate_k25},
                            "k50": {"recall": 0.4},
                        },
                        "bands_evaluated": len(metrics_by_band),
                        "shows_evaluated": 300,
                    },
                    "notebook": {
                        "metrics": {
                            "k10": {"recall": notebook_k10, "hit_rate": 0.87},
                            "k25": {"recall": notebook_k25},
                            "k50": {"recall": 0.39},
                        },
                        "bands_evaluated": len(metrics_by_band),
                        "shows_evaluated": 300,
                    },
                },
                "metrics_by_band": metrics_by_band,
                "promotion_gate": {"passes": gate},
            }
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def test_analyze_ablations_emits_batch2_candidates_and_combo_suggestions(
    tmp_path, monkeypatch, capsys
) -> None:
    batch_dir = tmp_path / "batch1"
    batch_dir.mkdir()
    baseline_path = tmp_path / "baseline.json"

    baseline_bands = {
        "goose": ((0.150, 0.300), (0.180, 0.320)),
        "phish": ((0.140, 0.290), (0.160, 0.300)),
        "billy": ((0.130, 0.280), (0.145, 0.285)),
    }
    _write_json(
        baseline_path,
        _report(
            label="shared_core_v1",
            candidate_cross=(0.150, 0.300),
            notebook_cross=(0.160, 0.305),
            band_values=baseline_bands,
        ),
    )

    _write_json(
        batch_dir / "threshold_min3.json",
        _report(
            label="threshold_min3",
            candidate_cross=(0.162, 0.308),
            notebook_cross=(0.160, 0.305),
            band_values={
                "goose": ((0.158, 0.305), (0.180, 0.320)),
                "phish": ((0.152, 0.298), (0.160, 0.300)),
                "billy": ((0.136, 0.282), (0.145, 0.285)),
            },
            overrides={"min_plays_threshold": 3},
        ),
    )
    _write_json(
        batch_dir / "weight_cap10.json",
        _report(
            label="weight_cap10",
            candidate_cross=(0.159, 0.303),
            notebook_cross=(0.160, 0.305),
            band_values={
                "goose": ((0.157, 0.304), (0.180, 0.320)),
                "phish": ((0.148, 0.294), (0.160, 0.300)),
                "billy": ((0.137, 0.283), (0.145, 0.285)),
            },
            overrides={"positive_weight_cap": 10.0},
        ),
    )
    _write_json(
        batch_dir / "no_venue.json",
        _report(
            label="no_venue",
            candidate_cross=(0.149, 0.297),
            notebook_cross=(0.160, 0.305),
            band_values={
                "goose": ((0.149, 0.297), (0.180, 0.320)),
                "phish": ((0.141, 0.289), (0.160, 0.300)),
                "billy": ((0.132, 0.279), (0.145, 0.285)),
            },
            overrides={"feature_columns": ["current_gap"]},
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "analyze_ablations.py",
            "--batch-dir",
            str(batch_dir),
            "--baseline",
            str(baseline_path),
        ],
    )

    module.main()
    output = capsys.readouterr().out

    assert "Batch 2 qualified winners:" in output
    assert "- threshold_min3:" in output
    assert "- weight_cap10:" in output
    assert "Suggested Batch 2 combinations:" in output
    assert "threshold_min3 + weight_cap10" in output
    assert '"min_plays_threshold": 3' in output
    assert '"positive_weight_cap": 10.0' in output


def test_analyze_ablations_reports_no_batch2_candidates_when_filters_fail(
    tmp_path, monkeypatch, capsys
) -> None:
    batch_dir = tmp_path / "batch1"
    batch_dir.mkdir()
    baseline_path = tmp_path / "baseline.json"

    baseline_bands = {
        "goose": ((0.150, 0.300), (0.180, 0.320)),
        "phish": ((0.140, 0.290), (0.160, 0.300)),
        "billy": ((0.130, 0.280), (0.145, 0.285)),
    }
    _write_json(
        baseline_path,
        _report(
            label="shared_core_v1",
            candidate_cross=(0.150, 0.300),
            notebook_cross=(0.160, 0.305),
            band_values=baseline_bands,
        ),
    )
    _write_json(
        batch_dir / "freq_only.json",
        _report(
            label="freq_only",
            candidate_cross=(0.149, 0.299),
            notebook_cross=(0.160, 0.305),
            band_values={
                "goose": ((0.149, 0.299), (0.180, 0.320)),
                "phish": ((0.140, 0.289), (0.160, 0.300)),
                "billy": ((0.131, 0.279), (0.145, 0.285)),
            },
            overrides={"feature_columns": ["plays_past_year"]},
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "analyze_ablations.py",
            "--batch-dir",
            str(batch_dir),
            "--baseline",
            str(baseline_path),
        ],
    )

    module.main()
    output = capsys.readouterr().out

    assert "Batch 2: no single-factor ablation qualifies." in output
