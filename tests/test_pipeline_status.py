from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.pipeline_status import build_band_status, fantasy_goose_eligible

ROOT = Path(__file__).resolve().parents[1]


def _steps():
    steps = {
        name: {"outcome": "success", "outputs": {}}
        for name in (
            "preflight",
            "collection",
            "data_check",
            "show_target",
            "predictions",
            "prediction_validation",
            "accuracy_calc",
            "accuracy_validation",
            "freshness_audit",
            "supabase_audit",
            "freshness_enforcement",
            "cache_revalidation",
        )
    }
    steps["preflight"]["outputs"] = {
        "should_run_collection": "true",
        "collection_mode": "window_refresh",
        "execution_mode": "bounded_refresh",
    }
    steps["collection"]["outputs"] = {
        "workflow_state": "success",
        "outcome_code": "success",
        "recent_data_usable": "true",
    }
    steps["data_check"]["outputs"] = {"missing_data": "false"}
    steps["show_target"]["outputs"] = {"has_upcoming_show": "true"}
    steps["freshness_audit"]["outputs"] = {"freshness_state": "fresh"}
    steps["supabase_audit"]["outputs"] = {"audit_state": "ok"}
    return steps


def _status(steps, **kwargs):
    return build_band_status(
        band="goose",
        steps=steps,
        job_status=kwargs.get("job_status", "success"),
        accuracy_skipped=kwargs.get("accuracy_skipped", False),
    )


def test_validated_goose_is_eligible_despite_unrelated_band_failure():
    goose = _status(_steps())
    phish = deepcopy(goose) | {"band": "phish", "workflow_state": "failed"}

    assert goose["workflow_state"] == "success"
    assert fantasy_goose_eligible(goose)
    assert not fantasy_goose_eligible(phish)
    assert goose["collection_workflow_state"] == "success"


@pytest.mark.parametrize("stage", list(_steps()))
@pytest.mark.parametrize("outcome", ["failure", "skipped", "cancelled", "missing"])
def test_required_failed_or_missing_stage_fails_closed(stage, outcome):
    steps = _steps()
    if outcome == "missing":
        del steps[stage]
    else:
        steps[stage]["outcome"] = outcome

    status = _status(steps)

    assert status["workflow_state"] == "failed"
    assert not fantasy_goose_eligible(status)
    assert status["collection_workflow_state"] == (
        "unknown"
        if stage in {"collection", "preflight"} and outcome == "missing"
        else "success"
    )
    if stage != "predictions":
        assert status["prediction_action"] == "generated"


@pytest.mark.parametrize(
    "stage,key",
    [
        ("preflight", "should_run_collection"),
        ("data_check", "missing_data"),
        ("show_target", "has_upcoming_show"),
        ("freshness_audit", "freshness_state"),
        ("supabase_audit", "audit_state"),
    ],
)
def test_successful_step_without_required_output_fails_closed(stage, key):
    steps = _steps()
    del steps[stage]["outputs"][key]

    assert _status(steps)["workflow_state"] == "failed"


def test_later_job_failure_overrides_collection_and_preserves_generation():
    status = _status(_steps(), job_status="failure")

    assert status["workflow_state"] == "failed"
    assert status["outcome_code"] == "failed_internal"
    assert status["collection_workflow_state"] == "success"
    assert status["prediction_action"] == "generated"


def test_cache_delivery_failure_is_explicit_and_blocks_automatic_play():
    steps = _steps()
    steps["cache_revalidation"]["outcome"] = "failure"
    status = _status(steps, job_status="failure")

    assert status["cache_revalidation_outcome"] == "failure"
    assert status["workflow_state"] == "failed"
    assert status["prediction_action"] == "generated"
    assert not fantasy_goose_eligible(status)


def test_degraded_reuse_does_not_require_regeneration():
    steps = _steps()
    steps["collection"]["outputs"].update(
        workflow_state="degraded", outcome_code="degraded_upstream_lag"
    )
    steps["data_check"]["outputs"]["missing_data"] = "true"
    steps["freshness_audit"]["outputs"]["freshness_state"] = "warning"
    steps["supabase_audit"]["outputs"]["audit_state"] = "warning"
    for stage in (
        "predictions",
        "prediction_validation",
        "accuracy_calc",
        "accuracy_validation",
    ):
        steps[stage]["outcome"] = "skipped"

    status = _status(steps)

    assert status["workflow_state"] == "degraded"
    assert status["prediction_action"] == "reused_existing"
    assert not fantasy_goose_eligible(status)


def test_no_upcoming_show_does_not_require_predictions_but_still_requires_accuracy():
    steps = _steps()
    steps["show_target"]["outputs"]["has_upcoming_show"] = "false"
    for stage in ("predictions", "prediction_validation"):
        steps[stage]["outcome"] = "skipped"

    assert _status(steps)["workflow_state"] == "success"
    steps["accuracy_calc"]["outcome"] = "skipped"
    assert _status(steps)["workflow_state"] == "failed"


def test_manual_skip_accuracy_allows_only_accuracy_stages_to_skip():
    steps = _steps()
    for stage in ("accuracy_calc", "accuracy_validation"):
        steps[stage]["outcome"] = "skipped"
    steps["freshness_audit"]["outputs"]["freshness_state"] = "warning"
    steps["supabase_audit"]["outputs"]["audit_state"] = "warning"

    status = _status(steps, accuracy_skipped=True)

    assert status["workflow_state"] == "success"
    assert fantasy_goose_eligible(status)
    steps["prediction_validation"]["outcome"] = "skipped"
    assert _status(steps, accuracy_skipped=True)["workflow_state"] == "failed"


