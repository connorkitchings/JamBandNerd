from __future__ import annotations

from scripts import sync_retained_prediction_corpus as module


def test_sync_retained_prediction_corpus_passes_dry_run_to_backtest(monkeypatch):
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "run_backtest",
        lambda **kwargs: calls.append(kwargs) or 3,
    )

    total = module.sync_retained_prediction_corpus(
        band="goose",
        window=100,
        incremental=False,
        dry_run=True,
    )

    assert total == 3
    assert calls == [
        {
            "band": "goose",
            "start": None,
            "end": None,
            "shows": 100,
            "exclusion_window": None,
            "incremental": False,
            "require_results": False,
            "prune_to_window": True,
            "dry_run": True,
        }
    ]
