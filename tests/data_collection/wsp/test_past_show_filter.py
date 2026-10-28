from datetime import date

import pandas as pd

from jambandnerd.data_collection.wsp.orchestration import _only_past_shows

TODAY = date(2026, 6, 15)


def _kept(show_dates: list[str]) -> list[str]:
    df = pd.DataFrame({"show_id": show_dates, "show_date": show_dates})
    return _only_past_shows(df, today=TODAY)["show_id"].tolist()


def test_future_show_is_excluded():
    assert _kept(["2027-01-01"]) == []


def test_today_is_excluded():
    assert _kept(["2026-06-15"]) == []


def test_past_show_is_kept():
    assert _kept(["2026-06-14"]) == ["2026-06-14"]


def test_mixed_shows_keep_only_past_ones():
    dates = ["2026-06-14", "2026-06-15", "2026-06-16", "2027-02-01", "2020-01-01"]
    assert _kept(dates) == ["2026-06-14", "2020-01-01"]
