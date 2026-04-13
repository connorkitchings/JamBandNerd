from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from scripts.check_supported_model_freshness import audit_supported_model_freshness


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, rows):
        self._rows = list(rows)
        self._filters: list[tuple[str, object]] = []
        self._orders: list[tuple[str, bool]] = []
        self._limit: int | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: object):
        self._filters.append((column, value))
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


def _model_definition(
    *,
    slug: str,
    version: str,
    prediction_table: str,
    aggregate_accuracy_table: str,
    enabled_for_pipeline: bool = True,
    enabled_for_web: bool = True,
):
    return SimpleNamespace(
        slug=slug,
        version=version,
        prediction_table=prediction_table,
        aggregate_accuracy_table=aggregate_accuracy_table,
        enabled_for_pipeline=enabled_for_pipeline,
        enabled_for_web=enabled_for_web,
    )


def _install_registry(monkeypatch):
    models = [
        _model_definition(
            slug="notebook",
            version="notebook_v1",
            prediction_table="predictions_notebook",
            aggregate_accuracy_table="notebook_accuracy",
        ),
        _model_definition(
            slug="deal",
            version="deal_v2",
            prediction_table="predictions_deal",
            aggregate_accuracy_table="accuracy_deal",
        ),
    ]
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.list_models", lambda: models
    )
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.list_accuracy_validation_models",
        lambda: models,
    )


def _iso(hours_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _freshness_rows(
    *,
    notebook_prediction_hours: int | None = 2,
    deal_prediction_hours: int | None = 3,
    notebook_per_show_hours: int | None = 4,
    notebook_aggregate_hours: int | None = 5,
    deal_per_show_hours: int | None = 6,
    deal_aggregate_hours: int | None = 7,
):
    rows: dict[str, list[dict[str, object]]] = {
        "predictions_notebook": [],
        "predictions_deal": [],
        "accuracy_per_show": [],
        "notebook_accuracy": [],
        "accuracy_deal": [],
    }

    if notebook_prediction_hours is not None:
        rows["predictions_notebook"].append(
            {
                "band": "wsp",
                "model_version": "notebook_v1",
                "predicted_at": _iso(notebook_prediction_hours),
            }
        )
    if deal_prediction_hours is not None:
        rows["predictions_deal"].append(
            {
                "band": "wsp",
                "model_version": "deal_v2",
                "predicted_at": _iso(deal_prediction_hours),
            }
        )
    if notebook_per_show_hours is not None:
        rows["accuracy_per_show"].append(
            {
                "band": "wsp",
                "model_version": "notebook_v1",
                "evaluated_at": _iso(notebook_per_show_hours),
            }
        )
    if deal_per_show_hours is not None:
        rows["accuracy_per_show"].append(
            {
                "band": "wsp",
                "model_version": "deal_v2",
                "evaluated_at": _iso(deal_per_show_hours),
            }
        )
    if notebook_aggregate_hours is not None:
        rows["notebook_accuracy"].append(
            {
                "band": "wsp",
                "model_version": "notebook_v1",
                "evaluated_at": _iso(notebook_aggregate_hours),
            }
        )
    if deal_aggregate_hours is not None:
        rows["accuracy_deal"].append(
            {
                "band": "wsp",
                "model_version": "deal_v2",
                "evaluated_at": _iso(deal_aggregate_hours),
            }
        )

    return rows


def test_audit_supported_model_freshness_passes_for_fresh_supported_models(
    monkeypatch,
):
    _install_registry(monkeypatch)
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_supabase_client",
        lambda: _ClientStub(_freshness_rows()),
    )

    result = audit_supported_model_freshness(band="wsp", max_age_hours=48)

    assert result.freshness_state == "fresh"
    assert result.stale_prediction_models == ()
    assert result.stale_accuracy_models == ()
    assert result.max_prediction_age_hours is not None
    assert result.max_accuracy_age_hours is not None


def test_audit_supported_model_freshness_flags_stale_predictions_only(monkeypatch):
    _install_registry(monkeypatch)
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_supabase_client",
        lambda: _ClientStub(
            _freshness_rows(notebook_prediction_hours=60, deal_prediction_hours=4)
        ),
    )

    result = audit_supported_model_freshness(band="wsp", max_age_hours=48)

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == ("notebook",)
    assert result.stale_accuracy_models == ()
    assert result.max_prediction_age_hours is not None
    assert result.max_prediction_age_hours > 48


def test_audit_supported_model_freshness_flags_stale_accuracy_only(monkeypatch):
    _install_registry(monkeypatch)
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_supabase_client",
        lambda: _ClientStub(
            _freshness_rows(
                notebook_per_show_hours=60,
                notebook_aggregate_hours=62,
            )
        ),
    )

    result = audit_supported_model_freshness(band="wsp", max_age_hours=48)

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == ()
    assert result.stale_accuracy_models == ("notebook",)
    assert result.max_accuracy_age_hours is not None
    assert result.max_accuracy_age_hours > 48


def test_audit_supported_model_freshness_counts_missing_supported_rows_as_stale(
    monkeypatch,
):
    _install_registry(monkeypatch)
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_supabase_client",
        lambda: _ClientStub(
            _freshness_rows(
                notebook_prediction_hours=None,
                notebook_per_show_hours=None,
                notebook_aggregate_hours=None,
            )
        ),
    )

    result = audit_supported_model_freshness(band="wsp", max_age_hours=48)

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == ("notebook",)
    assert result.stale_accuracy_models == ("notebook",)
    assert "notebook predictions missing" in result.freshness_reason
    assert "notebook per-show accuracy missing" in result.freshness_reason


def test_audit_supported_model_freshness_handles_mixed_model_states(monkeypatch):
    _install_registry(monkeypatch)
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_supabase_client",
        lambda: _ClientStub(
            _freshness_rows(
                notebook_prediction_hours=3,
                deal_prediction_hours=72,
                notebook_per_show_hours=4,
                notebook_aggregate_hours=5,
                deal_per_show_hours=6,
                deal_aggregate_hours=7,
            )
        ),
    )

    result = audit_supported_model_freshness(band="wsp", max_age_hours=48)

    assert result.freshness_state == "stale"
    assert result.stale_prediction_models == ("deal",)
    assert result.stale_accuracy_models == ()


def test_audit_supported_model_freshness_treats_skip_accuracy_as_warning(
    monkeypatch,
):
    _install_registry(monkeypatch)
    monkeypatch.setattr(
        "scripts.check_supported_model_freshness.get_supabase_client",
        lambda: _ClientStub(
            _freshness_rows(
                notebook_per_show_hours=55,
                notebook_aggregate_hours=57,
            )
        ),
    )

    result = audit_supported_model_freshness(
        band="wsp",
        max_age_hours=48,
        skip_accuracy=True,
    )

    assert result.freshness_state == "warning"
    assert result.stale_prediction_models == ()
    assert result.stale_accuracy_models == ("notebook",)
    assert "skip_accuracy=true" in result.freshness_reason
