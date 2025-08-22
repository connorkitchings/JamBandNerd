"""Script to run the Phish data collection pipeline."""
import logging
import pandas as pd

from jambandnerd.data_collection.phish.collector import PhishCollector
from jambandnerd.db.operations import upsert_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    """Main function to run the Phish data collection and storage."""
    logging.info("Starting Phish data collection pipeline...")
    collector = PhishCollector()

    # --- Songs ---
    logging.info("--- Collecting Songs ---")
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = pd.DataFrame(songs_data)
        songs_df.drop_duplicates(subset=['songid'], inplace=True)
        songs_df.rename(columns={
            'songid': 'api_song_id',
            'song': 'song_name',
            'abbr': 'abbreviation',
            'debut': 'debut_date',
            'last_played': 'last_played_date'
        }, inplace=True)
        
        # Ensure all target columns exist, fill missing with None
        target_cols = ['api_song_id', 'song_name', 'slug', 'abbreviation', 'artist', 'debut_date', 'last_played_date', 'times_played', 'gap', 'last_permalink', 'debut_permalink']
        for col in target_cols:
            if col not in songs_df.columns:
                songs_df[col] = None
        final_songs_df = songs_df[target_cols].copy()

        upsert_dataframe("phish_songs_raw", final_songs_df, conflict_columns=["api_song_id"])
        logging.info(f"Upserted {len(final_songs_df)} songs into phish_songs_raw.")

    # --- Shows & Venues ---
    logging.info("--- Collecting Shows & Venues ---")
    shows_data = collector.collect_shows()
    if shows_data:
        shows_df = pd.DataFrame(shows_data)
        shows_df.drop_duplicates(subset=['showid'], inplace=True)
        shows_df.rename(columns={
            'showid': 'api_show_id',
            'venueid': 'api_venue_id',
            'created_at': 'api_created_at',
            'updated_at': 'api_updated_at',
            'artistid': 'api_artist_id',
            'tourid': 'api_tour_id'
        }, inplace=True)

        target_cols = ['api_show_id', 'show_year', 'show_month', 'show_day', 'show_date', 'permalink', 'exclude_from_stats', 'api_venue_id', 'setlist_notes', 'venue_name', 'venue_city', 'venue_state', 'venue_country', 'api_artist_id', 'artist_name', 'api_tour_id', 'tour_name', 'api_created_at', 'api_updated_at']
        for col in target_cols:
            if col not in shows_df.columns:
                shows_df[col] = None
        final_shows_df = shows_df[target_cols].copy()

        final_shows_df['api_artist_id'] = pd.to_numeric(final_shows_df['api_artist_id'], errors='coerce').astype('Int64')
        final_shows_df['api_tour_id'] = pd.to_numeric(final_shows_df['api_tour_id'], errors='coerce').astype('Int64')

        upsert_dataframe("phish_shows_raw", final_shows_df, conflict_columns=["api_show_id"])
        logging.info(f"Upserted {len(final_shows_df)} shows into phish_shows_raw.")

        # Extract and load venues
        venues_data = collector.collect_venues(shows_data)
        if venues_data:
            venues_df = pd.DataFrame(venues_data)
            venues_df.drop_duplicates(subset=['api_venue_id'], inplace=True)
            upsert_dataframe("phish_venues_raw", venues_df, conflict_columns=["api_venue_id"])
            logging.info(f"Upserted {len(venues_df)} venues into phish_venues_raw.")

    # --- Setlists ---
    logging.info("--- Collecting Setlists ---")
    setlists_data = collector.collect_setlists()
    if setlists_data:
        setlists_df = pd.DataFrame(setlists_data)
        setlists_df.drop_duplicates(subset=['uniqueid'], inplace=True)
        setlists_df.rename(columns={
            'uniqueid': 'api_unique_id',
            'showid': 'api_show_id',
            'songid': 'api_song_id',
            'set': 'set_number',
            'isjamchart': 'is_jam_chart',
            'tracktime': 'track_time'
        }, inplace=True)

        target_cols = ['api_unique_id', 'api_show_id', 'show_date', 'permalink', 'api_song_id', 'song_name', 'set_number', 'position', 'transition', 'is_reprise', 'is_jam', 'is_jam_chart', 'track_time', 'gap', 'is_original', 'footnote']
        for col in target_cols:
            if col not in setlists_df.columns:
                setlists_df[col] = None
        final_setlists_df = setlists_df[target_cols].copy()

        upsert_dataframe("phish_setlists_raw", final_setlists_df, conflict_columns=["api_unique_id"])
        logging.info(f"Upserted {len(final_setlists_df)} setlist entries into phish_setlists_raw.")

    logging.info("Phish data collection pipeline finished.")

if __name__ == "__main__":
    main()