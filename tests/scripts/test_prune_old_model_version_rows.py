from __future__ import annotations

import json
from pathlib import Path

from scripts.admin import prune_old_model_version_rows as prune


class _Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters: list[tuple[str, str, object]] = []
        self.mode = "select"
        self.window: tuple[int, int] | None = None
        self.max_rows: int | None = None

    def select(self, *_):
        return self

    def delete(self):
        self.mode = "delete"
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self.filters.append(("neq", col, val))
        return self

    def limit(self, n):
        self.max_rows = n
        return self

    def range(self, a, b):
        self.window = (a, b)
        return self

    def _match(self, row):
        return all(
            (row.get(c) == v) if op == "eq" else (row.get(c) != v)
            for op, c, v in self.filters
        )

    def execute(self):
        rows = self.db.tables[self.table]
        hits = [r for r in rows if self._match(r)]
        if self.mode == "delete":
            self.db.deletes.append(self.table)
            self.db.tables[self.table] = [r for r in rows if r not in hits]
        if self.window:
            hits = hits[self.window[0] : self.window[1] + 1]
        if self.max_rows is not None:
            hits = hits[: self.max_rows]
        return type("R", (), {"data": hits})()


class _FakeClient:
    def __init__(self, tables):
        self.tables = {t: list(tables.get(t, [])) for t in prune.TABLES}
        self.deletes: list[str] = []

    def table(self, name):
        return _Query(self, name)


def _tables(with_current: bool = True):
    preds = [{"id": 1, "band": "wsp", "model_version": "old"}]
    if with_current:
        preds.append({"id": 2, "band": "wsp", "model_version": "new"})
    return {
        "setlist_predictions": preds,
        "setlist_prediction_songs": [
            {"band": "wsp", "model_version": "old", "song_name": "A"},
            {"band": "wsp", "model_version": "new", "song_name": "B"},
        ],
        "setlist_results": [{"band": "wsp", "model_version": "old"}],
        "setlist_accuracy": [{"band": "phish", "model_version": "old"}],
    }


def test_dry_run_deletes_nothing_and_writes_no_backup(tmp_path: Path):
    client = _FakeClient(_tables())

    counts = prune.prune_band(client, "wsp", "new", apply=False, backup_dir=tmp_path)

    assert counts["setlist_predictions"] == 1
    assert client.deletes == []
    assert list(tmp_path.iterdir()) == []


def test_band_without_current_board_is_skipped(tmp_path: Path):
    client = _FakeClient(_tables(with_current=False))

    counts = prune.prune_band(client, "wsp", "new", apply=True, backup_dir=tmp_path)

    assert counts is None
    assert client.deletes == []
    assert list(tmp_path.iterdir()) == []


def test_apply_backs_up_then_deletes_only_this_bands_other_versions(tmp_path: Path):
    client = _FakeClient(_tables())

    counts = prune.prune_band(client, "wsp", "new", apply=True, backup_dir=tmp_path)

    assert counts == {
        "setlist_prediction_songs": 1,
        "setlist_predictions": 1,
        "setlist_accuracy": 0,
        "setlist_results": 1,
    }
    (backup,) = tmp_path.iterdir()
    saved = json.loads(backup.read_text())
    assert saved["rows"]["setlist_predictions"][0]["id"] == 1
    assert [r["model_version"] for r in client.tables["setlist_predictions"]] == ["new"]
    assert client.tables["setlist_accuracy"] == _tables()["setlist_accuracy"]
