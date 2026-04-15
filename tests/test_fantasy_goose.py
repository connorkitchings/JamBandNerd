from __future__ import annotations

from datetime import date, datetime

from jambandnerd.integrations.fantasy_goose import (
    EASTERN_TZ,
    FANTASY_GOOSE_VERIFICATION_DELAY_MS,
    FANTASY_GOOSE_VERIFICATION_RETRIES,
    FantasyGooseShow,
    FantasyGooseSong,
    has_entry_for_date,
    has_existing_entry,
    match_predictions_to_fg_songs,
    normalize_song_name,
    parse_fantasy_goose_show,
    select_target_show,
)


def test_parse_fantasy_goose_show_parses_label_and_cutoff():
    show = parse_fantasy_goose_show(
        {
            "value": "995",
            "label": "04/10/2026 - ExploreAsheville.com Arena - Asheville, NC",
            "cutoff": "2026-04-10 18:00:00",
        }
    )

    assert show.show_id == "995"
    assert show.show_date == date(2026, 4, 10)
    assert show.cutoff_at is not None
    assert show.cutoff_at.hour == 18


def test_select_target_show_returns_no_show_when_date_missing():
    result = select_target_show(
        [
            FantasyGooseShow(
                show_id="995",
                label="04/10/2026 - ExploreAsheville.com Arena - Asheville, NC",
                show_date=date(2026, 4, 10),
                cutoff_at=datetime(2026, 4, 10, 18, 0, tzinfo=EASTERN_TZ),
            )
        ],
        target_date=date(2026, 4, 11),
        now_et=datetime(2026, 4, 10, 12, 0, tzinfo=EASTERN_TZ),
    )

    assert result.status == "no_show_tonight"


def test_select_target_show_returns_cutoff_passed_when_deadline_elapsed():
    result = select_target_show(
        [
            FantasyGooseShow(
                show_id="995",
                label="04/10/2026 - ExploreAsheville.com Arena - Asheville, NC",
                show_date=date(2026, 4, 10),
                cutoff_at=datetime(2026, 4, 10, 18, 0, tzinfo=EASTERN_TZ),
            )
        ],
        target_date=date(2026, 4, 10),
        now_et=datetime(2026, 4, 10, 19, 0, tzinfo=EASTERN_TZ),
    )

    assert result.status == "cutoff_passed"
    assert result.target_show is not None


def test_select_target_show_picks_earliest_open_show():
    result = select_target_show(
        [
            FantasyGooseShow(
                show_id="996",
                label="04/10/2026 - Late Show",
                show_date=date(2026, 4, 10),
                cutoff_at=datetime(2026, 4, 10, 21, 0, tzinfo=EASTERN_TZ),
            ),
            FantasyGooseShow(
                show_id="995",
                label="04/10/2026 - Early Show",
                show_date=date(2026, 4, 10),
                cutoff_at=datetime(2026, 4, 10, 18, 0, tzinfo=EASTERN_TZ),
            ),
        ],
        target_date=date(2026, 4, 10),
        now_et=datetime(2026, 4, 10, 12, 0, tzinfo=EASTERN_TZ),
    )

    assert result.status == "ready"
    assert result.target_show is not None
    assert result.target_show.show_id == "995"


def test_match_predictions_to_fg_songs_uses_normalization():
    predictions = [
        {"rank": 1, "song_name": "Turbulence & The Night Rays"},
        {"rank": 2, "song_name": "Drippin'"},
    ]
    songs = [
        FantasyGooseSong(id="1", name="Turbulence and The Night Rays"),
        FantasyGooseSong(id="2", name="Drippin'"),
    ]

    matches, missing = match_predictions_to_fg_songs(predictions, songs, limit=2)

    assert [item.fantasy_goose_song_id for item in matches] == ["1", "2"]
    assert missing == []


def test_match_predictions_to_fg_songs_reports_unresolved_names():
    predictions = [
        {"rank": 1, "song_name": "Arcadia"},
        {"rank": 2, "song_name": "Madhuvan"},
    ]
    songs = [FantasyGooseSong(id="1", name="Arcadia")]

    matches, missing = match_predictions_to_fg_songs(predictions, songs, limit=2)

    assert [item.prediction_name for item in matches] == ["Arcadia"]
    assert missing == ["Madhuvan"]


def test_has_existing_entry_matches_show_label_and_venue():
    show = FantasyGooseShow(
        show_id="995",
        label="04/10/2026 - ExploreAsheville.com Arena - Asheville, NC",
        show_date=date(2026, 4, 10),
        cutoff_at=datetime(2026, 4, 10, 18, 0, tzinfo=EASTERN_TZ),
    )

    assert has_existing_entry(
        "My Picks\n04/10/2026 - ExploreAsheville.com Arena - Asheville, NC\nArcadia",
        show,
    )


def test_has_entry_for_date_detects_existing_pick_by_date():
    assert has_entry_for_date(
        "My Picks\n04/10/2026 - ExploreAsheville.com Arena", date(2026, 4, 10)
    )


def test_normalize_song_name_canonicalizes_punctuation():
    assert normalize_song_name("Turbulence & The Night Rays") == normalize_song_name(
        "Turbulence and The Night Rays"
    )


def test_verification_constants_are_reasonable():
    assert FANTASY_GOOSE_VERIFICATION_RETRIES >= 2
    assert FANTASY_GOOSE_VERIFICATION_DELAY_MS >= 500


def test_has_existing_entry_matches_date_and_venue_separately():
    show = FantasyGooseShow(
        show_id="995",
        label="04/14/2026 - War Memorial Auditorium - Fort Lauderdale, FL",
        show_date=date(2026, 4, 14),
        cutoff_at=datetime(2026, 4, 14, 18, 0, tzinfo=EASTERN_TZ),
    )
    assert has_existing_entry(
        "04/14/2026 - War Memorial Auditorium - Fort Lauderdale, FL", show
    )


def test_has_existing_entry_rejects_wrong_venue():
    show = FantasyGooseShow(
        show_id="995",
        label="04/14/2026 - War Memorial Auditorium - Fort Lauderdale, FL",
        show_date=date(2026, 4, 14),
        cutoff_at=datetime(2026, 4, 14, 18, 0, tzinfo=EASTERN_TZ),
    )
    assert not has_existing_entry("04/14/2026 - Some Other Venue - Tampa, FL", show)


def test_has_existing_entry_matches_on_date_and_venue_even_without_full_label():
    show = FantasyGooseShow(
        show_id="995",
        label="04/14/2026 - War Memorial Auditorium - Fort Lauderdale, FL",
        show_date=date(2026, 4, 14),
        cutoff_at=datetime(2026, 4, 14, 18, 0, tzinfo=EASTERN_TZ),
    )
    assert has_existing_entry(
        "Your Picks:\n04/14/2026\nwar memorial auditorium - fort lauderdale, fl\nArcadia, Drippin'",
        show,
    )
