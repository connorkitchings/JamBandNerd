from __future__ import annotations

from scripts.admin.dedupe_um_shows import select_duplicate_shows
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
