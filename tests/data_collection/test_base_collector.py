"""Shared HTTP response contracts, without network requests or cache writes."""

from dataclasses import replace
from unittest.mock import Mock

import pytest
import requests

from src.jambandnerd.data_collection.config import COLLECTOR_CONFIGS
from src.jambandnerd.data_collection.goose import collector as goose


@pytest.fixture
def collector(monkeypatch):
    monkeypatch.setattr(
        goose,
        "get_collector_config",
        lambda _: replace(COLLECTOR_CONFIGS["goose"], cache_enabled=False),
    )
    instance = goose.GooseCollector()
    monkeypatch.setattr(instance.session, "get", Mock())
    return instance


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "schema changed"},
        None,
        "unexpected",
        {"data": None},
        {"data": {"id": 1}},
        {"data": "unexpected"},
        [None],
        ["record"],
        {"data": [{"id": 1}, 2]},
    ],
)
def test_invalid_record_shapes_preserve_daily_empty_return_and_record_failure(
    collector, payload
):
    response = Mock()
    response.json.return_value = payload
    collector.session.get.return_value = response
    assert collector._fetch_from_endpoint("records") == []
    assert collector._consecutive_failures == 1


@pytest.mark.parametrize(
    "payload,expected",
    [
        ([], []),
        ({"data": []}, []),
        ([{"id": 1}], [{"id": 1}]),
        ({"data": [{"id": 1}]}, [{"id": 1}]),
    ],
)
def test_valid_record_arrays_reset_failures_including_empty_results(
    collector, payload, expected
):
    collector.record_failure()
    response = Mock()
    response.json.return_value = payload
    collector.session.get.return_value = response
    assert collector._fetch_from_endpoint("records") == expected
    assert collector._consecutive_failures == 0


@pytest.mark.parametrize(
    "failure", ["parse", "http", "request", "timeout", "connection", "circuit"]
)
def test_failure_logs_redact_key_in_url_and_exception_text(collector, caplog, failure):
    endpoint = "records?apikey=mock-key"
    url = f"{collector.config.base_url}/{endpoint}"
    response = Mock(status_code=503)
    collector.session.get.return_value = response
    if failure == "parse":
        response.json.side_effect = ValueError(f"Invalid response from {url}")
    elif failure == "http":
        response.raise_for_status.side_effect = requests.HTTPError(
            f"Error at {url}", response=response
        )
    elif failure == "request":
        response.raise_for_status.side_effect = requests.RequestException(
            f"Error at {url}"
        )
    elif failure == "timeout":
        collector.session.get.side_effect = requests.Timeout()
    elif failure == "connection":
        collector.session.get.side_effect = requests.ConnectionError()
    else:
        collector.trip_circuit()
    try:
        collector._fetch_from_endpoint(endpoint)
    except requests.RequestException:
        pass
    assert "mock-key" not in caplog.text
    assert "apikey=REDACTED" in caplog.text
