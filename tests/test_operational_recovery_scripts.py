from __future__ import annotations

from scripts import audit_raw_data, rebuild_derived_data


def test_audit_bands_returns_number_of_failing_bands(monkeypatch):
    calls: list[str] = []

    def fake_diagnose_band(band: str, verbose: bool = False):  # noqa: ARG001
        calls.append(band)
        return {"band": band, "issues": [] if band == "goose" else ["problem"]}

    monkeypatch.setattr(audit_raw_data, "diagnose_band", fake_diagnose_band)

    failures = audit_raw_data.audit_bands(["goose", "phish"], verbose=False)

    assert failures == 1
    assert calls == ["goose", "phish"]


def test_rebuild_band_outputs_runs_predictions_accuracy_and_validation(monkeypatch):
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        rebuild_derived_data,
        "generate_predictions",
        lambda **kwargs: events.append(("predict", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "run_backtest",
        lambda **kwargs: events.append(("backtest", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "save_aggregate_accuracy",
        lambda **kwargs: events.append(("aggregate", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "validate_predictions",
        lambda bands, max_age_hours: events.append(("validate", bands[0])) or 0,
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "validate_accuracy",
        lambda bands, max_age_hours: events.append(("validate_accuracy", bands[0]))
        or 0,
    )

    rebuild_derived_data.rebuild_band_outputs(
        band="goose",
        rebuild_predictions=True,
        rebuild_accuracy=True,
        clear_existing=False,
        start=None,
        end=None,
        recent_shows=None,
        aggregate_shows=100,
        max_age_hours=72,
    )

    assert events == [
        ("predict", "notebook"),
        ("backtest", "notebook"),
        ("aggregate", "notebook"),
        ("predict", "ckplus"),
        ("backtest", "ckplus"),
        ("aggregate", "ckplus"),
        ("validate", "goose"),
        ("validate_accuracy", "goose"),
    ]


def test_rebuild_band_outputs_skips_validation_when_predictions_skipped(monkeypatch):
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        rebuild_derived_data,
        "run_backtest",
        lambda **kwargs: events.append(("backtest", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "save_aggregate_accuracy",
        lambda **kwargs: events.append(("aggregate", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "validate_predictions",
        lambda bands, max_age_hours: events.append(("validate", bands[0])) or 0,
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "validate_accuracy",
        lambda bands, max_age_hours: events.append(("validate_accuracy", bands[0]))
        or 0,
    )

    rebuild_derived_data.rebuild_band_outputs(
        band="goose",
        rebuild_predictions=False,
        rebuild_accuracy=True,
        clear_existing=False,
        start=None,
        end=None,
        recent_shows=50,
        aggregate_shows=50,
        max_age_hours=72,
    )

    assert events == [
        ("backtest", "notebook"),
        ("aggregate", "notebook"),
        ("backtest", "ckplus"),
        ("aggregate", "ckplus"),
        ("validate_accuracy", "goose"),
    ]


def test_rebuild_band_outputs_clears_one_model_at_a_time(monkeypatch):
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        rebuild_derived_data,
        "clear_model_outputs",
        lambda **kwargs: events.append(("clear", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "generate_predictions",
        lambda **kwargs: events.append(("predict", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "run_backtest",
        lambda **kwargs: events.append(("backtest", kwargs["model"])),
    )
    monkeypatch.setattr(
        rebuild_derived_data,
        "save_aggregate_accuracy",
        lambda **kwargs: events.append(("aggregate", kwargs["model"])),
    )
    monkeypatch.setattr(rebuild_derived_data, "validate_predictions", lambda *args, **kwargs: 0)
    monkeypatch.setattr(rebuild_derived_data, "validate_accuracy", lambda *args, **kwargs: 0)

    rebuild_derived_data.rebuild_band_outputs(
        band="goose",
        rebuild_predictions=True,
        rebuild_accuracy=True,
        clear_existing=True,
        start=None,
        end=None,
        recent_shows=25,
        aggregate_shows=25,
        max_age_hours=72,
    )

    assert events[:8] == [
        ("clear", "notebook"),
        ("predict", "notebook"),
        ("backtest", "notebook"),
        ("aggregate", "notebook"),
        ("clear", "ckplus"),
        ("predict", "ckplus"),
        ("backtest", "ckplus"),
        ("aggregate", "ckplus"),
    ]


def test_clear_existing_outputs_deletes_selected_rows(monkeypatch):
    events: list[tuple[str, str, str]] = []

    class _QueryStub:
        def __init__(self, table_name: str):
            self.table_name = table_name

        def delete(self):
            return self

        def eq(self, column: str, value: str):
            events.append((self.table_name, column, value))
            return self

        def execute(self):
            return None

    class _ClientStub:
        def table(self, name: str):
            return _QueryStub(name)

    monkeypatch.setattr(
        rebuild_derived_data, "get_supabase_client", lambda: _ClientStub()
    )

    rebuild_derived_data.clear_existing_outputs(
        bands=["goose"],
        clear_predictions=True,
        clear_accuracy=True,
    )

    assert ("predictions_notebook", "band", "goose") in events
    assert ("predictions_ckplus", "band", "goose") in events
    assert ("prediction_songs", "band", "goose") in events
    assert ("accuracy_per_show", "band", "goose") in events
    assert ("notebook_accuracy", "band", "goose") in events
    assert ("accuracy_ckplus", "band", "goose") in events
