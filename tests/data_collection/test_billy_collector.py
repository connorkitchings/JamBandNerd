from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.jambandnerd.data_collection.billy.collector import BillyCollector


class TestBillyCollector:
    @pytest.fixture
    def collector(self):
        return BillyCollector()

    def test_collect_shows_parses_html(self, collector):
        # BillyBase past-shows card structure.
        mock_html = """
        <html>
            <article class="ecs-post-loop">
                <a href="#"></a>
                <a href="/show/van-andel-arena-grand-rapids-mi/">
                    Van Andel Arena – Grand Rapids, MI
                </a>
                <a href="/show/van-andel-arena-grand-rapids-mi/">
                    2023-10-31
                </a>
            </article>
        </html>
        """

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            shows = collector.collect_shows(
                start_date=date(2023, 10, 31), end_date=date(2023, 11, 1)
            )

            assert len(shows) == 1
            assert shows[0]["show_date"] == "2023-10-31"
            assert shows[0]["venue_name"] == "Van Andel Arena"
            assert shows[0]["venue_city"] == "Grand Rapids"
            assert shows[0]["venue_state"] == "MI"
            assert shows[0]["source_url"] == (
                "https://billybase.net/show/van-andel-arena-grand-rapids-mi/"
            )

    def test_collect_setlists_parses_html(self, collector):
        mock_html = """
        <html>
            <link rel="canonical" href="https://billybase.net/show/van-andel-arena-grand-rapids-mi/">
            <section>
                <div class="elementor-widget-container">
                    <h2>SETLIST</h2>
                </div>
                <div class="elementor-widget-container">
                    <div class="elementor-shortcode">
                        <p>Set 1</p>
                        <ol>
                            <li>
                                <a href="/song/dust-in-a-baggie/">Dust in a Baggie</a>
                                <sup class="item-notes"></sup>
                            </li>
                        </ol>
                        <p>Encore</p>
                        <ol>
                            <li>
                                <a href="/song/meet-me-at-the-creek/">Meet Me At The Creek</a>
                                <sup class="item-notes"></sup>
                            </li>
                        </ol>
                    </div>
                </div>
            </section>
        </html>
        """

        shows_to_process = [
            {
                "show_id": "1",
                "source_url": "https://billybase.net/show/van-andel-arena-grand-rapids-mi/",
                "source_uuid": "uuid1",
                "show_date": "2023-10-31",
            }
        ]

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            setlists = collector.collect_setlists(shows_to_process)

            assert len(setlists) == 2
            assert setlists[0]["song_name"] == "Dust in a Baggie"
            assert setlists[0]["set_number"] == 1
            assert setlists[0]["is_segue"] is False
            assert setlists[1]["song_name"] == "Meet Me At The Creek"
            assert setlists[1]["set_number"] == 99  # Encore default
            assert setlists[1]["encore"] is True

    def test_collect_songs_deferred(self, collector):
        with patch.object(collector.session, "get") as mock_get:
            # collect_songs does not hit the network in the deferred implementation.
            songs = collector.collect_songs()
            assert songs == []
            mock_get.assert_not_called()

    def test_parse_show_card_extracts_show(self, collector):
        from bs4 import BeautifulSoup

        html = """
        <article class="ecs-post-loop">
            <a href="#"></a>
            <a href="/show/red-rocks-amphitheatre-morrison-co/">
                Red Rocks Amphitheatre – Morrison, CO
            </a>
            <a href="/show/red-rocks-amphitheatre-morrison-co/">
                2026-08-15
            </a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("article", class_="ecs-post-loop")
        show = collector._parse_show_card(card)

        assert show is not None
        assert show["show_date"] == "2026-08-15"
        assert show["venue_name"] == "Red Rocks Amphitheatre"
        assert show["venue_city"] == "Morrison"
        assert show["venue_state"] == "CO"
        assert show["source_url"] == (
            "https://billybase.net/show/red-rocks-amphitheatre-morrison-co/"
        )

    def test_parse_show_page_extracts_info(self, collector):
        from bs4 import BeautifulSoup

        html = """
        <html>
            <link rel="canonical" href="https://billybase.net/show/fishers-event-center-fishers-in/">
            <section>
                <h2>SHOW INFO</h2>
                <h2>SHOW DATE</h2>
                <h2>2026-08-08</h2>
                <h2>SHOW VENUE</h2>
                <h2>Fishers Event Center</h2>
                <h2>TOUR</h2>
                <h2>Spring Tour 2026</h2>
                <h2>CITY</h2>
                <h2>Fishers</h2>
                <h2>STATE / COUNTRY</h2>
                <h2>Indiana</h2>
            </section>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        show = collector._parse_show_page(soup)

        assert show is not None
        assert show["show_date"] == "2026-08-08"
        assert show["venue_name"] == "Fishers Event Center"
        assert show["venue_city"] == "Fishers"
        assert show["source_url"] == (
            "https://billybase.net/show/fishers-event-center-fishers-in/"
        )

    def test_find_prev_show_url(self, collector):
        from bs4 import BeautifulSoup

        html = """
        <a class="elementor-button" href="https://billybase.net/show/prev-show/">&lt; Prev</a>
        """
        soup = BeautifulSoup(html, "html.parser")
        url = collector._find_prev_show_url(soup)
        assert url == "https://billybase.net/show/prev-show/"

    def test_collect_setlists_detects_segue(self, collector):
        mock_html = """
        <html>
            <link rel="canonical" href="https://billybase.net/show/van-andel-arena-grand-rapids-mi/">
            <section>
                <div class="elementor-widget-container">
                    <h2>SETLIST</h2>
                </div>
                <div class="elementor-widget-container">
                    <div class="elementor-shortcode">
                        <p>Set 1</p>
                        <ol>
                            <li>
                                <a href="/song/song-a/">Song A</a>
                                <sup class="item-notes"></sup>
                                <div class="tooltip">
                                    <img src="https://billybase.net/wp-content/uploads/greater-than.png">
                                </div>
                            </li>
                            <li>
                                <a href="/song/song-b/">Song B</a>
                                <sup class="item-notes">1</sup>
                            </li>
                        </ol>
                    </div>
                </div>
            </section>
        </html>
        """

        shows_to_process = [
            {
                "show_id": "1",
                "source_url": "https://billybase.net/show/van-andel-arena-grand-rapids-mi/",
                "source_uuid": "uuid1",
                "show_date": "2023-10-31",
            }
        ]

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            setlists = collector.collect_setlists(shows_to_process)

            assert len(setlists) == 2
            assert setlists[0]["song_name"] == "Song A"
            assert setlists[0]["is_segue"] is True
            assert setlists[1]["song_name"] == "Song B"
            assert setlists[1]["is_segue"] is False
            assert setlists[1]["song_notes"] == "1"


