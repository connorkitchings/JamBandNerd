"""Tests for the shared CloudflareBypass Playwright module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from jambandnerd.data_collection.browser import CloudflareBypass


class TestCloudflareBypassMakeRequest:
    """Test CloudflareBypass.make_request with mocked Playwright."""

    @patch("jambandnerd.data_collection.browser._get_browser")
    @patch("jambandnerd.data_collection.browser._enforce_rate_limit")
    def test_returns_response_on_200(self, mock_rate_limit, mock_get_browser):
        mock_pw_resp = MagicMock()
        mock_pw_resp.status = 200
        mock_pw_resp.headers = {"content-type": "application/json"}
        mock_pw_resp.status_text = "OK"

        mock_page = MagicMock()
        mock_page.goto.return_value = mock_pw_resp
        mock_page.content.return_value = '[{"id": 1, "name": "song"}]'

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        with patch("jambandnerd.data_collection.browser._context", mock_context):
            resp = CloudflareBypass.make_request("https://example.com/api/songs.json")

        assert resp.status_code == 200
        assert resp.encoding == "utf-8"
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "song"
        mock_page.close.assert_called_once()

    @patch("jambandnerd.data_collection.browser._get_browser")
    @patch("jambandnerd.data_collection.browser._enforce_rate_limit")
    def test_returns_error_response_on_403(self, mock_rate_limit, mock_get_browser):
        mock_pw_resp = MagicMock()
        mock_pw_resp.status = 403
        mock_pw_resp.headers = {"content-type": "text/html"}
        mock_pw_resp.status_text = "Forbidden"

        mock_page = MagicMock()
        mock_page.goto.return_value = mock_pw_resp
        mock_page.content.return_value = "<html>Forbidden</html>"

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        with patch("jambandnerd.data_collection.browser._context", mock_context):
            resp = CloudflareBypass.make_request("https://example.com/api")

        assert resp.status_code == 403
        mock_page.close.assert_called_once()

    @patch("jambandnerd.data_collection.browser._get_browser")
    @patch("jambandnerd.data_collection.browser._enforce_rate_limit")
    def test_raises_on_null_response(self, mock_rate_limit, mock_get_browser):
        mock_page = MagicMock()
        mock_page.goto.return_value = None

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        with patch("jambandnerd.data_collection.browser._context", mock_context):
            with pytest.raises(
                requests.exceptions.RequestException, match="no response"
            ):
                CloudflareBypass.make_request("https://example.com/api")

        mock_page.close.assert_called_once()

    @patch("jambandnerd.data_collection.browser._get_browser")
    @patch("jambandnerd.data_collection.browser._enforce_rate_limit")
    def test_page_closed_on_exception(self, mock_rate_limit, mock_get_browser):
        mock_page = MagicMock()
        mock_page.goto.side_effect = RuntimeError("browser crash")

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        with patch("jambandnerd.data_collection.browser._context", mock_context):
            with pytest.raises(RuntimeError, match="browser crash"):
                CloudflareBypass.make_request("https://example.com/api")

        mock_page.close.assert_called_once()


class TestCloudflareBypassCleanup:
    def test_closes_context_and_browser(self):
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()

        with patch("jambandnerd.data_collection.browser._pw", mock_pw):
            with patch("jambandnerd.data_collection.browser._browser", mock_browser):
                with patch("jambandnerd.data_collection.browser._context", mock_context):
                    CloudflareBypass.cleanup()

        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    def test_noop_when_none(self):
        with patch("jambandnerd.data_collection.browser._pw", None):
            with patch("jambandnerd.data_collection.browser._browser", None):
                with patch("jambandnerd.data_collection.browser._context", None):
                    CloudflareBypass.cleanup()
