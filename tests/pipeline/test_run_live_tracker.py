"""Exercise live polling through real collectors and normalizers, without I/O."""

import importlib
import re
import sys
import traceback
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from scripts import run_live_tracker as tracker
from src.jambandnerd.data_collection.config import COLLECTOR_CONFIGS

TARGET_DATE = "2026-11-16"


def show_payload(band, show_id=101, date=TARGET_DATE):
    if band == "goose":
        return {"show_id": show_id, "showdate": date, "artist": "Goose"}
    return {"showid": show_id, "showdate": date}


def setlist_payload(band, song="First Song", show_id=101, position=1):
    if band == "goose":
        return {
            "show_id": show_id,
            "setnumber": "1",
            "position": position,
            "songname": song,
            "artist": "Goose",
        }
    return {
        "uniqueid": str(position),
        "showid": show_id,
        "showdate": TARGET_DATE,
        "set": "1",
        "position": position,
        "song": song,
    }


@pytest.fixture
def polling(monkeypatch):
    monkeypatch.setenv("PHISH_API_KEY", "mock-key")
    upsert = Mock()
    predict = Mock(return_value=True)
    sleep = Mock()
    monkeypatch.setattr(tracker, "validate_and_upsert_dataframe", upsert)
    monkeypatch.setattr(tracker, "generate_live_predictions", predict)
    monkeypatch.setattr(tracker.time, "sleep", sleep)

    def prepare(band, *, shows=None, setlists=None):
        module = importlib.import_module(
            f"src.jambandnerd.data_collection.{band}.collector"
        )
        config = COLLECTOR_CONFIGS[band]
        monkeypatch.setattr(
            module,
            "get_collector_config",
            lambda _: replace(config, cache_enabled=False),
        )
        show_results = iter(shows if shows is not None else [[show_payload(band)]] * 20)
        setlist_results = iter(
            setlists if setlists is not None else [[setlist_payload(band)]] * 20
        )
        calls = []

        def get(session, url, **kwargs):
            assert kwargs["timeout"] == 30
            calls.append(url)
            is_setlist = "setlists" in url
            result = next(setlist_results if is_setlist else show_results)
            if isinstance(result, Exception):
                raise result
            if isinstance(result, Mock):
                return result
            response = Mock()
            response.json.return_value = {"data": result} if band == "phish" else result
            return response

        monkeypatch.setattr(requests.Session, "get", get)
        return upsert, predict, sleep, calls

    return prepare


@pytest.mark.parametrize("band", ["goose", "phish"])
def test_one_poll_upserts_actual_normalized_contract(polling, band):
    upsert, predict, sleep, calls = polling(
        band,
        setlists=[
            [setlist_payload(band), setlist_payload(band, show_id=999, position=2)]
        ],
    )
    tracker.run_live_tracker(band, TARGET_DATE, max_iterations=1)

    payload = upsert.call_args.kwargs
    assert payload["table_name"] == f"{band}_setlists_raw"
    assert payload["skip_validation"] is True
    frame = payload["df"]
    assert len(frame) == 1
    assert str(frame.iloc[0]["show_id"]) == "101"
    assert frame.iloc[0]["song_name"] == "First Song"
    if band == "phish":
        assert payload["conflict_columns"] == ["api_unique_id"]
        assert payload["required_columns"] == ["set_number", "position"]
        assert frame.iloc[0]["api_unique_id"] == "1"
        assert frame.iloc[0]["position"] == 1
        assert "song_position" not in frame.columns
        assert "setlists/showid/101.json?" in calls[-1]
    else:
        assert payload["conflict_columns"] == ["show_id", "set_number", "song_position"]
        assert payload["required_columns"] == ["set_number", "song_position"]
        assert frame.iloc[0]["song_position"] == 1
    assert frame.iloc[0]["set_number"] == 1
    assert frame.iloc[0]["source_hash"]
    predict.assert_called_once_with(band=band)
    sleep.assert_not_called()
    # A live tracker must not alter the timeout used by daily collectors.
    assert COLLECTOR_CONFIGS[band].timeout == (120 if band == "phish" else 30)


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("scenario", ["no-shows", "wrong-date", "empty", "other-show"])
def test_poll_without_target_setlist_does_not_write_or_predict(polling, band, scenario):
    shows = [[]] if scenario == "no-shows" else None
    if scenario == "wrong-date":
        shows = [[show_payload(band, date="2026-11-15")]]
    setlists = [[]] if scenario == "empty" else None
    if scenario == "other-show":
        setlists = [[setlist_payload(band, show_id=999)]]
    upsert, predict, _, calls = polling(band, shows=shows, setlists=setlists)

    tracker.run_live_tracker(band, TARGET_DATE, max_iterations=1)

    upsert.assert_not_called()
    predict.assert_not_called()
    assert len(calls) == (1 if scenario in {"no-shows", "wrong-date"} else 2)


