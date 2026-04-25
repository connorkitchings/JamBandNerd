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
    notebook_row = {
        "band": "goose",
        "model_slug": "notebook",
        "model_version": "notebook_v1",
        "evaluated_at": iso,
        "show_date": "2026-03-20",
        "prediction_run_id": 101,
        "actual_song_count": 12,
    }
    deal_row = {
        "band": "goose",
        "model_slug": "deal",
        "model_version": "deal_v2",
        "evaluated_at": iso,
        "show_date": "2026-03-20",
        "prediction_run_id": 201,
        "actual_song_count": 12,
    }
    return {
        "completed_show_accuracy": _repeat_rows(notebook_row, count=50)
        + _repeat_rows(deal_row, count=50)
    }


def _repeat_rows(row: dict[str, object], *, count: int, with_lineage: bool = True):
    rows = []
    for index in range(count):
        payload = dict(row)
        payload["show_date"] = f"2026-03-{index + 1:02d}"
        payload["prediction_run_id"] = 1000 + index if with_lineage else None
        rows.append(payload)
    return rows


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

    assert failures == 2


def test_validate_accuracy_fails_when_replay_lineage_missing(monkeypatch):
    rows = _accuracy_rows()
    for row in rows["completed_show_accuracy"]:
        row["prediction_run_id"] = None
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 2


def test_validate_accuracy_ignores_sparse_recent_rows_for_replay_lineage(monkeypatch):
    rows = _accuracy_rows()
    rows["completed_show_accuracy"] = [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "evaluated_at": rows["completed_show_accuracy"][0]["evaluated_at"],
            "show_date": "2026-03-21",
            "prediction_run_id": None,
            "actual_song_count": 1,
        },
        *rows["completed_show_accuracy"],
    ]
    rows["completed_show_accuracy"].insert(
        1,
        {
            "band": "goose",
            "model_slug": "deal",
            "model_version": "deal_v2",
            "evaluated_at": rows["completed_show_accuracy"][2]["evaluated_at"],
            "show_date": "2026-03-21",
            "prediction_run_id": None,
            "actual_song_count": 1,
        },
    )
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0


def test_validate_accuracy_prefers_lineaged_duplicate_show_date(monkeypatch):
    rows = _accuracy_rows()
    iso = rows["completed_show_accuracy"][0]["evaluated_at"]
    rows["completed_show_accuracy"] = [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "evaluated_at": iso,
            "show_date": "2026-03-19",
            "prediction_run_id": None,
            "actual_song_count": 10,
        },
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "evaluated_at": iso,
            "show_date": "2026-03-19",
            "prediction_run_id": 101,
            "actual_song_count": 10,
        },
        *rows["completed_show_accuracy"],
    ]
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0


def test_validate_accuracy_uses_model_specific_replay_windows(monkeypatch):
    base_rows = _accuracy_rows()
    notebook_row = base_rows["completed_show_accuracy"][0]
    deal_row = base_rows["completed_show_accuracy"][50]
    rows = {
        "completed_show_accuracy": _repeat_rows(notebook_row, count=50)
        + _repeat_rows(deal_row, count=50)
    }
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(bands=["goose"], max_age_hours=72)

    assert failures == 0


def test_validate_accuracy_respects_global_replay_window_override(monkeypatch):
    base_rows = _accuracy_rows()
    notebook_row = base_rows["completed_show_accuracy"][0]
    deal_row = base_rows["completed_show_accuracy"][50]
    rows = {
        "completed_show_accuracy": _repeat_rows(notebook_row, count=10)
        + _repeat_rows(deal_row, count=10)
    }
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
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
        lambda: _ClientStub(_accuracy_rows(stale_hours=96)),
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
        lambda: _ClientStub({"completed_show_accuracy": []}),
    )

    failures = validate_accuracy(
        bands=["goose"],
        max_age_hours=72,
        skip_freshness=True,
    )

    assert failures == 4


def test_skip_freshness_fails_invalid_timestamp(monkeypatch):
    rows = _accuracy_rows()
    rows["completed_show_accuracy"][0]["evaluated_at"] = "not-a-timestamp"
    rows["completed_show_accuracy"][50]["evaluated_at"] = "not-a-timestamp"
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(
        bands=["goose"],
        max_age_hours=72,
        skip_freshness=True,
    )

    assert failures == 2


def test_skip_freshness_still_checks_replay_lineage(monkeypatch):
    rows = _accuracy_rows()
    for row in rows["completed_show_accuracy"]:
        row["prediction_run_id"] = None
    monkeypatch.setattr(
        "scripts.validate_accuracy_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_accuracy(
        bands=["goose"],
        max_age_hours=72,
        skip_freshness=True,
    )

    assert failures == 2
