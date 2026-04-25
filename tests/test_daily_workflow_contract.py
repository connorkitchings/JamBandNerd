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
