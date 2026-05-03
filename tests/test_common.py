from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import common


def test_ensure_source_reachable_fails_after_repeated_429(monkeypatch):
    responses = [SimpleNamespace(status_code=429) for _ in range(3)]
    calls = []

    def fake_get(*_args, **_kwargs):
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr(common.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(RuntimeError, match="transient status 429"):
        common.ensure_source_reachable("goose")

    assert len(calls) == 3


def test_ensure_source_reachable_succeeds_after_transient_retry(monkeypatch):
    responses = [SimpleNamespace(status_code=503), SimpleNamespace(status_code=200)]
    calls = []

    def fake_get(*_args, **_kwargs):
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr(common.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("requests.get", fake_get)

    common.ensure_source_reachable("goose")

    assert len(calls) == 2
