from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from jambandnerd.config.bands import get_daily_pipeline_bands
from jambandnerd.models.registry import list_active_bands

WORKFLOW_PATH = Path(".github/workflows/daily-pipeline.yml")
WEEKLY_CORRECTION_WORKFLOW_PATH = Path(".github/workflows/weekly-correction-sweep.yml")
CORRECTION_DETECTOR_PATH = Path(
    "src/jambandnerd/data_collection/correction_detector.py"
)
ACTIVE_DOC_PATHS = (
    Path("README.md"),
    Path("docs/user/pipeline_usage.md"),
    Path("docs/user/configuration.md"),
    Path("docs/contributor/developer_guide/architecture.md"),
    Path("docs/contributor/developer_guide/extending_the_platform.md"),
    Path("docs/contributor/model_readiness.md"),
    Path("docs/operations/github_actions.md"),
    Path("docs/reference/specifications/data_strategy.md"),
    Path("docs/reference/specifications/database.md"),
    Path("docs/reference/specifications/predictions_schema.md"),
    Path("docs/reference/specifications/cli.md"),
    Path("scripts/README.md"),
)
FORBIDDEN_ACTIVE_DOC_TERMS = (
    "api_show_id",
    "predictions_notebook",
    "predictions_deal",
    "predictions_ckplus",
    "notebook_accuracy",
    "accuracy_deal",
    "accuracy_ckplus",
    "aggregate accuracy table",
    "aggregate accuracy tables",
)


def test_daily_workflow_matrix_and_backtest_windows_match_repo_contract() -> None:
    workflow = WORKFLOW_PATH.read_text()

    assert "python scripts/get_all_bands.py" in workflow

    result = subprocess.run(
        [sys.executable, "scripts/get_all_bands.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    matrix_bands = json.loads(result.stdout)

    assert matrix_bands == list(get_daily_pipeline_bands())
    assert matrix_bands == list_active_bands()
    assert "eggy" not in matrix_bands

    assert (
        "uv run python scripts/generate_live_predictions.py "
        "--band ${{ matrix.band }} --require-output"
    ) in workflow
    sync_pattern = (
        r"uv run python scripts/sync_retained_prediction_corpus\.py "
        r"--band \$\{\{ matrix\.band \}\} "
        r"--window \d+ --incremental --require-results"
    )
    assert re.search(sync_pattern, workflow), (
        "daily-pipeline.yml must contain a sync_retained_prediction_corpus "
        "invocation with --window <int>"
    )


def test_daily_workflow_limits_degraded_accuracy_warning_to_wsp_upstream_lag() -> None:
    workflow = WORKFLOW_PATH.read_text()
    informational_accuracy_condition = (
        "github.event.inputs.skip_accuracy == 'true' || "
        "(matrix.band == 'wsp' && "
        "steps.collection.outputs.outcome_code == 'degraded_upstream_lag')"
    )

    assert workflow.count(informational_accuracy_condition) == 2
    assert (
        workflow.count('if [[ "${ACCURACY_FRESHNESS_IS_INFORMATIONAL}" == "true" ]]')
        == 1
    )
    assert (
        'if [[ "${ACCURACY_FRESHNESS_IS_INFORMATIONAL}" == "true" || '
        '"${BACKTEST_INCREMENTAL_ALL_SCORED}" == "true" ]]'
    ) in workflow


def test_active_docs_do_not_reference_retired_storage_contract_terms() -> None:
    offenders: list[str] = []
    for path in ACTIVE_DOC_PATHS:
        contents = path.read_text()
        for term in FORBIDDEN_ACTIVE_DOC_TERMS:
            if term in contents:
                offenders.append(f"{path}:{term}")

    assert offenders == []


def test_github_actions_docs_match_current_deal_window_and_band_authority() -> None:
    contents = Path("docs/operations/github_actions.md").read_text()

    assert "scripts/get_all_bands.py" in contents
    assert "get_daily_pipeline_bands()" in contents
    assert "Eggy remains collectable" in contents


def test_weekly_correction_sweep_is_not_scheduled_without_detector() -> None:
    workflow = WEEKLY_CORRECTION_WORKFLOW_PATH.read_text()
    script = Path("scripts/run_correction_sweep.py").read_text()

    assert "workflow_dispatch:" in workflow
    if (
        "src.jambandnerd.data_collection.correction_detector" in script
        and not CORRECTION_DETECTOR_PATH.exists()
    ):
        assert "\n  schedule:" not in workflow
    else:
        assert "\n  schedule:" in workflow
