from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from scripts import collection_preflight


def test_decide_collection_execution_mode_keeps_mutable_sources_on_daily_refresh():
    execution_mode, should_run_collection = (
        collection_preflight.decide_collection_execution_mode(
            collection_mode="always_refresh",
            recent_completed_show_count=0,
            missing_recent_setlist_count=0,
            upcoming_show_count=0,
            allows_verify_only_when_idle=False,
        )
    )

    assert execution_mode == "full_refresh"
    assert should_run_collection is True


def test_compute_band_preflight_runs_when_recent_show_has_missing_setlist(monkeypatch):
    client = object()
    monkeypatch.setattr(collection_preflight, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        collection_preflight,
        "get_collection_policy",
        lambda _band: SimpleNamespace(
            collection_mode="window_refresh",
            upcoming_lookahead_days=14,
            supports_upstream_update_timestamp=True,
            skip_existing_setlists=True,
            allows_verify_only_when_idle=False,
        ),
    )
    monkeypatch.setattr(
        collection_preflight, "get_band_id_column", lambda _band: "show_id"
    )

    def fetch_rows(table_name, **_kwargs):
        if table_name.endswith("_shows_raw"):
            return [{"show_id": "show-1", "show_date": "2026-03-16"}]
        return []

    monkeypatch.setattr(collection_preflight, "fetch_table_rows", fetch_rows)
    monkeypatch.setattr(
        collection_preflight,
        "fetch_column_values_for_ids",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        collection_preflight,
        "_fetch_last_successful_collection_at",
        lambda **_kwargs: "2026-03-15T12:00:00+00:00",
    )

    preflight = collection_preflight.compute_band_preflight(
        "um", today=date(2026, 3, 17), client=client
    )

    assert preflight.execution_mode == "bounded_refresh"
    assert preflight.should_run_collection is True
    assert preflight.missing_recent_setlist_count == 1


def test_compute_band_preflight_allows_verify_only_for_idle_policy(monkeypatch):
    client = object()
    monkeypatch.setattr(collection_preflight, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        collection_preflight,
        "get_collection_policy",
        lambda _band: SimpleNamespace(
            collection_mode="verify_only_when_idle",
            upcoming_lookahead_days=14,
            supports_upstream_update_timestamp=False,
            skip_existing_setlists=False,
            allows_verify_only_when_idle=True,
        ),
    )
    monkeypatch.setattr(
        collection_preflight, "get_band_id_column", lambda _band: "show_id"
    )
    monkeypatch.setattr(
        collection_preflight, "fetch_table_rows", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        collection_preflight,
        "fetch_column_values_for_ids",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        collection_preflight,
        "_fetch_last_successful_collection_at",
        lambda **_kwargs: None,
    )

    preflight = collection_preflight.compute_band_preflight(
        "custom", today=date(2026, 3, 17), client=client
    )

    assert preflight.execution_mode == "verify_only"
    assert preflight.should_run_collection is False
