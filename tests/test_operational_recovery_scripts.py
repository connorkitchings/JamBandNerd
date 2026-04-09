from __future__ import annotations

import json
from datetime import datetime

from scripts import audit_raw_data, rebuild_derived_data
from scripts import rebuild_prediction_songs as rebuild_prediction_projection


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
    monkeypatch.setattr(
        rebuild_derived_data, "validate_predictions", lambda *args, **kwargs: 0
    )
    monkeypatch.setattr(
        rebuild_derived_data, "validate_accuracy", lambda *args, **kwargs: 0
    )

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
    assert ("historical_prediction_runs", "band", "goose") in events
    assert ("accuracy_per_show", "band", "goose") in events
    assert ("notebook_accuracy", "band", "goose") in events
    assert ("accuracy_ckplus", "band", "goose") in events


def test_rebuild_prediction_songs_bounded_window_rebuilds_multiple_dates(monkeypatch):
    replace_calls: list[dict[str, object]] = []
    deleted_refs: list[str] = []
    refreshed_at = "2026-04-09T13:45:00+00:00"

    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, table_name: str, rows_by_table: dict[str, list[dict]]):
            self.table_name = table_name
            self.rows_by_table = rows_by_table
            self._filters: list[tuple[str, str, object]] = []
            self._orders: list[tuple[str, bool]] = []
            self._limit: int | None = None
            self._mode = "select"

        def select(self, *_args, **_kwargs):
            self._mode = "select"
            return self

        def delete(self):
            self._mode = "delete"
            return self

        def eq(self, column: str, value: object):
            self._filters.append(("eq", column, value))
            return self

        def gte(self, column: str, value: object):
            self._filters.append(("gte", column, value))
            return self

        def lte(self, column: str, value: object):
            self._filters.append(("lte", column, value))
            return self

        def order(self, column: str, desc: bool = False):
            self._orders.append((column, desc))
            return self

        def limit(self, value: int):
            self._limit = value
            return self

        def _matches(self, row: dict) -> bool:
            for op, column, value in self._filters:
                row_value = row.get(column)
                if op == "eq" and row_value != value:
                    return False
                if op == "gte" and (row_value is None or row_value < value):
                    return False
                if op == "lte" and (row_value is None or row_value > value):
                    return False
            return True

        def execute(self):
            source_rows = self.rows_by_table.get(self.table_name, [])
            rows = [row for row in source_rows if self._matches(row)]
            for column, desc in reversed(self._orders):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]

            if self._mode == "delete":
                kept = [row for row in source_rows if not self._matches(row)]
                self.rows_by_table[self.table_name] = kept
                deleted_refs.extend(
                    str(row.get("reference_date"))
                    for row in rows
                    if row.get("reference_date") is not None
                )
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, rows_by_table: dict[str, list[dict]]):
            self.rows_by_table = rows_by_table

        def table(self, name: str):
            return _QueryStub(name, self.rows_by_table)

    rows_by_table = {
        "predictions_notebook": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-01",
                "predicted_at": "2026-04-08T19:30:01+00:00",
                "top_k": 1,
                "predictions": json.dumps([{"rank": 1, "song_name": "Arcadia"}]),
            },
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-02",
                "predicted_at": "2026-04-08T19:30:02+00:00",
                "top_k": 1,
                "predictions": json.dumps([{"rank": 1, "song_name": "Madhuvan"}]),
            },
        ],
        "prediction_songs": [
            {
                "band": "goose",
                "model_slug": "notebook",
                "model_version": "notebook_v1",
                "reference_date": "2026-03-31",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
            {
                "band": "goose",
                "model_slug": "notebook",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-01",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
            {
                "band": "goose",
                "model_slug": "notebook",
                "model_version": "notebook_v0",
                "reference_date": "2026-04-02",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
            {
                "band": "goose",
                "model_slug": "ckplus",
                "model_version": "ckplus_v1",
                "reference_date": "2026-04-01",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
        ],
    }

    monkeypatch.setattr(
        rebuild_prediction_projection,
        "get_supabase_client",
        lambda: _ClientStub(rows_by_table),
    )
    monkeypatch.setattr(
        rebuild_prediction_projection,
        "datetime",
        type(
            "_FrozenDateTime",
            (),
            {
                "now": staticmethod(
                    lambda tz=None: datetime(2026, 4, 9, 13, 45, tzinfo=tz)
                )
            },
        ),
    )
    monkeypatch.setattr(
        rebuild_prediction_projection,
        "replace_prediction_projection",
        lambda **kwargs: replace_calls.append(kwargs),
    )

    rebuild_prediction_projection.rebuild_prediction_songs(
        band="goose",
        model="notebook",
        reference_date_from="2026-04-01",
        reference_date_to="2026-04-02",
    )

    assert [call["reference_date"] for call in replace_calls] == [
        "2026-04-01",
        "2026-04-02",
    ]
    assert [call["predicted_at"] for call in replace_calls] == [
        refreshed_at,
        refreshed_at,
    ]
    assert deleted_refs == ["2026-04-01", "2026-04-02"]
    assert rows_by_table["prediction_songs"] == [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-31",
            "predicted_at": "2026-04-01T00:00:00+00:00",
        },
        {
            "band": "goose",
            "model_slug": "ckplus",
            "model_version": "ckplus_v1",
            "reference_date": "2026-04-01",
            "predicted_at": "2026-04-01T00:00:00+00:00",
        },
    ]


def test_rebuild_prediction_songs_bounded_window_deletes_orphans(monkeypatch):
    replace_calls: list[str] = []

    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, table_name: str, rows_by_table: dict[str, list[dict]]):
            self.table_name = table_name
            self.rows_by_table = rows_by_table
            self._filters: list[tuple[str, str, object]] = []
            self._mode = "select"

        def select(self, *_args, **_kwargs):
            self._mode = "select"
            return self

        def delete(self):
            self._mode = "delete"
            return self

        def eq(self, column: str, value: object):
            self._filters.append(("eq", column, value))
            return self

        def gte(self, column: str, value: object):
            self._filters.append(("gte", column, value))
            return self

        def lte(self, column: str, value: object):
            self._filters.append(("lte", column, value))
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def _matches(self, row: dict) -> bool:
            for op, column, value in self._filters:
                row_value = row.get(column)
                if op == "eq" and row_value != value:
                    return False
                if op == "gte" and (row_value is None or row_value < value):
                    return False
                if op == "lte" and (row_value is None or row_value > value):
                    return False
            return True

        def execute(self):
            source_rows = self.rows_by_table.get(self.table_name, [])
            rows = [row for row in source_rows if self._matches(row)]
            if self._mode == "delete":
                self.rows_by_table[self.table_name] = [
                    row for row in source_rows if not self._matches(row)
                ]
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, rows_by_table: dict[str, list[dict]]):
            self.rows_by_table = rows_by_table

        def table(self, name: str):
            return _QueryStub(name, self.rows_by_table)

    rows_by_table = {
        "predictions_notebook": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-01",
                "predicted_at": "2026-04-08T19:30:01+00:00",
                "top_k": 1,
                "predictions": json.dumps([{"rank": 1, "song_name": "Arcadia"}]),
            }
        ],
        "prediction_songs": [
            {
                "band": "goose",
                "model_slug": "notebook",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-01",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
            {
                "band": "goose",
                "model_slug": "notebook",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-02",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
            {
                "band": "goose",
                "model_slug": "notebook",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-03",
                "predicted_at": "2026-04-01T00:00:00+00:00",
            },
        ],
    }

    monkeypatch.setattr(
        rebuild_prediction_projection,
        "get_supabase_client",
        lambda: _ClientStub(rows_by_table),
    )
    monkeypatch.setattr(
        rebuild_prediction_projection,
        "replace_prediction_projection",
        lambda **kwargs: replace_calls.append(str(kwargs["reference_date"])),
    )

    rebuild_prediction_projection.rebuild_prediction_songs(
        band="goose",
        model="notebook",
        reference_date_from="2026-04-01",
        reference_date_to="2026-04-02",
    )

    assert replace_calls == ["2026-04-01"]
    assert rows_by_table["prediction_songs"] == [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-04-03",
            "predicted_at": "2026-04-01T00:00:00+00:00",
        }
    ]


