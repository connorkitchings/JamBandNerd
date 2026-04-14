import json
from datetime import date

from scripts.generate_pipeline_summary import (
    build_data_quality_lines,
    build_prediction_coverage_lines,
    build_supported_model_freshness_lines,
    render_summary,
)


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, table_name, rows, client):
        self._table_name = table_name
        self._rows = list(rows)
        self._client = client
        self._filters = []
        self._orders = []
        self._range = None
        self._limit = None
        self._selected_columns = "*"

    def select(self, columns="*", **_kwargs):
        self._selected_columns = columns
        return self

    def eq(self, column, value):
        self._filters.append(("eq", column, value))
        return self

    def gte(self, column, value):
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column, value):
        self._filters.append(("lte", column, value))
        return self

    def in_(self, column, values):
        self._filters.append(("in", column, list(values)))
        return self

    def order(self, column, desc=False):
        self._orders.append((column, desc))
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        self._client.query_counts[self._table_name] = (
            self._client.query_counts.get(self._table_name, 0) + 1
        )
        rows = list(self._rows)
        for operator, column, value in self._filters:
            if operator == "eq":
                rows = [row for row in rows if row.get(column) == value]
            elif operator == "gte":
                rows = [row for row in rows if row.get(column) >= value]
            elif operator == "lte":
                rows = [row for row in rows if row.get(column) <= value]
            elif operator == "in":
                values = set(value)
                rows = [row for row in rows if row.get(column) in values]

        for column, desc in reversed(self._orders):
            rows.sort(
                key=lambda row: (row.get(column) is None, row.get(column)),
                reverse=desc,
            )

        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._selected_columns != "*":
            selected_columns = [
                column.strip() for column in self._selected_columns.split(",")
            ]
            rows = [
                {column: row.get(column) for column in selected_columns} for row in rows
            ]
        return _ResponseStub(rows)


class _FailingQueryStub:
    def __init__(self, table_name, message):
        self._table_name = table_name
        self._message = message

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        raise RuntimeError(self._message)


class _ClientStub:
    def __init__(self, table_rows, *, failing_tables=None):
        self._table_rows = table_rows
        self._failing_tables = failing_tables or {}
        self.query_counts = {}

    def table(self, name):
        if name in self._failing_tables:
            return _FailingQueryStub(name, self._failing_tables[name])
        return _QueryStub(name, self._table_rows.get(name, []), self)


def test_build_data_quality_lines_uses_completed_show_window():
    client = _ClientStub(
        {
            "goose_shows_raw": [
                {"show_id": "past", "show_date": "2026-03-16"},
                {"show_id": "today", "show_date": "2026-03-17"},
            ],
            "goose_setlists_raw": [{"show_id": "past"}],
        }
    )

    lines = build_data_quality_lines(
        client,
        bands=["goose"],
        days=7,
        today=date(2026, 3, 17),
    )

    assert "- ✅ All recent completed shows have setlist data" in lines
    assert "- Window: 2026-03-10 through 2026-03-16" in lines
    assert "- Total completed shows: 1" in lines


def test_build_data_quality_lines_batches_setlist_lookups():
    shows_rows = [
        {"show_id": f"show-{index}", "show_date": "2026-03-16"} for index in range(120)
    ]
    setlists_rows = [{"show_id": f"show-{index}"} for index in range(120)]
    client = _ClientStub(
        {
            "um_shows_raw": shows_rows,
            "um_setlists_raw": setlists_rows,
        }
    )

    lines = build_data_quality_lines(
        client,
        bands=["um"],
        days=7,
        today=date(2026, 3, 17),
    )

    assert "- ✅ All recent completed shows have setlist data" in lines
    assert client.query_counts["um_setlists_raw"] == 3


def test_build_prediction_coverage_lines_uses_latest_completed_show_with_setlist():
    client = _ClientStub(
        {
            "goose_shows_raw": [
                {"show_id": "today", "show_date": "2026-03-17"},
                {"show_id": "missing", "show_date": "2026-03-16"},
                {"show_id": "played", "show_date": "2026-03-15"},
            ],
            "goose_setlists_raw": [
                {"show_id": "played", "song_name": "Song A"},
                {"show_id": "played", "song_name": "Song B"},
                {"show_id": "today", "song_name": "Ignore Me"},
            ],
            "predictions": [
                {
                    "band": "goose",
                    "model_slug": "notebook",
                    "reference_date": "2026-03-15",
                    "predicted_at": "2026-03-15T12:00:00+00:00",
                    "predictions": json.dumps(
                        [
                            {"song_name": "Song A"},
                            {"song_name": "Other Song"},
                        ]
                    ),
                }
            ],
        }
    )

    lines = build_prediction_coverage_lines(
        client,
        bands=["goose"],
        today=date(2026, 3, 17),
    )

    assert "| GOOSE | 1/2 | 2 | 2026-03-15 |" in lines