def test_verify_only_still_requires_completeness_and_target_checks():
    steps = _steps()
    steps["preflight"]["outputs"]["should_run_collection"] = "false"
    steps["collection_idle"] = steps.pop("collection")
    for stage in (
        "predictions",
        "prediction_validation",
        "accuracy_calc",
        "accuracy_validation",
        "freshness_audit",
        "supabase_audit",
        "freshness_enforcement",
        "cache_revalidation",
    ):
        steps[stage]["outcome"] = "skipped"

    status = _status(steps)

    assert status["workflow_state"] == "success"
    assert status["prediction_action"] == "skipped_idle"
    steps["data_check"]["outcome"] = "skipped"
    assert _status(steps)["workflow_state"] == "failed"


@pytest.mark.parametrize(
    "key,value",
    [
        ("prediction_validation_outcome", "skipped"),
        ("prediction_validation_outcome", None),
        ("supabase_audit_state", "failed"),
        ("supabase_audit_state", "unknown"),
        ("workflow_state", "failed"),
        ("prediction_action", "reused_existing"),
    ],
)
def test_fantasy_gate_fails_closed_for_invalid_artifact(key, value):
    status = _status(_steps())
    status[key] = value

    assert not fantasy_goose_eligible(status)


def test_status_cli_writes_final_failure_artifact_and_gate_declines_it(tmp_path):
    steps = _steps()
    steps["prediction_validation"]["outcome"] = "failure"
    summary = tmp_path / "summary.md"
    env = os.environ | {
        "BAND": "goose",
        "STEPS_JSON": json.dumps(steps),
        "JOB_STATUS": "failure",
        "GITHUB_STEP_SUMMARY": str(summary),
    }

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/pipeline_status.py")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    artifact = tmp_path / ".github/workflow-status/goose.json"
    status = json.loads(artifact.read_text())
    assert status["workflow_state"] == "failed"
    assert status["prediction_action"] == "generated"
    assert "prediction_validation_outcome: failure" in summary.read_text()
    gate_output = tmp_path / "gate-output"
    gate = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/pipeline_status.py"),
            "--fantasy-gate",
            str(artifact),
        ],
        env=env | {"GITHUB_OUTPUT": str(gate_output)},
        text=True,
        capture_output=True,
    )
    assert gate.returncode == 0
    assert gate_output.read_text() == "should_play=false\n"


def test_fantasy_gate_cli_declines_missing_or_malformed_artifact(tmp_path):
    artifact = tmp_path / "goose.json"
    for contents in (None, "{bad json", "[]"):
        if contents is not None:
            artifact.write_text(contents)
        gate = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/pipeline_status.py"),
                "--fantasy-gate",
                str(artifact),
            ],
            text=True,
            capture_output=True,
            env=os.environ | {"GITHUB_OUTPUT": str(tmp_path / "gate-output")},
        )
        assert gate.returncode == 0
        assert gate.stdout.strip() == "should_play=false"


def test_workflow_records_final_status_after_freshness_and_cache_with_always_upload():
    workflow = (ROOT / ".github/workflows/daily-pipeline.yml").read_text()
    assert workflow.index("id: freshness_enforcement") < workflow.index(
        "- name: Write Band Status"
    )
    assert workflow.index("id: cache_revalidation") < workflow.index(
        "- name: Write Band Status"
    )
    status_step = workflow.split("- name: Write Band Status", 1)[1].split(
        "- name: Upload Band Status", 1
    )[0]
    assert "if: always()" in status_step
    assert "STEPS_JSON: ${{ toJSON(steps) }}" in status_step
    assert "JOB_STATUS: ${{ job.status }}" in status_step
    assert "run: python scripts/pipeline_status.py" in status_step
    upload_step = workflow.split("- name: Upload Band Status", 1)[1].split(
        "- name: Upload Supabase Audit", 1
    )[0]
    assert "if: always()" in upload_step


def test_workflow_uses_post_collection_upcoming_check_without_replacing_policy_metadata():
    workflow = (ROOT / ".github/workflows/daily-pipeline.yml").read_text()
    assert (
        workflow.index("- name: Run Data Collection")
        < workflow.index("id: show_target")
        < workflow.index("- name: Generate Predictions")
    )
    assert "--check-upcoming-only" in workflow
    assert "steps.show_target.outputs.has_upcoming_show == 'true'" in workflow
    assert "steps.preflight.outputs.has_upcoming_show == 'true'" not in workflow
    assert (
        "steps.collection.outputs.workflow_state == 'success' && steps.data_check.outputs.missing_data == 'false'"
        in workflow
    )
    status = _status(_steps())
    assert status["has_upcoming_show"] is True
    assert status["collection_mode"] == "window_refresh"
    assert status["execution_mode"] == "bounded_refresh"


def test_fantasy_workflow_downloads_triggering_run_and_uses_validated_board_gate():
    workflow = (ROOT / ".github/workflows/fantasy-goose.yml").read_text()
    assert "run-id: ${{ github.event.workflow_run.id }}" in workflow
    assert "github-token: ${{ github.token }}" in workflow
    assert (
        "python scripts/pipeline_status.py --fantasy-gate band-status/goose.json"
        in workflow
    )
    assert "github.event.workflow_run.conclusion == 'success'" not in workflow


def test_fantasy_automatic_trigger_is_limited_to_production_branch():
    workflow = (ROOT / ".github/workflows/fantasy-goose.yml").read_text()
    automatic_trigger = workflow.split("  workflow_run:", 1)[1].split(
        "  workflow_dispatch:", 1
    )[0]
    assert "    branches:\n      - main\n" in automatic_trigger
    assert "  workflow_dispatch:" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
