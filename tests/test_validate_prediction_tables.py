import json
from datetime import date, datetime, timedelta, timezone

from jambandnerd.models.registry import get_band_metadata
from scripts.validate_prediction_tables import validate_predictions

GOOSE_MODEL_VERSION = get_band_metadata("goose").model_version


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
        self._filters.append(("eq", column, value))
        return self

    def gte(self, column, value):
        self._filters.append(("gte", column, value))
        return self

    def order(self, column, desc=False):
        self._orders.append((column, desc))
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        rows = list(self._rows)
        for op, column, value in self._filters:
            if op == "eq":
                rows = [row for row in rows if row.get(column) == value]
            elif op == "gte":
                rows = [row for row in rows if str(row.get(column) or "") >= value]
        for column, desc in reversed(self._orders):
            rows.sort(key=lambda row: row.get(column) or "", reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return _ResponseStub(rows)


class _ClientStub:
    def __init__(self, table_rows):
        self._table_rows = table_rows

    def table(self, name):
        return _QueryStub(self._table_rows.get(name, []))


_DEFAULT_GENERATED_AT = object()


def _rows(
    *,
    generated_at=_DEFAULT_GENERATED_AT,
    predictions=None,
    projection_song="Fresh Song",
):
    if generated_at is _DEFAULT_GENERATED_AT:
        generated_at = datetime.now(timezone.utc)
    predictions = predictions or [{"rank": 1, "song_name": "Fresh Song"}]
    target_show_date = (date.today() + timedelta(days=1)).isoformat()
    return {
        "setlist_predictions": [
            {
                "band": "goose",
                "model_version": GOOSE_MODEL_VERSION,
                "target_show_key": "show-1",
                "target_show_date": target_show_date,
                "reference_date": target_show_date,
                "generated_at": (
                    generated_at.isoformat() if generated_at is not None else None
                ),
                "top_k": len(predictions),
                "predictions": json.dumps(predictions),
            }
        ],
        "setlist_prediction_songs": [
            {
                "band": "goose",
                "model_version": GOOSE_MODEL_VERSION,
                "target_show_key": "show-1",
                "target_show_date": target_show_date,
                "reference_date": target_show_date,
                "generated_at": (
                    generated_at.isoformat() if generated_at is not None else None
                ),
                "top_k": len(predictions),
                "rank": 1,
                "song_name": projection_song,
            }
        ],
        "goose_shows_raw": [{"show_date": target_show_date}],
    }


def test_validate_predictions_uses_latest_generated_at(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(_rows()),
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 0
    captured = capsys.readouterr().out
    assert "[OK] goose:" in captured
    assert "top_song=Fresh Song" in captured


def test_validate_predictions_fails_on_invalid_latest_json(monkeypatch, capsys):
    rows = _rows()
    rows["setlist_predictions"][0]["predictions"] = "{bad json"
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 1
    assert "[FAIL] goose: invalid JSON payload" in capsys.readouterr().out


def test_validate_predictions_warns_on_missing_latest_generated_at(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(_rows(generated_at=None)),
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 1
    assert "[WARN] goose: missing generated_at timestamp" in capsys.readouterr().out


def test_validate_predictions_fails_on_projection_mismatch(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(_rows(projection_song="Wrong Song")),
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 1
    assert "projection top_song=Wrong Song" in capsys.readouterr().out


def test_validate_predictions_flags_stale_row(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(
            _rows(generated_at=datetime.now(timezone.utc) - timedelta(days=3))
        ),
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 1
    assert "[STALE] goose:" in capsys.readouterr().out


def test_validate_predictions_allows_stale_row_without_upcoming_show(
    monkeypatch, capsys
):
    # Stale canonical prediction, but the band has no upcoming show, so
    # regeneration is intentionally idle and the stale row is not a failure.
    rows = _rows(generated_at=datetime.now(timezone.utc) - timedelta(days=3))
    rows["goose_shows_raw"] = []  # no future show on record

    monkeypatch.setattr(
        "scripts.validate_prediction_tables.get_supabase_client",
        lambda: _ClientStub(rows),
    )

    failures = validate_predictions(bands=["goose"], max_age_hours=48)

    assert failures == 0
    assert "[OK] goose:" in capsys.readouterr().out
