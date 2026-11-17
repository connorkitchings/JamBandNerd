"""Exercise cache acknowledgement and credential boundaries without network I/O."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from scripts import revalidate_website_cache as module

SITE_URL = "https://example.com"
SECRET = "test-secret-that-must-not-appear"


@pytest.fixture
def transport(monkeypatch):
    post = Mock()
    sleep = Mock()
    monkeypatch.setattr(module.requests, "post", post)
    monkeypatch.setattr(module.time, "sleep", sleep)
    return post, sleep


def _response(status=200, payload=None):
    response = Mock(status_code=status)
    response.json.return_value = (
        payload if payload is not None else {"revalidated": True, "band": "goose"}
    )
    return response


def _run():
    module.revalidate_website_cache(band="goose", site_url=SITE_URL, secret=SECRET)


def test_cache_confirmation_uses_exact_endpoint_and_never_follows_redirects(transport):
    post, sleep = transport
    post.return_value = _response()

    module.revalidate_website_cache(
        band="goose", site_url=SITE_URL + "/", secret=SECRET
    )

    post.assert_called_once_with(
        SITE_URL + "/api/revalidate",
        headers={"Authorization": "Bearer " + SECRET},
        json={"band": "goose"},
        allow_redirects=False,
        timeout=30,
    )
    sleep.assert_not_called()


@pytest.mark.parametrize("status", [201, 204, 301, 302, 307, 308, 400, 401, 403, 404])
def test_non_200_permanent_responses_fail_without_retry_or_redirect(transport, status):
    post, sleep = transport
    post.return_value = _response(status)
    post.return_value.headers = {"Location": "https://another-host.example/"}

    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        _run()

    assert post.call_count == 1
    assert post.call_args.kwargs["allow_redirects"] is False
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"revalidated": False, "band": "goose"},
        {"revalidated": 1, "band": "goose"},
        {"revalidated": True, "band": "phish"},
        {"revalidated": True},
        ["goose"],
        "not an acknowledgement",
    ],
)
def test_200_requires_exact_success_and_requested_band(transport, payload):
    post, sleep = transport
    post.return_value = _response(payload=payload)

    with pytest.raises(RuntimeError, match="acknowledgement did not match"):
        _run()

    assert post.call_count == 1
    sleep.assert_not_called()


def test_non_json_200_fails_without_retry(transport):
    post, sleep = transport
    post.return_value = _response()
    post.return_value.json.side_effect = ValueError(SECRET)

    with pytest.raises(RuntimeError, match="invalid JSON") as error:
        _run()

    assert SECRET not in str(error.value)
    assert post.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [requests.Timeout(SECRET), requests.ConnectionError(SECRET), 429, 500, 503, 599],
)
def test_transient_failures_retry_then_confirm(transport, failure):
    post, sleep = transport
    post.side_effect = [
        failure if isinstance(failure, Exception) else _response(failure),
        _response(),
    ]

    _run()

    assert post.call_count == 2
    sleep.assert_called_once_with(5)


@pytest.mark.parametrize("failure", [requests.Timeout(SECRET), 429, 503])
def test_transient_failure_retries_are_bounded(transport, failure):
    post, sleep = transport
    post.side_effect = [
        failure if isinstance(failure, Exception) else _response(failure)
    ] * 4

    with pytest.raises(RuntimeError):
        _run()

    assert post.call_count == 4
    assert sleep.call_count == 3
    assert all(call.args == (5,) for call in sleep.call_args_list)


@pytest.mark.parametrize(
    "site_url",
    [
        "http://example.com",
        "https://example.com/path",
        "https://example.com?",
        "https://example.com?secret=value",
        "https://example.com#fragment",
        "https://user:password@example.com",
        "https://example.com\\evil",
        "https://example.com\n",
        "https://",
        "https://example.com:bad",
        "https://example.com:0",
        "https://example.com:65536",
        "https://[broken",
        "https://ex%61mple.com",
    ],
)
def test_invalid_origin_never_receives_credentials(transport, site_url):
    post, sleep = transport

    with pytest.raises(RuntimeError, match="HTTPS origin"):
        module.revalidate_website_cache(band="goose", site_url=site_url, secret=SECRET)

    post.assert_not_called()
    sleep.assert_not_called()


@pytest.mark.parametrize("missing", ["BAND", "SITE_URL", "REVALIDATE_SECRET"])
def test_cli_missing_configuration_fails_without_network(
    monkeypatch, transport, missing
):
    for key, value in {
        "BAND": "goose",
        "SITE_URL": SITE_URL,
        "REVALIDATE_SECRET": SECRET,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing)

    assert module.main() == 1
    transport[0].assert_not_called()


@pytest.mark.parametrize(
    "failure", [requests.Timeout(SECRET), 307, 401, "non-json", "wrong-band", "success"]
)
def test_cli_sanitizes_errors_and_acknowledges_only_success(
    monkeypatch, transport, capsys, failure
):
    for key, value in {
        "BAND": "goose",
        "SITE_URL": SITE_URL,
        "REVALIDATE_SECRET": SECRET,
    }.items():
        monkeypatch.setenv(key, value)
    post, _ = transport
    if isinstance(failure, Exception):
        post.side_effect = failure
    elif isinstance(failure, int):
        post.return_value = _response(failure)
        post.return_value.text = SECRET
    elif failure == "non-json":
        post.return_value = _response()
        post.return_value.json.side_effect = ValueError(SECRET)
    elif failure == "wrong-band":
        post.return_value = _response(payload={"revalidated": True, "band": SECRET})
    else:
        post.return_value = _response()

    assert module.main() == (0 if failure == "success" else 1)
    logs = capsys.readouterr()
    assert SECRET not in logs.out + logs.err
    assert ("confirmed" in logs.out) == (failure == "success")


def test_both_workflows_use_shared_helper_and_keep_secrets_step_scoped():
    root = Path(__file__).resolve().parents[1]
    for name in ("daily-pipeline.yml", "weekly-correction-sweep.yml"):
        workflow = (root / ".github/workflows" / name).read_text()
        cache_step = workflow.split("      - name: Revalidate Website Cache\n", 1)[
            1
        ].split("\n      - name:", 1)[0]
        assert "run: uv run python scripts/revalidate_website_cache.py" in cache_step
        assert "BAND: ${{ matrix.band }}" in cache_step
        assert "SITE_URL: ${{ vars.SITE_URL }}" in cache_step
        assert "REVALIDATE_SECRET: ${{ secrets.REVALIDATE_SECRET }}" in cache_step
        assert workflow.count("${{ vars.SITE_URL }}") == 1
        assert workflow.count("${{ secrets.REVALIDATE_SECRET }}") == 1
        assert "curl --fail-with-body" not in cache_step
