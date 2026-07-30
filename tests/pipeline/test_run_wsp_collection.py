from __future__ import annotations

from datetime import datetime

from scripts import run_wsp_collection


def test_default_wsp_year_window_extends_into_next_year():
    # The default window must span into next year so newly-published future
    # tours are picked up immediately (no Jan-1 blind spot). The collector
    # treats an unpublished tour page (404) as a soft skip, so scanning next
    # year is safe even before everydaycompanion.com has posted it.
    today = datetime(2026, 7, 30)
    year_start, year_end = run_wsp_collection.default_wsp_year_window(today=today)

    assert (year_start, year_end) == (2025, 2027)


def test_default_wsp_year_window_uses_now_when_no_today_supplied():
    current_year = datetime.now().year
    year_start, year_end = run_wsp_collection.default_wsp_year_window()

    assert year_start == current_year - 1
    assert year_end == current_year + 1
