# Phish.net API Raw Data Schema

This document outlines the complete, raw schema of the data returned from the Phish.net API v5.
This represents the data *before* any transformation or filtering is applied by the `loaders.py`
script.

## 1. Songs (`/api/v5/songs.json`)

The songs endpoint returns a comprehensive list of all songs played by Phish.

| Column Name       | Data Type | Description                                      |
| ----------------- | --------- | ------------------------------------------------ |
| `songid`          | int64     | Unique numerical identifier for the song.        |
| `song`            | object    | The official name of the song.                   |
| `slug`            | object    | A URL-friendly version of the song name.         |
| `abbr`            | object    | A common abbreviation for the song.              |
| `artist`          | object    | The original artist of the song, if a cover.     |
| `debut`           | object    | The date of the song's first performance (YYYY-MM-DD). |
| `last_played`     | object    | The date of the song's most recent performance (YYYY-MM-DD). |
| `times_played`    | int64     | The total number of times the song has been played. |
| `last_permalink`  | object    | A URL to the setlist of the last performance.    |
| `debut_permalink` | object    | A URL to the setlist of the debut performance.   |
| `gap`             | int64     | The number of shows since the song was last played. |

## 2. Shows (`/api/v5/shows/artist/phish.json`)

The shows endpoint provides details for every Phish performance.

| Column Name          | Data Type | Description                                             |
| -------------------- | --------- | ------------------------------------------------------- |
| `showid`             | int64     | Unique numerical identifier for the show.               |
| `showyear`           | object    | The year of the show.                                   |
| `showmonth`          | int64     | The month of the show (1-12).                           |
| `showday`            | int64     | The day of the show.                                    |
| `showdate`           | object    | The full date of the show (YYYY-MM-DD).                 |
| `permalink`          | object    | A URL to the show's page on Phish.net.                  |
| `exclude_from_stats` | int64     | A flag (0 or 1) to exclude the show from statistics.    |
| `venueid`            | int64     | The unique identifier for the venue.                    |
| `setlist_notes`      | object    | Any notes associated with the setlist.                  |
| `venue`              | object    | The name of the venue.                                  |
| `city`               | object    | The city where the venue is located.                    |
| `state`              | object    | The state where the venue is located.                   |
| `country`            | object    | The country where the venue is located.                 |
| `artistid`           | int64     | The unique identifier for the artist (1 for Phish).     |
| `artist_name`        | object    | The name of the artist.                                 |
| `tourid`             | float64   | The unique identifier for the tour.                     |
| `tour_name`          | object    | The name of the tour.                                   |
| `created_at`         | object    | The timestamp when the record was created.              |
| `updated_at`         | object    | The timestamp when the record was last updated.         |

## 3. Setlists (`/api/v5/setlists/artistid/1.json`)

The setlists endpoint returns every song from every show, providing a flattened, detailed record of
each performance.

| Column Name            | Data Type | Description                                             |
| ---------------------- | --------- | ------------------------------------------------------- |
| `showid`               | int64     | Foreign key linking to the `shows` data.                |
| `showdate`             | object    | The full date of the show (YYYY-MM-DD).                 |
| `permalink`            | object    | A URL to the show's page on Phish.net.                  |
| `showyear`             | object    | The year of the show.                                   |
| `uniqueid`             | int64     | A unique identifier for this specific setlist entry.    |
| `meta`                 | object    | Additional metadata, often empty.                       |
| `reviews`              | int64     | The number of reviews for the show.                     |
| `exclude`              | int64     | A flag (0 or 1) to exclude the song from statistics.    |
| `setlistnotes`         | object    | Any notes associated with the setlist for that show.    |
| `soundcheck`           | object    | The song(s) played during soundcheck.                   |
| `songid`               | int64     | Foreign key linking to the `songs` data.                |
| `position`             | int64     | The position of the song within the set.                |
| `transition`           | int64     | A numerical code for the transition type.               |
| `footnote`             | object    | Any footnote associated with this specific song performance. |
| `set`                  | object    | The set number (e.g., '1', '2', 'E').                   |
| `isjam`                | int64     | A flag (0 or 1) indicating if the song contained a jam. |
| `isreprise`            | int64     | A flag (0 or 1) indicating if the song is a reprise.    |
| `isjamchart`           | int64     | A flag (0 or 1) indicating if the song is on a jam chart. |
| `jamchart_description` | object    | A description of the jam chart, if applicable.          |
| `tracktime`            | object    | The duration of the track (MM:SS).                      |
| `gap`                  | int64     | The number of shows since the song was last played.     |
| `tourid`               | int64     | The unique identifier for the tour.                     |
| `tourname`             | object    | The name of the tour.                                   |
| `tourwhen`             | object    | The year or season of the tour.                         |
| `song`                 | object    | The name of the song.                                   |
| `nickname`             | object    | A common nickname for the song.                         |
| `slug`                 | object    | A URL-friendly version of the song name.         |
| `is_original`          | int64     | A flag (0 or 1) indicating if the song is a Phish original. |
| `venueid`              | int64     | The unique identifier for the venue.                    |
| `venue`                | object    | The name of the venue.                                  |
| `city`                 | object    | The city where the venue is located.                    |
| `state`                | object    | The state where the venue is located.                   |
| `country`              | object    | The country where the venue is located.                 |
| `trans_mark`           | object    | The transition marker (e.g., '>', '->').                |
| `artistid`             | int64     | The unique identifier for the artist (1 for Phish).     |
| `artist_slug`          | object    | The URL-friendly slug for the artist.                   |
| `artist_name`          | object    | The name of the artist.                                 |
