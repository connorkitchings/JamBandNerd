from __future__ import annotations

from jambandnerd.config import bands as band_config


def _reset_band_caches() -> None:
    band_config._cached_registry_band_rows = None
    band_config._cached_runtime_band_id_columns = None


def test_repo_supported_bands_are_repo_authoritative() -> None:
    assert tuple(band_config.get_repo_supported_bands()) == band_config.SUPPORTED_BANDS
    assert (
        tuple(band_config.get_repo_collectable_bands()) == band_config.SUPPORTED_BANDS
    )


def test_band_scopes_are_explicit_and_consistent() -> None:
    assert tuple(band_config.get_repo_active_model_bands()) == (
        band_config.ACTIVE_MODEL_BANDS
    )
    assert tuple(band_config.get_daily_pipeline_bands()) == (
        band_config.DAILY_PIPELINE_BANDS
    )
    assert set(band_config.ACTIVE_MODEL_BANDS).issubset(band_config.SUPPORTED_BANDS)
    assert set(band_config.DAILY_PIPELINE_BANDS).issubset(
        band_config.ACTIVE_MODEL_BANDS
    )
    assert "eggy" in band_config.SUPPORTED_BANDS
    assert "eggy" not in band_config.ACTIVE_MODEL_BANDS
    assert "eggy" not in band_config.DAILY_PIPELINE_BANDS


def test_runtime_band_metadata_prefers_registry(monkeypatch) -> None:
    _reset_band_caches()
    monkeypatch.setattr(
        "jambandnerd.db.operations.fetch_active_bands",
        lambda: [
            {"slug": "goose", "id_column": "show_id"},
            {"slug": "phish", "id_column": "show_id"},
        ],
    )

    assert list(band_config.get_registry_active_band_slugs()) == ["goose", "phish"]
    assert band_config.get_runtime_band_id_column("phish") == "show_id"


def test_runtime_band_metadata_falls_back_to_repo_defaults(monkeypatch) -> None:
    _reset_band_caches()
    monkeypatch.setattr("jambandnerd.db.operations.fetch_active_bands", lambda: [])

    assert tuple(band_config.get_registry_active_band_slugs()) == (
        band_config.SUPPORTED_BANDS
    )
    assert band_config.get_runtime_band_id_column("um") == "show_id"
    assert band_config.get_repo_band_id_column("um") == "show_id"
