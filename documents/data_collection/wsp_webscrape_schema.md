# Widespread Panic Web Scrape Data Schema

This document outlines the schema of the pandas DataFrames produced by the web scraping scripts in
`src/jambandnerd/data_collection/wsp/`. This represents the final structure of the data after it has
been scraped from everydaycompanion.com and processed by the various `scrape_*.py` modules.

## 1. Songs (`scrape_wsp_songs.py`)

This DataFrame contains the complete Widespread Panic song catalog.

| Column Name    | Data Type      | Description                                                 |
| -------------- | -------------- | ----------------------------------------------------------- |
| `code`         | object (string)| Unique song code from everydaycompanion.com. |
| `song`         | object (string)| The official name of the song.                              |
| `first_played` | datetime64[ns] | The date the song was first played.                         |
| `last_played`  | datetime64[ns] | The date the song was last played.                          |
| `times_played` | int64          | The total number of times the song has been played.         |
| `aka`          | object (string)| Other names the song is known by.                           |

## 2. Shows (`scrape_wsp_shows.py`)

This DataFrame contains information for every show played.

| Column Name            | Data Type      | Description                                            |
| ---------------------- | -------------- | ------------------------------------------------------ |
| `date`                 | datetime64[ns] | The specific date of the show.                         |
| `year`                 | object (string)| The year the show took place.                          |
| `month`                | object (string)| The month the show took place (1-12).                  |
| `day`                  | object (string)| The day of the month the show took place.              |
| `weekday`              | object (string)| The day of the week the show took place.               |
| `date_ec`              | object (string)| Date from everydaycompanion.com (MM/DD/YY).            |
| `venue`                | object (string)| The name of the venue.                                 |
| `city`                 | object (string)| The city where the show was held.                      |
| `state`                | object (string)| The state where the show was held.                     |
| `show_index_overall`   | int64          | Unique index for every show.                           |
| `show_index_withinyear`| int64          | Index of show within its year.                         |
| `run_index`            | int64          | Index for consecutive shows at the same venue.         |
| `venue_full`           | object (string)| Full location string (venue, city, state).             |
| `link`                 | object (string)| URL to setlist page, used as a primary key.            |

## 3. Setlists (`load_setlist_data.py`)

This DataFrame contains the setlist for each show, with one row per song played.

| Column Name        | Data Type      | Description                                                |
| ------------------ | -------------- | ---------------------------------------------------------- |
| `song_name`        | object (string)| The name of the song played.                               |
| `set_name`         | object (string)| Set the song was in (e.g., '1', '2', 'E').                 |
| `song_index_set`   | int64          | The position of the song within the set.                   |
| `song_index_show`  | int64          | Song's position in the entire show.                        |
| `is_into`          | int64          | Flag (0/1) for a transition ('>') into next song.          |
| `song_note_detail` | object (string)| Notes for this specific performance.                       |
| `link`             | object (string)| URL of the show's setlist page, for linking.               |
