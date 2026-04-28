from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import sync_retained_prediction_corpus as module


def test_sync_retained_prediction_corpus_passes_dry_run_to_backtests(monkeypatch):
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "list_pipeline_models",
        lambda: [
            SimpleNamespace(slug="notebook"),
            SimpleNamespace(slug="deal"),
        ],
    )
    monkeypatch.setattr(
        module,
        "run_backtest",
        lambda **kwargs: calls.append(kwargs) or 3,
    )

    total = module.sync_retained_prediction_corpus(
        band="goose",
        window=50,
        incremental=False,
        dry_run=True,
    )

    assert total == 6
    assert [call["model"] for call in calls] == ["notebook", "deal"]
    assert all(call["dry_run"] is True for call in calls)
    assert all(call["incremental"] is False for call in calls)


def test_sync_retained_prediction_corpus_scopes_to_selected_models(monkeypatch):
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "list_pipeline_models",
        lambda: [
            SimpleNamespace(slug="notebook"),
            SimpleNamespace(slug="deal"),
        ],
    )
    monkeypatch.setattr(
        module,
        "run_backtest",
        lambda **kwargs: calls.append(kwargs) or 2,
    )

    total = module.sync_retained_prediction_corpus(
        band="goose",
        models=["deal", "deal"],
        dry_run=True,
    )

    assert total == 2
    assert [call["model"] for call in calls] == ["deal"]


def test_sync_retained_prediction_corpus_rejects_unsupported_models(monkeypatch):
    monkeypatch.setattr(
        module,
        "list_pipeline_models",
        lambda: [
            SimpleNamespace(slug="notebook"),
            SimpleNamespace(slug="deal"),
        ],
    )

    with pytest.raises(ValueError, match="Unsupported retained-corpus model"):
        module.sync_retained_prediction_corpus(
            band="goose",
            models=["ckplus"],
            dry_run=True,
        )
