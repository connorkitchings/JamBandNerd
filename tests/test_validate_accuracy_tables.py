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
        self._orders: list[tuple[str, bool]] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: str):
        self._filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False, **_kwargs):
        self._orders.append((column, desc))
        return self

    def limit(self, *_args, **_kwargs):
        if _args:
            self._limit = int(_args[0])
        return self

    def execute(self):
        rows = list(self._rows)
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        for column, desc in reversed(self._orders):
            rows.sort(key=lambda row: row.get(column) or "", reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return _ResponseStub(rows)


class _ClientStub:
    def __init__(self, table_rows):
        self._table_rows = table_rows

    def table(self, name: str):
        return _QueryStub(self._table_rows.get(name, []))


def _repeat_rows(
    *,
    stale_hours: int = 0,
    count: int = 50,
    with_lineage: bool = True,
    actual_song_count: int = 12,
):
    now = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
    rows = []
    for index in range(count):
        rows.append(
            {
                "band": "goose",
                "model_version": "goose_baseline_v1",
                "evaluated_at": now.isoformat(),
                "show_date": f"2026-03-{index + 1:02d}",
                "prediction_run_id": 1000 + index if with_lineage else None,
                "actual_song_count": actual_song_count,
            }
        )
    return {"setlist_accuracy": rows}


def test_validate_accuracy_passes_for_fresh_rows(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_repeat_rows()),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0


def test_validate_accuracy_fails_for_stale_rows(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_repeat_rows(stale_hours=96)),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 1


def test_validate_accuracy_fails_when_replay_lineage_missing(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_repeat_rows(with_lineage=False)),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 1


def test_validate_accuracy_respects_global_replay_window_override(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_repeat_rows(count=10)),
    )

    failures = validate_accuracy(
        bands=["goose"],
        max_age_hours=72,
        replay_window=10,
    )

    assert failures == 0


def test_skip_freshness_passes_stale_rows(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(_repeat_rows(stale_hours=96)),
    )

    failures = validate_accuracy(
        bands=["goose"],
        max_age_hours=72,
        skip_freshness=True,
    )

    assert failures == 0


def test_skip_freshness_fails_missing_rows(monkeypatch):
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub({"setlist_accuracy": []}),
    )

    failures = validate_accuracy(
        bands=["goose"],
        max_age_hours=72,
        skip_freshness=True,
    )

    assert failures == 2
