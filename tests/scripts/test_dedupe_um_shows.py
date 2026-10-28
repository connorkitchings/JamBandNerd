from __future__ import annotations

import pytest

from scripts.admin import dedupe_um_shows as dedupe
from scripts.admin.dedupe_um_shows import select_duplicate_shows, validate_delete_ids
from scripts.run_um_collection import normalize_um_show_url

OLD = "https://allthings.umphreys.com/2026-05-01"
NEW = "https://allthings.umphreys.com/setlists/2026-05-01"


def show(show_id, url, date="2026-05-01"):
    return {"show_id": show_id, "source_url": url, "show_date": date}


def songs(show_id, *names):
    return [{"show_id": show_id, "song_name": n} for n in names]


def test_normalizer_maps_old_and_new_urls_to_same_value():
    assert normalize_um_show_url(NEW) == normalize_um_show_url(OLD) == OLD


def test_normalizer_keeps_multi_show_suffix_distinct():
    assert normalize_um_show_url(NEW + "-2") != normalize_um_show_url(NEW)


def test_ghost_with_full_sibling_is_selected():
    rows = [show(1, OLD), show(2, "https://x/other")]
    out = select_duplicate_shows(rows, songs(2, "a", "b", "c"), set())
    assert out["ghost"] == [1] and out["pair"] == []


def test_empty_row_with_thin_sibling_is_not_ghost():
    rows = [show(1, OLD), show(2, "https://x/other")]
    out = select_duplicate_shows(rows, songs(2, "a", "b"), set())
    assert out["ghost"] == []


def test_same_url_identical_songs_deletes_row_without_setlists_segment():
    rows = [show(1, OLD), show(2, NEW)]
    sl = songs(1, "a", "b", "c") + songs(2, "a", "b", "c")
    out = select_duplicate_shows(rows, sl, set())
    assert out["pair"] == [1] and out["ghost"] == []


def test_same_url_differing_songs_not_deleted():
    rows = [show(1, OLD), show(2, NEW)]
    sl = songs(1, "a", "b", "c") + songs(2, "a", "b", "d")
    out = select_duplicate_shows(rows, sl, set())
    assert out["pair"] == [] and out["ghost"] == []


def test_dash_two_pages_not_merged():
    rows = [show(1, OLD), show(2, NEW + "-2")]
    sl = songs(1, "a", "b", "c") + songs(2, "a", "b", "c")
    out = select_duplicate_shows(rows, sl, set())
    assert out["pair"] == []


def test_accuracy_referenced_candidate_is_skipped():
    rows = [show(1, OLD), show(2, NEW)]
    sl = songs(1, "a", "b", "c") + songs(2, "a", "b", "c")
    out = select_duplicate_shows(rows, sl, {"1"})
    assert out["pair"] == [] and out["skipped"] == [(1, "pair")]


def test_referenced_pair_selected_when_flag_on():
    rows = [show(1, OLD), show(2, NEW)]
    sl = songs(1, "a", "b", "c") + songs(2, "a", "b", "c")
    out = select_duplicate_shows(rows, sl, {"1"}, delete_referenced_pairs=True)
    assert out["pair"] == [1]
    assert out["accuracy_show_ids"] == ["1"]
    assert out["skipped"] == []


def test_referenced_pair_skipped_when_flag_off():
    rows = [show(1, OLD), show(2, NEW)]
    sl = songs(1, "a", "b", "c") + songs(2, "a", "b", "c")
    out = select_duplicate_shows(rows, sl, {"1"})
    assert out["pair"] == [] and out["accuracy_show_ids"] == []


def test_referenced_ghost_still_skipped_when_flag_on():
    rows = [show(1, "https://x/a"), show(2, "https://x/b")]
    out = select_duplicate_shows(
        rows, songs(2, "a", "b", "c"), {"1"}, delete_referenced_pairs=True
    )
    assert out["ghost"] == [] and out["skipped"] == [(1, "ghost")]
    assert out["accuracy_show_ids"] == []


# --- --delete-ids ---------------------------------------------------------


def vshow(show_id, venue="Ryman", date="2025-04-05"):
    return {
        "show_id": show_id,
        "show_date": date,
        "venue_name": venue,
        "source_url": f"https://x/{show_id}",
    }


def test_delete_ids_accepts_ids_with_surviving_sibling():
    rows = [
        vshow(1),
        vshow(2),
        vshow(3, "Moon", "2026-04-30"),
        vshow(4, "Moon", "2026-04-30"),
    ]
    assert validate_delete_ids(rows, ["1", "3"]) == ["1", "3"]


def test_delete_ids_unknown_id_rejected():
    with pytest.raises(ValueError, match="not found"):
        validate_delete_ids([vshow(1), vshow(2)], ["9"])


def test_delete_ids_without_sibling_rejected():
    rows = [vshow(1), vshow(2, "Other Venue"), vshow(3, date="2025-04-06")]
    with pytest.raises(ValueError, match="no same-date, same-venue sibling"):
        validate_delete_ids(rows, ["1"])


def test_delete_ids_both_pair_members_rejected():
    with pytest.raises(ValueError, match="siblings are listed"):
        validate_delete_ids([vshow(1), vshow(2)], ["1", "2"])


class FakeClient:
    def __init__(self, calls):
        self.calls = calls

    def table(self, name):
        return FakeQuery(self.calls, name)


class FakeQuery:
    def __init__(self, calls, name):
        self.calls, self.name, self.filters = calls, name, []

    def delete(self):
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def execute(self):
        self.calls.append(("delete", self.name, tuple(self.filters)))


def test_delete_shows_backs_up_before_deleting_in_order(tmp_path, monkeypatch):
    calls = []
    real = dedupe.write_backup
    monkeypatch.setattr(
        dedupe, "write_backup", lambda d, p: (calls.append(("backup",)), real(d, p))[1]
    )
    dedupe.delete_shows(
        FakeClient(calls),
        tmp_path,
        [1],
        [vshow(1), vshow(2)],
        songs(1, "a"),
        [{"id": 7, "show_id": 1}],
        {"1"},
    )
    assert [c[:2] for c in calls] == [
        ("backup",),
        ("delete", "setlist_accuracy"),
        ("delete", "um_setlists_raw"),
        ("delete", "um_shows_raw"),
    ]
    assert len(list(tmp_path.glob("dedupe_um_shows_*.json"))) == 1


def test_delete_ids_dry_run_writes_and_deletes_nothing(tmp_path, monkeypatch, capsys):
    calls = []
    client = FakeClient(calls)
    monkeypatch.setattr(dedupe, "get_supabase_client", lambda: client)
    tables = {
        "um_shows_raw": [vshow(1), vshow(2)],
        "um_setlists_raw": songs(1, "a", "b"),
        "setlist_accuracy": [{"id": 7, "show_id": 1}],
    }
    monkeypatch.setattr(dedupe, "fetch_all", lambda c, t, cols, **eq: tables[t])
    monkeypatch.setattr(
        "sys.argv", ["x", "--delete-ids", "1", "--backup-dir", str(tmp_path / "b")]
    )
    dedupe.main()
    assert calls == [] and not (tmp_path / "b").exists()
    out = capsys.readouterr().out
    assert "show_id=1: 2 songs, accuracy ids=[7]" in out
