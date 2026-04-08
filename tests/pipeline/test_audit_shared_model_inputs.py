from __future__ import annotations

import json

import pytest

from scripts import audit_shared_model_inputs as module


def test_audit_shared_model_inputs_reports_universal_field_presence(monkeypatch):
    def fetch_table(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
        if table_name.endswith("_shows_raw"):
            return [
                {
                    "show_id": "show-1",
                    "show_date": "2024-01-01",
                    "venue_name": "Venue",
                    "state": "TN",
                }
            ]
        if table_name.endswith("_setlists_raw"):
            return [{"show_id": "show-1", "song_name": "Song A"}]
        raise AssertionError(f"Unexpected table: {table_name}")

    monkeypatch.setattr(module, "fetch_table", fetch_table)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )

    report = module.audit_bands(["goose", "phish"])

    assert report["bands"]["goose"]["show_fields"]["venue_name"]["present"] is True
    assert report["universal_show_fields"]["venue_name"]["present_in_all_bands"] is True
    assert report["universal_show_fields"]["city"]["present_in_all_bands"] is False


def test_write_report_output_writes_non_empty_json(tmp_path):
    output_path = tmp_path / "audit.json"
    report = {"bands": {"goose": {"status": "ok"}}, "universal_show_fields": {}}

    module.write_report_output(output_path, report)

    payload = json.loads(output_path.read_text())
    assert payload == report
    assert output_path.stat().st_size > 0


def test_write_report_output_raises_on_write_errors(tmp_path, monkeypatch):
    output_path = tmp_path / "audit.json"
    report = {"bands": {}, "universal_show_fields": {}}

    def boom(self, content, *args, **kwargs):  # noqa: ARG001
        raise OSError("disk full")

    monkeypatch.setattr(module.Path, "write_text", boom)

    with pytest.raises(OSError):
        module.write_report_output(output_path, report)
