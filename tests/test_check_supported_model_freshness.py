from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from scripts.check_supported_model_freshness import audit_supported_model_freshness

MODEL_VERSION = "wsp_baseline_v1"


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, rows):
        self._rows = list(rows)
        self._filters: list[tuple[str, object]] = []
        self._gte_filters: list[tuple[str, object]] = []
        self._orders: list[tuple[str, bool]] = []
        self._limit: int | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: object):
        self._filters.append((column, value))
        return self

    def gte(self, column: str, value: object):
        self._gte_filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False):
        self._orders.append((column, desc))
        return self

    def limit(self, value: int):
        self._limit = value
        return self

    def execute(self):
        rows = list(self._rows)
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        for column, value in self._gte_filters:
            rows = [row for row in rows if str(row.get(column) or "") >= str(value)]
        for column, desc in reversed(self._orders):
            rows.sort(
                key=lambda row: (row.get(column) is None, row.get(column)),
                reverse=desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _ResponseStub(rows)


class _ClientStub:
    def __init__(self, table_rows):
        self._table_rows = table_rows

    def table(self, name: str):
        return _QueryStub(self._table_rows.get(name, []))


def _iso(hours_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _freshness_rows(
    *,
    prediction_hours: int | None = 2,
    accuracy_hours: int | None = 4,
):
    rows: dict[str, list[dict[str, object]]] = {
        "setlist_predictions": [],
        "setlist_accuracy": [],
        "wsp_shows_raw": [
            {
                "show_date": date.today().isoformat(),
            }
        ],
    }

    if prediction_hours is not None:
        rows["setlist_predictions"].append(
            {
                "band": "wsp",
                "model_version": MODEL_VERSION,
                "generated_at": _iso(prediction_hours),
            }
        )
    if accuracy_hours is not None:
        rows["setlist_accuracy"].append(
            {
                "band": "wsp",
                "model_version": MODEL_VERSION,
                "evaluated_at": _iso(accuracy_hours),
            }
        )

    return rows


def _install_registry(monkeypatch):
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_band_metadata",
        lambda band: SimpleNamespace(model_version=f"{band}_baseline_v1"),
    )


def test_audit_supported_model_freshness_passes_for_fresh_active_model(
    monkeypatch,
):
    _install_registry(monkeypatch)
    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        client=_ClientStub(_freshness_rows()),
    )

    assert result.freshness_state == "fresh"
    assert result.stale_prediction_models == ()
    assert result.stale_accuracy_models == ()
    assert result.max_prediction_age_hours is not None
    assert result.max_accuracy_age_hours is not None


def test_audit_supported_model_freshness_flags_stale_predictions_only(monkeypatch):
    _install_registry(monkeypatch)
    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        client=_ClientStub(_freshness_rows(prediction_hours=60)),
    )

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == (MODEL_VERSION,)
    assert result.stale_accuracy_models == ()
    assert result.max_prediction_age_hours is not None
    assert result.max_prediction_age_hours > 48


def test_audit_supported_model_freshness_flags_stale_accuracy_only(monkeypatch):
    _install_registry(monkeypatch)
    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        client=_ClientStub(_freshness_rows(accuracy_hours=60)),
    )

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == ()
    assert result.stale_accuracy_models == (MODEL_VERSION,)
    assert result.max_accuracy_age_hours is not None
    assert result.max_accuracy_age_hours > 48


def test_audit_supported_model_freshness_counts_missing_rows_as_stale(
    monkeypatch,
):
    _install_registry(monkeypatch)
    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        client=_ClientStub(_freshness_rows(prediction_hours=None, accuracy_hours=None)),
    )

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == (MODEL_VERSION,)
    assert result.stale_accuracy_models == (MODEL_VERSION,)
    assert f"{MODEL_VERSION} predictions missing" in result.freshness_reason
    assert f"{MODEL_VERSION} per-show accuracy missing" in result.freshness_reason


def test_audit_supported_model_freshness_treats_skip_accuracy_as_warning(
    monkeypatch,
):
    _install_registry(monkeypatch)
    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        skip_accuracy=True,
        client=_ClientStub(_freshness_rows(accuracy_hours=55)),
    )

    assert result.freshness_state == "warning"
    assert result.stale_prediction_models == ()
    assert result.stale_accuracy_models == (MODEL_VERSION,)
    assert "skip_accuracy=true" in result.freshness_reason


def test_audit_supported_model_freshness_keeps_stale_predictions_failing_when_accuracy_is_skipped(
    monkeypatch,
):
    _install_registry(monkeypatch)
    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        skip_accuracy=True,
        client=_ClientStub(_freshness_rows(prediction_hours=60, accuracy_hours=60)),
    )

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == (MODEL_VERSION,)
    assert result.stale_accuracy_models == (MODEL_VERSION,)


def test_audit_supported_model_freshness_skips_live_check_without_upcoming_show(
    monkeypatch,
):
    _install_registry(monkeypatch)
    rows = _freshness_rows(prediction_hours=None)
    rows["wsp_shows_raw"] = []

    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        client=_ClientStub(rows),
    )

    assert result.freshness_state == "fresh"
    assert result.stale_prediction_models == ()
