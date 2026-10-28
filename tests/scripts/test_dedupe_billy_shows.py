from __future__ import annotations

import pytest

from scripts.admin.dedupe_billy_shows import select_duplicate_shows


def show(show_id, date="2026-05-01"):
    return {"show_id": show_id, "show_date": date}


def songs(show_id, *names):
    return [{"show_id": show_id, "song_name": n} for n in names]


def test_ghost_with_full_sibling_is_selected():
    out = select_duplicate_shows([show(1), show(2)], songs(2, "a", "b", "c"), set())
    assert out["ghost"] == [1] and out["pair"] == []


def test_two_full_same_date_rows_are_not_selected():
    rows = [show(1), show(2)]
    setlists = songs(1, "a", "b", "c") + songs(2, "d", "e", "f")
    out = select_duplicate_shows(rows, setlists, set())
    assert out["ghost"] == [] and out["pair"] == []


def test_zero_song_row_without_full_sibling_is_kept():
    out = select_duplicate_shows([show(1), show(2)], songs(2, "a"), set())
    assert out["ghost"] == []


def test_allowlisted_pair_id_is_selected_only_when_requested():
    rows = [show(1201, "2019-02-24"), show(1202, "2019-02-24")]
    setlists = songs(1201, "a", "b", "c") + songs(1202, "a", "b", "c")
    assert select_duplicate_shows(rows, setlists, set())["pair"] == []
    out = select_duplicate_shows(rows, setlists, set(), ["1202"])
    assert out["pair"] == [1202]


def test_unknown_delete_id_is_rejected():
    with pytest.raises(ValueError, match="allowlist"):
        select_duplicate_shows([show(5)], [], set(), ["5"])


def test_both_ids_of_a_pair_are_rejected():
    with pytest.raises(ValueError, match="both"):
        select_duplicate_shows([], [], set(), ["31152", "29184"])


def test_referenced_ghost_is_skipped():
    out = select_duplicate_shows([show(1), show(2)], songs(2, "a", "b", "c"), {"1"})
    assert out["ghost"] == [] and out["skipped"] == [(1, "ghost")]


def test_referenced_allowlisted_pair_row_is_selected_with_accuracy_rows():
    rows = [show(29184, "2026-09-28"), show(31152, "2026-09-28")]
    out = select_duplicate_shows(rows, [], {"29184", "31152"}, ["29184"])
    assert out["pair"] == [29184] and out["skipped"] == []
    assert out["accuracy_show_ids"] == ["29184"]
