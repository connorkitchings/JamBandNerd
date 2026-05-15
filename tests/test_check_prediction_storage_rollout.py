from __future__ import annotations

from unittest.mock import MagicMock

from scripts import check_prediction_storage_rollout as module


class _ResponseStub:
    def __init__(self, *, count: int = 0):
        self.count = count
        self.data = []


class _QueryStub:
    def __init__(
        self, *, table: str, rows_by_table: dict[str, list[dict[str, object]]]
    ):
        self._table = table
        self._rows_by_table = rows_by_table
        self._filters: list[tuple[str, object]] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: object):
        self._filters.append((column, value))
        return self

    def limit(self, _value: int):
        return self

    def execute(self):
        if self._table not in self._rows_by_table:
            raise RuntimeError(f"missing table: {self._table}")
        rows = list(self._rows_by_table[self._table])
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        return _ResponseStub(count=len(rows))


class _ClientStub:
    def __init__(self, rows_by_table: dict[str, list[dict[str, object]]]):
        self._rows_by_table = rows_by_table

    def table(self, name: str):
        return _QueryStub(table=name, rows_by_table=self._rows_by_table)


def _empty_rows() -> dict[str, list[dict[str, object]]]:
    return {table: [] for table in module.TABLE_REQUIRED_COLUMNS}


def test_rollout_checker_passes_empty_tables(monkeypatch):
    monkeypatch.setattr(module, "get_table_schema", lambda table: [])

    report = module.check_prediction_storage_rollout(
        bands=["goose"],
        expected_state="empty",
        client=_ClientStub(_empty_rows()),
    )

    assert report.state == "ok"
    assert report.tables[0].row_count == 0
    assert len(report.band_models) == 1
    assert report.band_models[0].setlist_predictions == 0


def test_rollout_checker_fails_empty_state_when_rows_exist(monkeypatch):
    monkeypatch.setattr(module, "get_table_schema", lambda table: [])
    rows = _empty_rows()
    rows[module.SETLIST_PREDICTIONS_TABLE] = [
        {
            "id": 1,
            "band": "goose",
            "model_version": "goose_baseline_v1",
        }
    ]

    report = module.check_prediction_storage_rollout(
        bands=["goose"],
        expected_state="empty",
        client=_ClientStub(rows),
    )

    assert report.state == "failed"
    assert "setlist_predictions:expected_empty:1" in report.blockers


def test_rollout_checker_fails_on_missing_table(monkeypatch):
    monkeypatch.setattr(module, "get_table_schema", lambda table: [])
    rows = _empty_rows()
    del rows[module.SETLIST_ACCURACY_TABLE]

    report = module.check_prediction_storage_rollout(
        bands=["goose"],
        expected_state="any",
        client=_ClientStub(rows),
    )

    assert report.state == "failed"
    assert any(
        blocker.startswith("setlist_accuracy:not_readable")
        for blocker in report.blockers
    )


def test_rollout_checker_fails_on_rpc_schema_mismatch(monkeypatch):
    def schema(table: str):
        return [
            {"column_name": column}
            for column in module.TABLE_REQUIRED_COLUMNS[table]
            if column != "target_show_key"
        ]

    monkeypatch.setattr(module, "get_table_schema", schema)

    report = module.check_prediction_storage_rollout(
        bands=["goose"],
        expected_state="empty",
        client=_ClientStub(_empty_rows()),
    )

    assert report.state == "failed"
    assert any(
        "schema_missing_columns:target_show_key" in item for item in report.blockers
    )


def test_rollout_checker_populated_state_runs_production_audit(monkeypatch):
    monkeypatch.setattr(module, "get_table_schema", lambda table: [])
    audit = MagicMock(state="failed", blockers=("goose:missing",), warnings=())
    monkeypatch.setattr(module, "run_supabase_audit", lambda bands: audit)

    report = module.check_prediction_storage_rollout(
        bands=["goose"],
        expected_state="populated",
        client=_ClientStub(_empty_rows()),
    )

    assert report.state == "failed"
    assert report.production_audit_state == "failed"
    assert "production_audit:goose:missing" in report.blockers
