from __future__ import annotations

from types import SimpleNamespace

from scripts import run_billy_collection as rbc


def _stub(monkeypatch, existing_rows, counts):
    class Query:
        def select(self, *_a, **_k):
            return self

        gte = lte = select

        def execute(self):
            return SimpleNamespace(data=existing_rows)

    monkeypatch.setattr(
        rbc, "get_supabase_client", lambda: SimpleNamespace(table=lambda _n: Query())
    )
    monkeypatch.setattr(rbc, "fetch_setlist_row_counts", lambda _t, _ids: counts)


def _row(show_id, uuid, venue, date="2026-05-01"):
    return {
        "show_id": show_id,
        "source_uuid": uuid,
        "show_date": date,
        "venue_name": venue,
    }


def _scraped(venue, date="2026-05-01"):
    return [{"show_date": date, "venue_name": venue, "source_uuid": "slug-uuid"}]


def test_reconcile_prefers_existing_row_with_setlist(monkeypatch):
    rows = [_row(1, "empty", "The Venue"), _row(2, "full", "The Venue")]
    _stub(monkeypatch, rows, {"2": 12})
    out = rbc._reconcile_existing_show_uuids_by_date_venue(_scraped("The Venue"))
    assert out[0]["source_uuid"] == "full"


def test_reconcile_matches_venue_prefix_variant(monkeypatch):
    _stub(monkeypatch, [_row(1, "old", "Pechanga Arena San Diego")], {})
    out = rbc._reconcile_existing_show_uuids_by_date_venue(_scraped("Pechanga Arena"))
    assert out[0]["source_uuid"] == "old"


def test_reconcile_matches_venue_token_subset(monkeypatch):
    _stub(monkeypatch, [_row(1, "old", "The Fillmore Auditorium Denver")], {})
    out = rbc._reconcile_existing_show_uuids_by_date_venue(
        _scraped("Denver Fillmore Auditorium")
    )
    assert out[0]["source_uuid"] == "old"


def test_reconcile_ignores_unrelated_venue_on_same_date(monkeypatch):
    _stub(monkeypatch, [_row(1, "old", "Red Rocks Amphitheatre")], {"1": 5})
    out = rbc._reconcile_existing_show_uuids_by_date_venue(_scraped("Fillmore"))
    assert out[0]["source_uuid"] == "slug-uuid"


def test_refetch_existing_flag_disables_setlist_skipping(monkeypatch):
    calls = []
    monkeypatch.setattr(rbc, "run_billy_collection", lambda **kw: calls.append(kw))
    monkeypatch.setattr("sys.argv", ["run_billy_collection.py", "--refetch-existing"])
    rbc.main()
    assert calls[0]["skip_existing_setlists"] is False
    monkeypatch.setattr("sys.argv", ["run_billy_collection.py"])
    rbc.main()
    assert calls[1]["skip_existing_setlists"] is True
