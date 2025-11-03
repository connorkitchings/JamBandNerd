"""A module for reviewing and cleaning setlist data before upserting to the database."""

from typing import Any, Dict, List

def review_setlist(setlist_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reviews and cleans a setlist, handling special cases like 'Lawyers, Guns, and Money'.

    Args:
        setlist_data: A list of dictionaries, where each dictionary represents a song in the setlist.

    Returns:
        A cleaned list of dictionaries representing the setlist.
    """
    i = 0
    while i < len(setlist_data):
        if setlist_data[i].get('song_name') == 'Lawyers' and i + 2 < len(setlist_data) and setlist_data[i+1].get('song_name') == 'Guns' and setlist_data[i+2].get('song_name') == 'And Money':
            # Combine the songs
            setlist_data[i]['song_name'] = 'Lawyers, Guns, and Money'
            
            # Remove the extra entries
            del setlist_data[i+1]
            del setlist_data[i+1] # Note: the index shifts after the first deletion

            # Renumber the song positions
            for j in range(i + 1, len(setlist_data)):
                setlist_data[j]['song_position'] -= 2
        i += 1
    return setlist_data