@pytest.mark.parametrize("band", ["goose", "phish"])
def test_same_count_correction_refreshes_but_order_and_timestamps_do_not(polling, band):
    first = [setlist_payload(band), setlist_payload(band, "Second Song", position=2)]
    corrected = [setlist_payload(band, "Corrected Song"), first[1]]
    upsert, predict, _, _ = polling(
        band, setlists=[first, list(reversed(first)), corrected, corrected]
    )

    tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=4)

    assert upsert.call_count == predict.call_count == 2
    assert upsert.call_args.kwargs["df"].iloc[0]["song_name"] == "Corrected Song"


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize(
    "source", ["shows", "setlists", "upsert", "predictions", "prediction-skip"]
)
def test_three_consecutive_errors_raise_without_false_success(polling, band, source):
    errors = [requests.Timeout("upstream timeout")] * 3
    options = {source: errors} if source in {"shows", "setlists"} else {}
    upsert, predict, sleep, calls = polling(band, **options)
    if source == "upsert":
        upsert.side_effect = RuntimeError("database unavailable")
    if source == "predictions":
        predict.side_effect = RuntimeError("predictions unavailable")
    if source == "prediction-skip":
        predict.return_value = False

    with pytest.raises(RuntimeError, match="three consecutive polling errors"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=10)

    assert sleep.call_count == 2
    if source in {"shows", "setlists"}:
        upsert.assert_not_called()
        predict.assert_not_called()
        assert len(calls) == (3 if source == "shows" else 6)
    elif source == "upsert":
        assert upsert.call_count == 3
        predict.assert_not_called()
    else:
        assert upsert.call_count == predict.call_count == 3


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("recovery", ["setlist", "no-show", "empty"])
def test_successful_poll_resets_consecutive_error_count(polling, band, recovery):
    error = requests.Timeout("upstream timeout")
    shows = [[show_payload(band)]] * 5
    if recovery == "no-show":
        shows[2] = []
    results = [error, error, error, error]
    if recovery != "no-show":
        results.insert(2, [] if recovery == "empty" else [setlist_payload(band)])
    upsert, predict, _, _ = polling(band, shows=shows, setlists=results)

    tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=5)

    assert (
        upsert.call_count == predict.call_count == (1 if recovery == "setlist" else 0)
    )


def test_workflow_matches_supported_cli_and_preserves_flags(monkeypatch):
    workflow = (
        Path(__file__).resolve().parents[2] / ".github/workflows/live-tracker.yml"
    ).read_text()
    options = re.search(r"        options:\n((?:          - \w+\n)+)", workflow)[1]
    workflow_bands = re.findall(r"- (\w+)", options)
    assert set(workflow_bands) == {"goose", "phish"}
    assert "bsky" not in workflow
    run = Mock()
    monkeypatch.setattr(tracker, "run_live_tracker", run)
    for band in workflow_bands:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_live_tracker.py",
                "--band",
                band,
                "--date",
                TARGET_DATE,
                "--interval",
                "15",
                "--max-iterations",
                "2",
            ],
        )
        tracker.main()
        run.assert_called_with(
            band=band, target_date=TARGET_DATE, interval=15, max_iterations=2
        )
    flags = set(re.findall(r"--[a-z-]+", workflow)) - {"--locked", "--no-dev"}
    assert flags == {"--band", "--date", "--interval", "--max-iterations"}


