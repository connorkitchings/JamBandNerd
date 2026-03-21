from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.validate_accuracy_tables import validate_accuracy


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, rows):
        self._rows = rows
        self._filters: list[tuple[str, str]] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: str):
        self._filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = list(self._rows)
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        return _ResponseStub(rows[:1])


class _ClientStub:
    def __init__(self, table_rows):
        self._table_rows = table_rows

    def table(self, name: str):
        return _QueryStub(self._table_rows.get(name, []))


def _accuracy_rows(*, stale_hours: int = 0):
    now = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
    iso = now.isoformat()
    return {
        "accuracy_per_show": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "evaluated_at": iso,
                "show_date": "2026-03-20",
            },
            {
                "band": "goose",
                "model_version": "ckplus_v1",
                "evaluated_at": iso,
                "show_date": "2026-03-20",
            },
        ],
        "notebook_accuracy": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "evaluated_at": iso,
                "window_start": "2025-01-01",
                "window_end": "2026-03-20",
            }
        ],
        "accuracy_ckplus": [
            {
                "band": "goose",
                "model_version": "ckplus_v1",
                "evaluated_at": iso,
                "window_start": "2025-01-01",
                "window_end": "2026-03-20",
            }
        ],
    }


def test_validate_accuracy_passes_for_fresh_rows(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_accuracy_rows()),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0


def test_validate_accuracy_fails_for_stale_rows(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_accuracy_rows(stale_hours=96)),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 4


def test_validate_accuracy_fails_when_aggregate_missing(monkeypatch):
    rows = _accuracy_rows()
    rows["accuracy_ckplus"] = []
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 1


def test_validate_accuracy_skip_aggregate_check(monkeypatch):
    rows = _accuracy_rows()
    rows["accuracy_ckplus"] = []
    rows["notebook_accuracy"] = []
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(
        bands=["goose"], max_age_hours=72, validate_aggregate=False
    )

    assert failures == 0
