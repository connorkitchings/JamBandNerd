from __future__ import annotations

from pathlib import Path

from jambandnerd.config.bands import get_repo_supported_bands

WORKFLOW_PATH = Path(".github/workflows/daily-pipeline.yml")
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

    assert "python -m scripts.get_all_bands" in workflow
    for band in get_repo_supported_bands():
        assert f"          - {band}" in workflow

    assert "uv run python scripts/generate_live_predictions.py" in workflow
    assert (
        "uv run python scripts/sync_retained_prediction_corpus.py --band ${{ matrix.band }} "
        "--window 50 --incremental --require-results"
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

    assert "both models use the same last-50 window" in contents
    assert "repo-authoritative automation band list" in contents


def test_daily_workflow_missing_recent_setlists_skip_regeneration() -> None:
    workflow = WORKFLOW_PATH.read_text()

    gated_steps = (
        "Generate Predictions (Notebook & Deal)",
        "Validate Prediction Tables",
        "Run Backtest and Save Per-Show Accuracy",
        "Validate Accuracy Tables",
    )
    for step_name in gated_steps:
        step_index = workflow.index(f"- name: {step_name}")
        step_block = workflow[
            step_index : workflow.index("\n      - name:", step_index + 1)
        ]
        assert "steps.data_check.outputs.missing_data != 'true'" in step_block

    assert 'workflow_state = "degraded"' in workflow
    assert 'outcome_code = "degraded_missing_recent_setlists"' in workflow
    assert 'prediction_action = "skipped_missing_setlists"' in workflow


def test_daily_workflow_preserves_verify_only_prediction_action() -> None:
    workflow = WORKFLOW_PATH.read_text()

    assert (
        "PREDICTION_ACTION: ${{ steps.collection.outputs.prediction_action || "
        "steps.collection_idle.outputs.prediction_action || '' }}"
    ) in workflow
    assert (
        'explicit_prediction_action = os.environ.get("PREDICTION_ACTION", "").strip()'
        in workflow
    )
    assert "elif explicit_prediction_action:" in workflow
    assert "prediction_action = explicit_prediction_action" in workflow