def test_render_summary_reports_per_band_errors_without_crashing():
    client = _ClientStub(
        {
            "goose_shows_raw": [{"show_id": "played", "show_date": "2026-03-16"}],
            "goose_setlists_raw": [{"show_id": "played", "song_name": "Song A"}],
            "predictions": [
                {
                    "band": "goose",
                    "model_slug": "notebook",
                    "reference_date": "2026-03-16",
                    "predicted_at": "2026-03-16T12:00:00+00:00",
                    "predictions": json.dumps([{"song_name": "Song A"}]),
                }
            ],
        },
        failing_tables={"phish_shows_raw": "boom"},
    )

    summary = render_summary(
        client,
        bands=["goose", "phish"],
        days=7,
        today=date(2026, 3, 17),
    )

    assert "### Data Quality Check" in summary
    assert "### Prediction Coverage" in summary
    assert "**GOOSE**:" in summary
    assert "**PHISH**:" in summary
    assert "- ❌ Error checking data: boom" in summary
    assert "| GOOSE | 1/1 | 1 | 2026-03-16 |" in summary
    assert "| PHISH | Error | n/a | boom |" in summary


def test_render_summary_includes_band_health_states():
    client = _ClientStub(
        {
            "goose_shows_raw": [{"show_id": "played", "show_date": "2026-03-16"}],
            "goose_setlists_raw": [{"show_id": "played", "song_name": "Song A"}],
            "predictions": [
                {
                    "band": "goose",
                    "model_slug": "notebook",
                    "reference_date": "2026-03-16",
                    "predicted_at": "2026-03-16T12:00:00+00:00",
                    "predictions": json.dumps([{"song_name": "Song A"}]),
                }
            ],
            "wsp_shows_raw": [],
            "wsp_setlists_raw": [],
        }
    )

    summary = render_summary(
        client,
        bands=["goose", "wsp"],
        band_statuses=[
            {
                "band": "goose",
                "workflow_state": "success",
                "outcome_code": "success",
                "execution_mode": "full_refresh",
                "missing_count": 0,
                "prediction_action": "generated",
            },
            {
                "band": "wsp",
                "workflow_state": "degraded",
                "outcome_code": "degraded_upstream_blocked",
                "execution_mode": "bounded_refresh",
                "missing_count": 0,
                "prediction_action": "reused_existing",
                "fallback_shows_filled": 2,
            },
        ],
        days=7,
        today=date(2026, 3, 17),
    )

    assert "### Band Run Health" in summary
    assert (
        "| GOOSE | success | success | full_refresh | 0 | generated | n/a |" in summary
    )
    assert (
        "| WSP | degraded | degraded_upstream_blocked | bounded_refresh | 0 | reused_existing | "
        "fallback shows filled=2 |" in summary
    )


def test_build_supported_model_freshness_lines_surfaces_stale_and_reused_states():
    lines = build_supported_model_freshness_lines(
        [
            {
                "band": "goose",
                "workflow_state": "success",
                "prediction_action": "generated",
                "freshness_state": "fresh",
                "stale_prediction_models": [],
                "stale_accuracy_models": [],
                "max_prediction_age_hours": 4.2,
                "max_accuracy_age_hours": 7.4,
                "freshness_reason": "all supported model predictions and accuracy are within 48h",
            },
            {
                "band": "wsp",
                "workflow_state": "degraded",
                "prediction_action": "reused_existing",
                "freshness_state": "stale",
                "stale_prediction_models": ["notebook"],
                "stale_accuracy_models": ["notebook"],
                "max_prediction_age_hours": 61.3,
                "max_accuracy_age_hours": 88.0,
                "freshness_reason": "notebook predictions stale age=61.3h; notebook per-show accuracy stale age=88.0h",
            },
        ]
    )

    assert "### Supported Model Freshness" in lines
    assert (
        "| GOOSE | fresh | none | 4.2h | 7.4h | no | "
        "all supported model predictions and accuracy are within 48h |" in lines
    )
    assert (
        "| WSP | stale | prediction: notebook; accuracy: notebook | 61.3h | 88.0h | yes | "
        "notebook predictions stale age=61.3h; notebook per-show accuracy stale age=88.0h |"
        in lines
    )


def test_render_summary_includes_supported_model_freshness_section():
    client = _ClientStub(
        {
            "wsp_shows_raw": [],
            "wsp_setlists_raw": [],
            "goose_shows_raw": [],
            "goose_setlists_raw": [],
        }
    )

    summary = render_summary(
        client,
        bands=["goose", "wsp"],
        band_statuses=[
            {
                "band": "goose",
                "workflow_state": "degraded",
                "prediction_action": "reused_existing",
                "freshness_state": "fresh",
                "stale_prediction_models": [],
                "stale_accuracy_models": [],
                "max_prediction_age_hours": 6.0,
                "max_accuracy_age_hours": 10.0,
                "freshness_reason": "all supported model predictions and accuracy are within 48h",
            },
            {
                "band": "wsp",
                "workflow_state": "degraded",
                "prediction_action": "reused_existing",
                "freshness_state": "stale",
                "stale_prediction_models": ["notebook"],
                "stale_accuracy_models": [],
                "max_prediction_age_hours": 54.0,
                "max_accuracy_age_hours": 12.0,
                "freshness_reason": "notebook predictions stale age=54.0h",
            },
        ],
        today=date(2026, 3, 17),
    )

    assert "### Supported Model Freshness" in summary
    assert "| GOOSE | fresh | none | 6.0h | 10.0h | yes |" in summary
    assert "| WSP | stale | prediction: notebook | 54.0h | 12.0h | yes |" in summary