@pytest.mark.parametrize("band", ["wsp", "billy", "um"])
def test_cli_rejects_unsupported_live_bands(monkeypatch, band):
    monkeypatch.setattr(sys, "argv", ["tracker", "--band", band, "--date", TARGET_DATE])
    with pytest.raises(SystemExit) as error:
        tracker.main()
    assert error.value.code == 2


def test_cli_propagates_terminal_polling_failure(monkeypatch, polling):
    polling("phish", setlists=[requests.Timeout("upstream timeout")] * 3)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tracker",
            "--band",
            "phish",
            "--date",
            TARGET_DATE,
            "--interval",
            "0",
            "--max-iterations",
            "3",
        ],
    )
    with pytest.raises(RuntimeError, match="three consecutive polling errors"):
        tracker.main()


@pytest.mark.parametrize("iterations", [1, 2])
def test_short_failed_run_is_not_successful(polling, iterations):
    polling("goose", shows=[requests.Timeout("upstream timeout")] * iterations)
    with pytest.raises(RuntimeError, match="without a successful poll"):
        tracker.run_live_tracker(
            "goose", TARGET_DATE, interval=0, max_iterations=iterations
        )


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("source", ["shows", "setlists"])
@pytest.mark.parametrize("failure", ["forbidden", "invalid-json"])
def test_suppressed_collector_failures_count_as_failed_polls(
    polling, band, source, failure
):
    if failure == "forbidden":
        response = Mock(status_code=403)
        result = requests.HTTPError("Forbidden", response=response)
    else:
        result = Mock()
        result.json.side_effect = ValueError("Invalid JSON")
    upsert, predict, _, _ = polling(band, **{source: [result] * 3})
    with pytest.raises(RuntimeError, match="three consecutive polling errors"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=10)
    upsert.assert_not_called()
    predict.assert_not_called()


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("source", ["shows", "setlists"])
@pytest.mark.parametrize(
    "payload",
    [
        {"message": "schema changed"},
        {"data": {"unexpected": "object"}},
        {"data": None},
        {"data": ["not a record"]},
    ],
)
def test_invalid_api_shapes_fail_without_writes_or_key_disclosure(
    polling, band, source, payload, caplog
):
    response = Mock()
    response.json.return_value = payload
    upsert, predict, _, _ = polling(band, **{source: [response] * 3})
    with pytest.raises(RuntimeError, match="three consecutive polling errors"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=10)
    upsert.assert_not_called()
    predict.assert_not_called()
    assert "mock-key" not in caplog.text
    assert "Failed to parse JSON response" in caplog.text


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("published", [True, False])
def test_nonempty_shrinking_snapshots_fail_without_acknowledging_removed_rows(
    polling, band, published, caplog
):
    caplog.set_level("INFO")
    first = [setlist_payload(band), setlist_payload(band, "Second Song", position=2)]
    smaller = first[:1]
    upsert, predict, _, _ = polling(band, setlists=[first, smaller, smaller, smaller])
    predict.return_value = published
    with pytest.raises(RuntimeError, match="three consecutive polling errors"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=4)
    upsert.assert_called_once()
    assert len(upsert.call_args.kwargs["df"]) == 2
    predict.assert_called_once_with(band=band)
    assert "snapshot removed previously observed rows" in caplog.text
    assert caplog.text.count("Predictions updated for the changed setlist") == int(
        published
    )


