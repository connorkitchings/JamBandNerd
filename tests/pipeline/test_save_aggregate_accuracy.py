from __future__ import annotations

from dataclasses import replace

import pytest

from scripts import save_aggregate_accuracy as module
from src.jambandnerd.models.registry import get_model_definition


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []
        self._limit = None
        self.upsert_calls = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def upsert(self, record, on_conflict):
        self.upsert_calls.append({"record": record, "on_conflict": on_conflict})
        return self

    def execute(self):
        rows = list(self._rows)
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _ResponseStub(rows)


class _ClientStub:
    def __init__(self, table_rows):
        self._table_rows = table_rows
        self.queries: dict[str, _QueryStub] = {}

    def table(self, name):
        query = self.queries.get(name)
        if query is None:
            query = _QueryStub(self._table_rows.get(name, []))
            self.queries[name] = query
        return query


def test_save_aggregate_accuracy_uses_registry_version_and_table(monkeypatch):
    per_show_rows = [
        {
            "band": "goose",
            "model_version": "custom_notebook_v9",
            "show_date": "2026-03-20",
            "k10_hit": 1,
            "k10_matches": 3,
            "k10_precision": 0.3,
            "k10_recall": 0.2,
            "k10_f1": 0.24,
            "k25_hit": 1,
            "k25_matches": 5,
            "k25_precision": 0.2,
            "k25_recall": 0.4,
            "k25_f1": 0.27,
            "k50_hit": 1,
            "k50_matches": 8,
            "k50_precision": 0.16,
            "k50_recall": 0.6,
            "k50_f1": 0.25,
        }
    ]
    client = _ClientStub({"accuracy_per_show": per_show_rows})

    monkeypatch.setattr(module, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(get_model_definition("notebook"), version="custom_notebook_v9"),
    )
    monkeypatch.setattr(
        module,
        "get_aggregate_accuracy_table",
        lambda slug: "accuracy_notebook_custom",
    )

    module.save_aggregate_accuracy("goose", "notebook", 10)

    upsert_calls = client.queries["accuracy_notebook_custom"].upsert_calls
    assert len(upsert_calls) == 1
    assert upsert_calls[0]["record"]["model_version"] == "custom_notebook_v9"


def test_main_rejects_model_not_in_aggregate_choices(monkeypatch):
    monkeypatch.setattr(module, "list_aggregate_accuracy_models", lambda: [get_model_definition("notebook")])
    monkeypatch.setattr(
        module,
        "save_aggregate_accuracy",
        lambda **kwargs: pytest.fail("save_aggregate_accuracy should not run"),
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        [
            "save_aggregate_accuracy.py",
            "--band",
            "goose",
            "--model",
            "deal",
        ],
    )

    with pytest.raises(SystemExit):
        module.main()

