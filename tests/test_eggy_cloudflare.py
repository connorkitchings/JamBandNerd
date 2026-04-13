"""Tests for EggyCollector's Cloudflare/403 fallback to Playwright."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from jambandnerd.data_collection.eggy.collector import EggyCollector


def _make_403_error(url: str) -> requests.exceptions.HTTPError:
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 403
    mock_resp.url = url
    err = requests.exceptions.HTTPError(f"403 Forbidden for url: {url}")
    err.response = mock_resp
    return err


def _make_500_error(url: str) -> requests.exceptions.HTTPError:
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 500
    err = requests.exceptions.HTTPError(f"500 Server Error for url: {url}")
    err.response = mock_resp
    return err


class TestEggyCollectorFetchFallback:
    """EggyCollector._fetch_from_endpoint falls back to Playwright on 403."""

    @patch.object(EggyCollector, "_fetch_via_playwright")
    @patch(
        "jambandnerd.data_collection.base.BandCollector._fetch_from_endpoint",
        side_effect=_make_403_error("https://thecarton.net/api/v2/songs.json"),
    )
    def test_falls_back_to_playwright_on_403(self, mock_super, mock_pw):
        mock_pw.return_value = [{"id": 1, "name": "Arrowhead"}]
        collector = EggyCollector()
        result = collector._fetch_from_endpoint("v2/songs.json")
        mock_pw.assert_called_once_with("https://thecarton.net/api/v2/songs.json")
        assert len(result) == 1
        assert result[0]["name"] == "Arrowhead"

    @patch.object(EggyCollector, "_fetch_via_playwright")
    @patch(
        "jambandnerd.data_collection.base.BandCollector._fetch_from_endpoint",
        side_effect=_make_500_error("https://thecarton.net/api/v2/songs.json"),
    )
    def test_reraises_non_403_http_error(self, mock_super, mock_pw):
        collector = EggyCollector()
        try:
            collector._fetch_from_endpoint("v2/songs.json")
        except requests.exceptions.HTTPError as exc:
            assert exc.response.status_code == 500
        else:
            raise AssertionError("Expected HTTPError to reraise")
        mock_pw.assert_not_called()

    @patch(
        "jambandnerd.data_collection.base.BandCollector._fetch_from_endpoint",
        return_value=[{"id": 2, "name": "White Rabbit"}],
    )
    def test_skips_playwright_on_success(self, mock_super):
        collector = EggyCollector()
        result = collector._fetch_from_endpoint("v2/songs.json")
        assert len(result) == 1
        assert result[0]["name"] == "White Rabbit"


class TestEggyCollectorPlaywrightFetch:
    """Tests for EggyCollector._fetch_via_playwright."""

    @patch("jambandnerd.data_collection.browser.CloudflareBypass.make_request")
    def test_parses_list_response(self, mock_request):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"id": 1}, {"id": 2}]
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        collector = EggyCollector()
        result = collector._fetch_via_playwright(
            "https://thecarton.net/api/v2/songs.json"
        )
        assert result == [{"id": 1}, {"id": 2}]

    @patch("jambandnerd.data_collection.browser.CloudflareBypass.make_request")
    def test_parses_wrapped_data_response(self, mock_request):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": 1}]}
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        collector = EggyCollector()
        result = collector._fetch_via_playwright(
            "https://thecarton.net/api/v2/songs.json"
        )
        assert result == [{"id": 1}]

    @patch("jambandnerd.data_collection.browser.CloudflareBypass.make_request")
    def test_returns_empty_on_playwright_failure(self, mock_request):
        mock_request.side_effect = RuntimeError("browser crashed")

        collector = EggyCollector()
        result = collector._fetch_via_playwright(
            "https://thecarton.net/api/v2/songs.json"
        )
        assert result == []

    @patch("jambandnerd.data_collection.browser.CloudflareBypass.make_request")
    def test_returns_empty_on_non_json(self, mock_request):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        collector = EggyCollector()
        result = collector._fetch_via_playwright(
            "https://thecarton.net/api/v2/songs.json"
        )
        assert result == []

    @patch("jambandnerd.data_collection.browser.CloudflareBypass.make_request")
    def test_returns_empty_on_unexpected_shape(self, mock_request):
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": "something unexpected"}
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        collector = EggyCollector()
        result = collector._fetch_via_playwright(
            "https://thecarton.net/api/v2/songs.json"
        )
        assert result == []
