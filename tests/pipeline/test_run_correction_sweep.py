"""Correction application must refresh derived data before cache invalidation."""

import json
import re
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import run_backtest as backtest
from scripts import run_correction_sweep as sweep
from scripts import sync_retained_prediction_corpus as retained
from src.jambandnerd.data_collection.correction_detector import CorrectionResult


@pytest.fixture
def cli(monkeypatch, tmp_path):
    output = tmp_path / "report.json"
    result = CorrectionResult("goose", "goose_setlists_raw", 1, 1, 1)
    client = object()
    monkeypatch.setattr(sweep, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        sweep, "run_correction_sweep", Mock(return_value={"setlists": result})
    )
    stages = {}
    for name, value in (
        ("sync_retained_prediction_corpus", 50),
        ("generate_live_predictions", True),
        ("_has_upcoming_show", True),
        ("validate_predictions", 0),
        ("validate_accuracy", 0),
    ):
        stages[name] = Mock(return_value=value)
        monkeypatch.setattr(sweep, name, stages[name])

    def run(*, band="goose", apply=True):
        monkeypatch.setattr(
            sys,
            "argv",
            ["sweep", "--band", band, "--output", str(output)]
            + (["--no-dry-run"] if apply else []),
        )
        with pytest.raises(SystemExit) as exit_info:
            sweep.main()
        return exit_info.value.code, json.loads(output.read_text())

    return run, result, stages


@pytest.mark.parametrize("scenario", ["dry-run", "no-op", "inactive"])
def test_sweep_without_applied_active_corrections_skips_refresh(cli, scenario):
    run, result, stages = cli
    if scenario == "no-op":
        result.corrections_applied = result.corrections_found = 0
    code, report = run(
        band="eggy" if scenario == "inactive" else "goose", apply=scenario != "dry-run"
    )
    assert code == 0
    refresh = report["post_correction_refresh"]
    assert refresh["status"] == "skipped"
    assert refresh["cache_invalidation_required"] is False
    for mock in stages.values():
        mock.assert_not_called()


@pytest.mark.parametrize("upcoming", [True, False])
def test_apply_refreshes_retained_live_and_validation_in_order(cli, upcoming):
    run, _, stages = cli
    stages["_has_upcoming_show"].return_value = upcoming
    order = Mock()
    for name, mock in stages.items():
        order.attach_mock(mock, name)
    code, report = run()
    assert code == 0
    refresh = report["post_correction_refresh"]
    assert refresh["status"] == "success"
    assert refresh["corrections_applied"] == 1
    assert refresh["retained_rows_refreshed"] == 50
    assert refresh["cache_invalidation_required"] is True
    stages["sync_retained_prediction_corpus"].assert_called_once_with(
        band="goose", window=50, incremental=False, require_results=True
    )
    assert [call[0] for call in order.mock_calls] == (
        ["sync_retained_prediction_corpus", "_has_upcoming_show"]
        + (["generate_live_predictions"] if upcoming else [])
        + ["validate_predictions", "validate_accuracy"]
    )
    if upcoming:
        stages["generate_live_predictions"].assert_called_once_with(
            band="goose", require_output=True
        )
    else:
        assert refresh["stages"]["live_predictions"] == "skipped_no_upcoming_show"
    stages["validate_accuracy"].assert_called_once_with(
        bands=["goose"],
        max_age_hours=72,
        replay_window=50,
        require_exact_retained_window=True,
    )


def test_partial_raw_apply_refreshes_successful_rows_and_retains_failure(cli):
    run, result, stages = cli
    result.errors.append("Another show could not be corrected")
    code, report = run()
    assert code == 1
    assert report["results"]["setlists"]["errors"] == result.errors
    assert report["post_correction_refresh"]["status"] == "success"
    assert report["post_correction_refresh"]["cache_invalidation_required"] is True
    stages["sync_retained_prediction_corpus"].assert_called_once()


@pytest.mark.parametrize(
    "stage",
    [
        "retained_corpus",
        "live_predictions",
        "prediction_validation",
        "accuracy_validation",
    ],
)
def test_refresh_failure_records_stage_exits_nonzero_and_prints_recovery(
    cli, capsys, stage
):
    run, _, stages = cli
    names = {
        "retained_corpus": "sync_retained_prediction_corpus",
        "live_predictions": "generate_live_predictions",
        "prediction_validation": "validate_predictions",
        "accuracy_validation": "validate_accuracy",
    }
    stages[names[stage]].side_effect = RuntimeError("refresh unavailable")
    code, report = run()
    refresh = report["post_correction_refresh"]
    assert code == 1
    assert refresh["status"] == "failed"
    assert refresh["stages"][stage] == "failed"
    assert refresh["error"] == f"{stage}: refresh unavailable"
    assert refresh["cache_invalidation_required"] is False
    recovery = "uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --no-incremental --require-results"
    assert recovery in refresh["recovery_commands"]
    assert recovery in capsys.readouterr().out