def _card(slug, day):
    return (
        f'<article class="ecs-post-loop"><a href="#"></a>'
        f'<a href="/show/{slug}/">Venue {slug} \u2013 Town, NY</a>'
        f'<a href="/show/{slug}/">{day}</a></article>'
    )


def _show_page(slug, day, prev_slug=None):
    from bs4 import BeautifulSoup

    prev = (
        f'<a href="https://billybase.net/show/{prev_slug}/">&lt; Prev</a>'
        if prev_slug
        else ""
    )
    return BeautifulSoup(
        f"""<html>
        <link rel="canonical" href="https://billybase.net/show/{slug}/">
        <section><h2>SHOW INFO</h2><h2>SHOW DATE</h2><h2>{day}</h2>
        <h2>SHOW VENUE</h2><h2>Venue {slug}</h2><h2>CITY</h2><h2>Town</h2>
        <h2>STATE / COUNTRY</h2><h2>New York</h2></section>{prev}</html>""",
        "html.parser",
    )


def _walkback_collector(pages):
    from bs4 import BeautifulSoup

    collector = BillyCollector()
    fetched = []

    def fake_fetch(url):
        fetched.append(url)
        page = pages[url]
        return BeautifulSoup(page, "html.parser") if isinstance(page, str) else page

    collector._fetch_soup = fake_fetch  # type: ignore[method-assign]
    return collector, fetched


LISTING = "https://billybase.net/past-shows/"


def _url(slug):
    return f"https://billybase.net/show/{slug}/"


class TestPastShowsWalkback:
    def test_walks_back_past_oldest_card_down_to_start_date(self):
        pages = {
            LISTING: _card("s-0925", "2026-09-25"),
            _url("s-0925"): _show_page("s-0925", "2026-09-25", "s-0920"),
            _url("s-0920"): _show_page("s-0920", "2026-09-20", "s-0801"),
            _url("s-0801"): _show_page("s-0801", "2026-08-01", "s-0418"),
            _url("s-0418"): _show_page("s-0418", "2026-04-10", "s-0101"),
        }
        collector, fetched = _walkback_collector(pages)

        shows = collector._collect_past_shows(date(2026, 4, 15))

        assert [s["show_date"] for s in shows] == [
            "2026-09-25",
            "2026-09-20",
            "2026-08-01",
            "2026-04-10",
        ]
        assert _url("s-0101") not in fetched

    def test_stops_at_first_show_on_or_before_start_date(self):
        pages = {
            LISTING: _card("s-0925", "2026-09-25"),
            _url("s-0925"): _show_page("s-0925", "2026-09-25", "s-0801"),
            _url("s-0801"): _show_page("s-0801", "2026-08-01", "s-0701"),
            _url("s-0701"): _show_page("s-0701", "2026-07-01", "s-0601"),
        }
        collector, fetched = _walkback_collector(pages)

        shows = collector._collect_past_shows(date(2026, 8, 1))

        assert [s["show_date"] for s in shows] == ["2026-09-25", "2026-08-01"]
        assert _url("s-0701") not in fetched

    def test_no_walkback_when_oldest_card_already_covers_start_date(self):
        pages = {LISTING: _card("s-0925", "2026-09-25") + _card("s-0301", "2026-03-01")}
        collector, fetched = _walkback_collector(pages)

        shows = collector._collect_past_shows(date(2026, 4, 15))

        assert len(shows) == 2
        assert fetched == [LISTING]

    def test_no_prev_link_returns_card_shows_only(self):
        pages = {
            LISTING: _card("s-0925", "2026-09-25"),
            _url("s-0925"): _show_page("s-0925", "2026-09-25", None),
        }
        collector, _ = _walkback_collector(pages)

        shows = collector._collect_past_shows(date(2026, 4, 15))

        assert [s["show_date"] for s in shows] == ["2026-09-25"]
