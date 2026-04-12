from __future__ import annotations

from src.jambandnerd.models import readiness as module


class _ResponseStub:
    def __init__(self, data, count):
        self.data = data
        self.count = count


class _QueryStub:
    def __init__(self, rows):
        self._rows = list(rows)
        self._filters = []
        self._limit = None
        self._orders: list[tuple[str, bool]] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, column, desc=False, **_kwargs):
        self._orders.append((column, desc))
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        rows = list(self._rows)
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        for column, desc in reversed(self._orders):
            rows = sorted(rows, key=lambda row: row.get(column) or "", reverse=desc)
        count = len(rows)
        if self._limit is not None:
            rows = rows[: self._limit]
        return _ResponseStub(rows, count)


class _ClientStub:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _QueryStub(self._tables.get(name, []))


def _history_rows(
    model_slug: str, model_version: str, *, count: int
) -> list[dict[str, str]]:
    return [
        {
            "band": "goose",
            "model_slug": model_slug,
            "model_version": model_version,
            "target_show_date": f"2026-01-{index + 1:02d}",
            "generated_at": f"2026-02-{index + 1:02d}T00:00:00+00:00",
        }
        for index in range(count)
    ]


def test_build_model_readiness_report_marks_band_ready():
    client = _ClientStub(
        {
            "predictions_deal": [
                {
                    "band": "goose",
                    "model_version": "deal_v2",
                    "reference_date": "2026-04-10",
                }
            ],
            "prediction_songs": [
                {
                    "band": "goose",
                    "model_slug": "deal",
                    "model_version": "deal_v2",
                    "reference_date": "2026-04-10",
                }
            ],
            "historical_prediction_runs": _history_rows("deal", "deal_v2", count=50)
            + _history_rows("notebook", "notebook_v1", count=50),
            "accuracy_per_show": [
                {
                    "band": "goose",
                    "model_version": "deal_v2",
                    "show_id": f"show-{index}",
                }
                for index in range(50)
            ],
            "accuracy_deal": [
                {
                    "band": "goose",
                    "model_version": "deal_v2",
                    "num_shows": 50,
                    "window_end": "2026-04-10",
                }
            ],
        }
    )

    report = module.build_model_readiness_report("deal", bands=["goose"], client=client)

    assert report["ready_for_backend"] is True
    assert report["ready_for_web_promotion"] is True
    assert report["bands"][0]["ready"] is True
    assert report["bands"][0]["replay_overlap"]["notebook"] == 50


def test_build_model_readiness_report_surfaces_missing_requirements():
    client = _ClientStub(
        {
            "predictions_deal": [],
            "prediction_songs": [],
            "historical_prediction_runs": _history_rows("deal", "deal_v2", count=12)
            + _history_rows("notebook", "notebook_v1", count=8),
            "accuracy_per_show": [
                {
                    "band": "goose",
                    "model_version": "deal_v2",
                    "show_id": f"show-{index}",
                }
                for index in range(10)
            ],
            "accuracy_deal": [],
        }
    )

    report = module.build_model_readiness_report("deal", bands=["goose"], client=client)

    assert report["ready_for_backend"] is False
    blockers = report["bands"][0]["blockers"]
    assert "canonical_predictions_missing" in blockers
    assert "prediction_projection_missing" in blockers
    assert "aggregate_windows_missing:50" in blockers
    assert "historical_runs_below_window:12/50" in blockers
    assert "per_show_accuracy_below_window:10/50" in blockers
    assert "replay_overlap_below_window:notebook:8/50" in blockers
