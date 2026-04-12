from __future__ import annotations

from pathlib import Path

from scripts import common as common_module
from src.jambandnerd.db import table_snapshots as snapshot_module


def test_write_and_load_table_snapshot_roundtrip(tmp_path: Path) -> None:
    rows = [{"show_id": "goose-1", "show_date": "2024-01-01"}]

    snapshot_module.write_table_snapshot("goose_shows_raw", rows, tmp_path)
    loaded = snapshot_module.load_table_snapshot("goose_shows_raw", tmp_path)

    assert loaded == rows


def test_fetch_table_prefers_local_snapshot(tmp_path: Path) -> None:
    rows = [{"show_id": "goose-1", "show_date": "2024-01-01"}]
    snapshot_module.write_table_snapshot("goose_shows_raw", rows, tmp_path)

    loaded = common_module.fetch_table("goose_shows_raw", snapshot_root=str(tmp_path))

    assert loaded == rows


def test_export_tables_to_snapshot_writes_manifest(monkeypatch, tmp_path: Path) -> None:
    table_rows = {
        "goose_shows_raw": [{"show_id": "goose-1"}],
        "goose_setlists_raw": [{"show_id": "goose-1", "song_name": "Song A"}],
    }

    def fake_fetch_table(table_name: str, chunk_size: int = 10000, *, snapshot_root=None):  # noqa: ARG001
        return table_rows[table_name]

    monkeypatch.setattr(common_module, "fetch_table", fake_fetch_table)

    manifest = common_module.export_tables_to_snapshot(
        ["goose_shows_raw", "goose_setlists_raw"],
        snapshot_root=str(tmp_path),
    )

    assert sorted(manifest["tables"].keys()) == [
        "goose_setlists_raw",
        "goose_shows_raw",
    ]
    assert manifest["tables"]["goose_shows_raw"]["row_count"] == 1
    assert (tmp_path / "manifest.json").exists()
