import pytest
from unittest.mock import MagicMock, patch
from src.jambandnerd.data_collection.wsp.collector import WSPCollector

@patch('src.jambandnerd.data_collection.wsp.collector.get_supabase_client')
def test_scrape_single_setlist_skip_existing(mock_get_supabase_client):
    # Arrange
    mock_supabase_client = MagicMock()
    mock_get_supabase_client.return_value = mock_supabase_client
    collector = WSPCollector()

    show_info = {
        'show_id': '123',
        'source_url': 'http://example.com/setlist.html'
    }

    # Mock the response for an existing setlist
    mock_supabase_client.table().select().eq().execute.return_value.data = [{'set_number': '1', 'song_position': 1}]

    # Act
    result = collector._scrape_single_setlist(show_info)

    # Assert
    assert result == []
    mock_supabase_client.table().select().eq().execute.assert_called_once_with()

@patch('src.jambandnerd.data_collection.wsp.collector.get_supabase_client')
@patch('src.jambandnerd.data_collection.wsp.collector.make_request')
@patch('src.jambandnerd.data_collection.wsp.collector.parse_setlist_from_text')
def test_scrape_single_setlist_scrape_new(mock_parse_setlist, mock_make_request, mock_get_supabase_client):
    # Arrange
    mock_supabase_client = MagicMock()
    mock_get_supabase_client.return_value = mock_supabase_client
    collector = WSPCollector()

    show_info = {
        'show_id': '123',
        'source_url': 'http://example.com/setlist.html'
    }

    # Mock the response for no existing setlist
    mock_supabase_client.table().select().eq().execute.return_value.data = []

    # Mock the HTML response
    mock_response = MagicMock()
    mock_response.content = '<html></html>'
    mock_response.url = 'http://example.com/setlist.html'
    mock_make_request.return_value = mock_response

    # Mock the parsed setlist
    mock_parse_setlist.return_value = [{'song_name': 'Song A'}]

    # Act
    result = collector._scrape_single_setlist(show_info)

    # Assert
    assert result == [{'song_name': 'Song A'}]
    mock_make_request.assert_called_once()
    mock_parse_setlist.assert_called_once()
