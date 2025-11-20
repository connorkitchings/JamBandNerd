from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.jambandnerd.data_collection.wsp.collector import WSPCollector
from src.jambandnerd.data_collection.wsp.orchestration import tourwrangler_fallback


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
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{'set_number': '1', 'song_position': 1}]

    # Act
    result = collector._scrape_single_setlist(show_info)

    # Assert
    assert result == []
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.assert_called_once()

@patch('src.jambandnerd.data_collection.wsp.collector.get_supabase_client')
@patch('src.jambandnerd.data_collection.wsp.collector.BeautifulSoup')
@patch('src.jambandnerd.data_collection.wsp.collector.parse_setlist_from_text')
def test_scrape_single_setlist_scrape_new(mock_parse_setlist, mock_beautiful_soup, mock_get_supabase_client):
    # Arrange
    mock_supabase_client = MagicMock()
    mock_get_supabase_client.return_value = mock_supabase_client
    collector = WSPCollector()

    show_info = {
        'show_id': '123',
        'source_url': 'http://example.com/setlist.html'
    }

    # Mock the response for no existing setlist
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Mock the parsed setlist
    mock_parse_setlist.return_value = [{'song_name': 'Song A'}]

    # Act
    with patch('src.jambandnerd.data_collection.wsp.collector.make_request') as mock_make_request:
        mock_response = MagicMock()
        mock_response.content = '<html></html>'
        mock_response.url = 'http://example.com/setlist.html'
        mock_make_request.return_value = mock_response
        result = collector._scrape_single_setlist(show_info)

    # Assert
    assert result == [{'song_name': 'Song A'}]
    mock_parse_setlist.assert_called_once()

@patch('src.jambandnerd.data_collection.wsp.orchestration.fetch_setlist_from_tourwrangler')
@patch('src.jambandnerd.data_collection.wsp.orchestration.get_supabase_client')
def test_tourwrangler_fallback(mock_get_supabase_client, mock_fetch_from_tw):
    # Arrange
    mock_supabase_client = MagicMock()
    mock_get_supabase_client.return_value = mock_supabase_client

    # Mock a recent show that is missing a setlist
    yesterday = date.today() - timedelta(days=1)
    mock_show = {
        'show_id': '456',
        'show_date': yesterday.isoformat(),
        'city': 'Atlanta',
        'state': 'GA'
    }
    mock_supabase_client.table.return_value.select.return_value.gte.return_value.lt.return_value.execute.return_value.data = [mock_show]
    mock_supabase_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [] # No existing setlist

    # Act
    tourwrangler_fallback(mock_supabase_client)

    # Assert
    mock_fetch_from_tw.assert_called_once()