@pytest.mark.parametrize("failure", [requests.Timeout, requests.ConnectionError])
@pytest.mark.parametrize("source", ["shows", "setlists"])
def test_transport_failures_redact_key_in_downstream_logs_and_terminal_trace(
    polling, failure, source, caplog
):
    keyed_url = "https://api.phish.net/v5/setlists/showid/101.json?apikey=mock-key"
    error = failure(f"Request failed for {keyed_url}")
    error.__cause__ = RuntimeError(f"Underlying connection failed at {keyed_url}")
    upsert, predict, _, _ = polling("phish", **{source: [error] * 3})
    with pytest.raises(
        RuntimeError, match="three consecutive polling errors"
    ) as terminal:
        tracker.run_live_tracker("phish", TARGET_DATE, interval=0, max_iterations=3)
    upsert.assert_not_called()
    predict.assert_not_called()
    assert "mock-key" not in caplog.text
    assert "mock-key" not in "".join(traceback.format_exception(terminal.value))
    sanitized = terminal.value.__cause__
    assert isinstance(sanitized, failure)
    assert "apikey=REDACTED" in str(sanitized)
    assert sanitized.__cause__ is None
    assert sanitized.__suppress_context__ is True


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("missing", ["empty", "no-show"])
def test_failed_publication_followed_by_missing_data_cannot_finish_successfully(
    polling, band, missing
):
    options = (
        {"shows": [[show_payload(band)], []]}
        if missing == "no-show"
        else {"setlists": [[setlist_payload(band)], []]}
    )
    upsert, predict, _, _ = polling(band, **options)
    predict.return_value = False
    with pytest.raises(RuntimeError, match="pending live prediction publication"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=2)
    upsert.assert_called_once()
    predict.assert_called_once_with(band=band)


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("failed_polls", [1, 2])
def test_failed_publications_at_exhaustion_fail_after_earlier_success(
    polling, band, failed_polls
):
    first = [setlist_payload(band)]
    changed = [setlist_payload(band, "Corrected Song")]
    upsert, predict, _, _ = polling(band, setlists=[first] + [changed] * failed_polls)
    predict.side_effect = [True] + [False] * failed_polls
    with pytest.raises(RuntimeError, match="pending live prediction publication"):
        tracker.run_live_tracker(
            band, TARGET_DATE, interval=0, max_iterations=1 + failed_polls
        )
    assert upsert.call_count == predict.call_count == 1 + failed_polls


@pytest.mark.parametrize("band", ["goose", "phish"])
def test_later_publication_recovery_clears_pending_obligation(polling, band):
    first = [setlist_payload(band)]
    upsert, predict, _, _ = polling(band, setlists=[first, [], first, []])
    predict.side_effect = [False, True]
    tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=4)
    assert upsert.call_count == predict.call_count == 2


@pytest.mark.parametrize("band", ["goose", "phish"])
@pytest.mark.parametrize("missing", ["empty", "no-show"])
def test_missing_data_does_not_reset_pending_publication_errors(polling, band, missing):
    options = (
        {"shows": [[show_payload(band)], [], [], [show_payload(band)]]}
        if missing == "no-show"
        else {"setlists": [[setlist_payload(band)], [], [], [setlist_payload(band)]]}
    )
    upsert, predict, sleep, _ = polling(band, **options)
    predict.return_value = False
    with pytest.raises(RuntimeError, match="three consecutive polling errors"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=4)
    upsert.assert_called_once()
    predict.assert_called_once()
    assert sleep.call_count == 2


@pytest.mark.parametrize("band", ["goose", "phish"])
def test_uncertain_raw_write_retains_publication_obligation_through_empty_poll(
    polling, band
):
    upsert, predict, _, _ = polling(band, setlists=[[setlist_payload(band)], []])
    upsert.side_effect = RuntimeError("Database commit status unknown")
    with pytest.raises(RuntimeError, match="pending live prediction publication"):
        tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=2)
    upsert.assert_called_once()
    predict.assert_not_called()


@pytest.mark.parametrize("band", ["goose", "phish"])
def test_pending_publication_retries_even_if_payload_returns_to_last_acknowledged_snapshot(
    polling, band
):
    first = [setlist_payload(band)]
    changed = [setlist_payload(band, "Corrected Song")]
    upsert, predict, _, _ = polling(band, setlists=[first, changed, first])
    predict.side_effect = [True, False, True]
    tracker.run_live_tracker(band, TARGET_DATE, interval=0, max_iterations=3)
    assert upsert.call_count == predict.call_count == 3
    assert upsert.call_args.kwargs["df"].iloc[0]["song_name"] == "First Song"