@pytest.mark.parametrize(
    "name,value",
    [
        ("sync_retained_prediction_corpus", 0),
        ("generate_live_predictions", False),
        ("validate_predictions", 1),
        ("validate_accuracy", 1),
    ],
)
def test_unsuccessful_refresh_return_values_do_not_enable_cache(cli, name, value):
    run, _, stages = cli
    stages[name].return_value = value
    code, report = run()
    assert code == 1
    assert report["post_correction_refresh"]["cache_invalidation_required"] is False


def test_old_already_scored_correction_rewrites_actual_songs_and_metrics(
    cli, monkeypatch
):
    run, _, _ = cli
    monkeypatch.setattr(
        sweep,
        "sync_retained_prediction_corpus",
        retained.sync_retained_prediction_corpus,
    )
    monkeypatch.setattr(backtest, "_verify_supabase_write_access", lambda: None)
    monkeypatch.setattr(backtest, "_write_github_output", lambda *a: None)
    old_date = (date.today() - timedelta(days=60)).isoformat()
    actual = ["Wrong A", "Wrong B", "Wrong C"]
    monkeypatch.setattr(
        backtest,
        "fetch_table",
        lambda table: (
            [{"show_id": "old-show", "show_date": old_date}]
            if "shows" in table
            else [{"show_id": "old-show", "song_name": song} for song in actual]
        ),
    )
    monkeypatch.setattr(
        backtest, "build_model_data_for_target", lambda *a, **kw: object()
    )
    predictor = Mock()
    predictor.predict.return_value = [
        SimpleNamespace(song_name="Corrected Song", probability=0.5)
    ]
    monkeypatch.setattr(backtest, "build_band_predictor", lambda *a, **kw: predictor)
    monkeypatch.setattr(
        backtest, "fetch_scored_target_show_keys", Mock(return_value={"old-show"})
    )
    results = {}
    accuracy = {}
    monkeypatch.setattr(
        backtest, "upsert_setlist_result", lambda **kw: results.update(kw) or 123
    )
    monkeypatch.setattr(
        backtest,
        "upsert_setlist_accuracy_dataframe",
        lambda frame, **kw: accuracy.update(frame.iloc[0].to_dict()),
    )
    monkeypatch.setattr(backtest, "prune_setlist_corpus", lambda **kw: 0)

    retained.sync_retained_prediction_corpus(
        band="goose", incremental=False, require_results=True
    )
    assert results["actual_songs"] == actual
    assert accuracy["p10"] == 0
    actual[0] = "Corrected Song"

    code, report = run()

    assert code == 0
    assert report["post_correction_refresh"]["retained_rows_refreshed"] == 1
    assert results["actual_songs"] == ["Corrected Song", "Wrong B", "Wrong C"]
    assert results["target_show_key"] == "old-show"
    assert accuracy["prediction_run_id"] == 123
    assert accuracy["p10"] == pytest.approx(0.1)
    assert accuracy["recall_10"] == pytest.approx(1 / 3)
    backtest.fetch_scored_target_show_keys.assert_not_called()


def test_workflow_gates_cache_from_report_and_scopes_cache_credentials(
    tmp_path, monkeypatch
):
    workflow = (
        Path(__file__).resolve().parents[2]
        / ".github/workflows/weekly-correction-sweep.yml"
    ).read_text()
    step = workflow.split("      - name: Read Post-Correction Refresh State\n", 1)[
        1
    ].split("      - name: Revalidate Website Cache\n")[0]
    script = textwrap.dedent(
        re.search(r"          python - <<'PYTHON'\n(.*?)          PYTHON", step, re.S)[
            1
        ]
    )
    assert "if: always()" in step
    assert (
        "if: always() && steps.refresh-state.outputs.cache_ready == 'true'" in workflow
    )
    cache = workflow.split("      - name: Revalidate Website Cache\n", 1)[1].split(
        "      - name: Upload Sweep Report\n"
    )[0]
    assert workflow.count("${{ vars.SITE_URL }}") == 1
    assert workflow.count("${{ secrets.REVALIDATE_SECRET }}") == 1
    assert "${{ vars.SITE_URL }}" in cache
    assert "${{ secrets.REVALIDATE_SECRET }}" in cache
    assert "run: uv run python scripts/revalidate_website_cache.py" in cache
    assert '"${{ github.event_name }}" != "schedule"' in workflow
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BAND", "goose")
    output = tmp_path / "step-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    report = tmp_path / "correction_sweep_report_goose.json"
    for state, expected in [
        (None, False),
        (
            {
                "status": "success",
                "corrections_applied": 1,
                "cache_invalidation_required": True,
            },
            True,
        ),
        (
            {
                "status": "success",
                "corrections_applied": 0,
                "cache_invalidation_required": True,
            },
            False,
        ),
        (
            {
                "status": "failed",
                "corrections_applied": 1,
                "cache_invalidation_required": False,
            },
            False,
        ),
        (
            {
                "status": "skipped",
                "corrections_applied": 1,
                "cache_invalidation_required": False,
            },
            False,
        ),
    ]:
        if state is not None:
            report.write_text(json.dumps({"post_correction_refresh": state}))
        output.write_text("")
        exec(compile(script, "workflow-refresh-state", "exec"), {})
        assert output.read_text() == f"cache_ready={str(expected).lower()}\n"
