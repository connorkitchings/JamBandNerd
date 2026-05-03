from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.jambandnerd.data_collection.wsp.collector import WSPCollector
from src.jambandnerd.data_collection.wsp.orchestration import tourwrangler_fallback


@patch("src.jambandnerd.data_collection.wsp.collector.decode_ec_response")
@patch("src.jambandnerd.data_collection.wsp.collector.parse_setlist_from_text")
@patch("src.jambandnerd.data_collection.wsp.collector.make_request")
def test_scrape_single_setlist_scrape_new(
    mock_make_request, mock_parse_setlist, mock_decode
):
    # Arrange
    collector = WSPCollector()

    show_info = {"show_id": "123", "source_url": "http://example.com/setlist.html"}

    mock_parse_setlist.return_value = [{"song_name": "Song A"}]

    mock_response = MagicMock()
    mock_response.url = "http://example.com/setlist.html"
    mock_make_request.return_value = mock_response
    mock_decode.return_value = "<html></html>"

    # Act
    result = collector._scrape_single_setlist(show_info)

    # Assert
    assert result == [{"song_name": "Song A"}]
    mock_parse_setlist.assert_called_once()


@patch("src.jambandnerd.data_collection.wsp.orchestration.get_supabase_client")
def test_tourwrangler_fallback_uses_recent_resolver(
    mock_get_supabase_client, monkeypatch
):
    # Arrange
    mock_supabase_client = MagicMock()
    mock_get_supabase_client.return_value = mock_supabase_client
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._resolve_recent_wsp_fallback",
        lambda *_args, **_kwargs: (
            [
                {
                    "show_id": "456",
                    "set_number": "1",
                    "song_position": 1,
                    "song_name": "Disco",
                    "source": "panicstream",
                }
            ],
            "panicstream",
            [],
        ),
    )
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration.get_table_schema",
        lambda *_args, **_kwargs: [{"column_name": "source"}],
    )
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration.validate_and_upsert_dataframe",
        lambda *_args, **_kwargs: None,
    )

    # Mock a recent show that is missing a setlist
    yesterday = date.today() - timedelta(days=1)
    mock_show = {
        "show_id": "456",
        "show_date": yesterday.isoformat(),
        "city": "Atlanta",
        "state": "GA",
    }
    mock_supabase_client.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value.data = [
        mock_show
    ]
    # No existing setlist.
    mock_supabase_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = (
        []
    )

    # Act
    row_count, show_count = tourwrangler_fallback(mock_supabase_client)

    # Assert
    assert row_count == 1
    assert show_count == 1
