import json
from datetime import date, datetime, timedelta, timezone

from scripts.validate_prediction_tables import validate_predictions


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []
        self._orders = []
        self._limit = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, column, desc=False):
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

    def table(self, name):
        return _QueryStub(self._table_rows.get(name, []))


def _prediction_rows(
    *, latest_predictions, stale_predictions=None, latest_predicted_at=None
):
    latest_predicted_at = latest_predicted_at or datetime.now(timezone.utc)
    stale_predicted_at = latest_predicted_at - timedelta(days=3)
    stale_predictions = stale_predictions or latest_predictions

    rows = {
        "predictions_notebook": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-03-25",
                "predicted_at": stale_predicted_at.isoformat(),
                "top_k": len(stale_predictions),
                "predictions": json.dumps(stale_predictions),
            },
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-03-20",
                "predicted_at": latest_predicted_at.isoformat(),
                "top_k": len(latest_predictions),
                "predictions": json.dumps(latest_predictions),
            },
        ],
        "predictions_ckplus": [
            {
                "band": "goose",
                "model_version": "deal_v2",
                "reference_date": "2026-03-25",
                "predicted_at": stale_predicted_at.isoformat(),
                "top_k": len(stale_predictions),
                "predictions": json.dumps(stale_predictions),
            },
            {
                "band": "goose",
                "model_version": "deal_v2",
                "reference_date": "2026-03-20",
                "predicted_at": latest_predicted_at.isoformat(),
                "top_k": len(latest_predictions),
                "predictions": json.dumps(latest_predictions),
            },
        ],
        "predictions_deal": [],
    }
    rows["predictions_deal"] = rows.pop("predictions_ckplus")
    return rows


def test_validate_predictions_uses_latest_predicted_at(monkeypatch, capsys):
    rows = _prediction_rows(
        latest_predictions=[{"song_name": "Fresh Song"}],
        stale_predictions=[{"song_name": "Old Song"}],
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [
            {
                "reference_date": reference_date,
                "song_name": "Fresh Song",
                "rank": 1,
            }
        ],
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 0
    captured = capsys.readouterr().out
    assert "top_song=Fresh Song" in captured
    assert "reference_date=2026-03-20" in captured


def test_validate_predictions_fails_on_invalid_latest_json(monkeypatch, capsys):
    now = datetime.now(timezone.utc)
    rows = _prediction_rows(
        latest_predictions=[{"song_name": "Fresh Song"}], latest_predicted_at=now
    )
    rows["predictions_notebook"][1]["predictions"] = "{bad json"
    rows["predictions_deal"][1]["predictions"] = "{bad json"
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [],
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 2
    captured = capsys.readouterr().out
    assert "[FAIL] goose: invalid JSON payload" in captured


def test_validate_predictions_warns_on_missing_latest_predicted_at(monkeypatch, capsys):
    rows = _prediction_rows(latest_predictions=[{"song_name": "Fresh Song"}])
    rows["predictions_notebook"][1]["predicted_at"] = None
    rows["predictions_deal"][1]["predicted_at"] = None
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [],
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 2
    captured = capsys.readouterr().out
    assert "[WARN] goose: missing predicted_at timestamp" in captured


def test_validate_predictions_fails_on_projection_mismatch(monkeypatch, capsys):
    rows = _prediction_rows(
        latest_predictions=[
            {"song_name": "Fresh Song"},
            {"song_name": "Second Song"},
        ]
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [
            {
                "reference_date": reference_date,
                "song_name": "Wrong Song",
                "rank": 1,
            },
            {
                "reference_date": reference_date,
                "song_name": "Second Song",
                "rank": 2,
            },
        ],
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 2
    captured = capsys.readouterr().out
    assert (
        "projection top_song=Wrong Song does not match canonical Fresh Song" in captured
    )


def test_validate_predictions_flags_stale_recent_projection_dates(monkeypatch, capsys):
    now = datetime.now(timezone.utc)
    recent_ref = (date.today() + timedelta(days=2)).isoformat()
    old_ref = (date.today() - timedelta(days=14)).isoformat()
    rows = _prediction_rows(
        latest_predictions=[
            {"song_name": "Fresh Song"},
            {"song_name": "Second Song"},
        ],
        latest_predicted_at=now,
    )
    rows["prediction_songs"] = [
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "reference_date": recent_ref,
            "predicted_at": (now - timedelta(days=7)).isoformat(),
        },
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "reference_date": old_ref,
            "predicted_at": now.isoformat(),
        },
        {
            "band": "goose",
            "model_version": "deal_v2",
            "reference_date": recent_ref,
            "predicted_at": (now - timedelta(days=7)).isoformat(),
        },
        {
            "band": "goose",
            "model_version": "deal_v2",
            "reference_date": old_ref,
            "predicted_at": now.isoformat(),
        },
    ]
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [
            {
                "reference_date": reference_date,
                "song_name": "Fresh Song",
                "rank": 1,
            },
            {
                "reference_date": reference_date,
                "song_name": "Second Song",
                "rank": 2,
            },
        ],
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 2
    captured = capsys.readouterr().out
    assert (
        f"prediction_songs reference_date={recent_ref} has predicted_at older than 48h cutoff"
        in captured
    )
    assert f"prediction_songs reference_date={old_ref}" not in captured


def test_validate_predictions_ignores_stale_old_projection_outside_window(
    monkeypatch, capsys
):
    now = datetime.now(timezone.utc)
    old_ref = (date.today() - timedelta(days=14)).isoformat()
    rows = _prediction_rows(
        latest_predictions=[
            {"song_name": "Fresh Song"},
            {"song_name": "Second Song"},
        ],
        latest_predicted_at=now,
    )
    rows["prediction_songs"] = [
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "reference_date": old_ref,
            "predicted_at": (now - timedelta(days=10)).isoformat(),
        },
        {
            "band": "goose",
            "model_version": "deal_v2",
            "reference_date": old_ref,
            "predicted_at": (now - timedelta(days=10)).isoformat(),
        },
    ]
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [
            {
                "reference_date": reference_date,
                "song_name": "Fresh Song",
                "rank": 1,
            },
            {
                "reference_date": reference_date,
                "song_name": "Second Song",
                "rank": 2,
            },
        ],
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 0
    captured = capsys.readouterr().out
    assert f"prediction_songs reference_date={old_ref}" not in captured


def test_validate_predictions_can_scope_to_selected_model(monkeypatch, capsys):
    now = datetime.now(timezone.utc)
    rows = {
        "predictions_notebook": [
            {
                "band": "goose",
                "model_version": "notebook_v1",
                "reference_date": "2026-03-25",
                "predicted_at": (now - timedelta(days=10)).isoformat(),
                "top_k": 1,
                "predictions": json.dumps([{"song_name": "Old Song"}]),
            }
        ],
        "predictions_deal": [
            {
                "band": "goose",
                "model_version": "deal_v2",
                "reference_date": "2026-03-27",
                "predicted_at": now.isoformat(),
                "top_k": 1,
                "predictions": json.dumps([{"song_name": "Fresh Deal Song"}]),
            }
        ],
    }
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.fetch_prediction_songs_for_date",
        lambda band, model_slug, reference_date: [
            {
                "reference_date": reference_date,
                "song_name": "Fresh Deal Song",
                "rank": 1,
            }
        ],
    )

    failures = validate_predictions(
        bands=["goose"],
        max_age_hours=48,
        models=["deal"],
    )

    assert failures == 0
    captured = capsys.readouterr().out
    assert "predictions_deal" in captured
    assert "predictions_notebook" not in captured