def test_rebuild_prediction_songs_legacy_mode_rebuilds_latest_only(monkeypatch):
    replace_calls: list[dict[str, object]] = []
    delete_called = False

    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, table_name: str, rows_by_table: dict[str, list[dict]]):
            self.table_name = table_name
            self.rows_by_table = rows_by_table
            self._filters: list[tuple[str, object]] = []
            self._orders: list[tuple[str, bool]] = []
            self._limit: int | None = None
            self._mode = "select"

        def select(self, *_args, **_kwargs):
            self._mode = "select"
            return self

        def delete(self):
            nonlocal delete_called
            delete_called = True
            self._mode = "delete"
            return self

        def eq(self, column: str, value: object):
            self._filters.append((column, value))
            return self

        def order(self, column: str, desc: bool = False):
            self._orders.append((column, desc))
            return self

        def limit(self, value: int):
            self._limit = value
            return self

        def execute(self):
            rows = list(self.rows_by_table.get(self.table_name, []))
            for column, value in self._filters:
                rows = [row for row in rows if row.get(column) == value]
            for column, desc in reversed(self._orders):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, rows_by_table: dict[str, list[dict]]):
            self.rows_by_table = rows_by_table

        def table(self, name: str):
            return _QueryStub(name, self.rows_by_table)

    rows_by_table = {
        "predictions_notebook": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-01",
                "predicted_at": "2026-04-08T19:30:01+00:00",
                "top_k": 1,
                "predictions": json.dumps([{"rank": 1, "song_name": "Arcadia"}]),
            },
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-04-02",
                "predicted_at": "2026-04-08T19:30:02+00:00",
                "top_k": 1,
                "predictions": json.dumps([{"rank": 1, "song_name": "Madhuvan"}]),
            },
        ]
    }

    monkeypatch.setattr(
        rebuild_prediction_projection,
        "get_supabase_client",
        lambda: _ClientStub(rows_by_table),
    )
    monkeypatch.setattr(
        rebuild_prediction_projection,
        "replace_prediction_projection",
        lambda **kwargs: replace_calls.append(kwargs),
    )

    rebuild_prediction_projection.rebuild_prediction_songs(
        band="goose",
        model="notebook",
    )

    assert [call["reference_date"] for call in replace_calls] == ["2026-04-02"]
    assert replace_calls[0]["predicted_at"] == "2026-04-08T19:30:02+00:00"
    assert delete_called is False
