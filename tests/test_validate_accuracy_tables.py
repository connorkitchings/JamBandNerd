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
        self._limit: int | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: str):
        self._filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        if _args:
            self._limit = int(_args[0])
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
                "prediction_run_id": 101,
                "actual_song_count": 12,
            },
            {
                "band": "goose",
                "model_version": "ckplus_v1",
                "evaluated_at": iso,
                "show_date": "2026-03-20",
                "prediction_run_id": 201,
                "actual_song_count": 12,
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


def test_validate_accuracy_fails_when_replay_lineage_missing(monkeypatch):
    rows = _accuracy_rows()
    rows["accuracy_per_show"][0]["prediction_run_id"] = None
    rows["accuracy_per_show"][1]["prediction_run_id"] = None
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 2


def test_validate_accuracy_ignores_sparse_recent_rows_for_replay_lineage(monkeypatch):
    rows = _accuracy_rows()
    rows["accuracy_per_show"] = [
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "evaluated_at": rows["accuracy_per_show"][0]["evaluated_at"],
            "show_date": "2026-03-21",
            "prediction_run_id": None,
            "actual_song_count": 1,
        },
        rows["accuracy_per_show"][0],
        {
            "band": "goose",
            "model_version": "ckplus_v1",
            "evaluated_at": rows["accuracy_per_show"][1]["evaluated_at"],
            "show_date": "2026-03-21",
            "prediction_run_id": None,
            "actual_song_count": 1,
        },
        rows["accuracy_per_show"][1],
    ]
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0


def test_validate_accuracy_prefers_lineaged_duplicate_show_date(monkeypatch):
    rows = _accuracy_rows()
    iso = rows["accuracy_per_show"][0]["evaluated_at"]
    rows["accuracy_per_show"] = [
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "evaluated_at": iso,
            "show_date": "2026-03-19",
            "prediction_run_id": None,
            "actual_song_count": 10,
        },
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "evaluated_at": iso,
            "show_date": "2026-03-19",
            "prediction_run_id": 101,
            "actual_song_count": 10,
        },
        rows["accuracy_per_show"][1],
    ]
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0
