# elgoose.net API Raw Data Schema

This document outlines the complete, raw schema of the data returned from the elgoose.net API.
This represents the data *before* any transformation or filtering is applied by the `loaders.py`
script.

## API Response Structure

All API endpoints return a JSON object with the following structure:

```json
{
  "error": false,
  "error_message": null,
  "data": [...] // Array of records
}
```

The schemas below describe the structure of individual records within the `data` array.

## 1. Songs (`/api/v2/songs.json`)

| Column Name       | Data Type | Description                                      |
| ----------------- | --------- | ------------------------------------------------ |
| `id`              | int64     | Unique numerical identifier for the song.        |
| `name`            | object    | The official name of the song.                   |
| `slug`            | object    | A URL-friendly version of the song name.         |
| `isoriginal`      | int64     | A flag (0 or 1) indicating if the song is a Goose original. |
| `original_artist` | object    | The original artist of the song, if a cover.     |
| `created_at`      | object    | The timestamp when the record was created (string format). |
| `updated_at`      | object    | The timestamp when the record was last updated (string format). |

## 2. Shows (`/api/v2/shows.json`)

| Column Name       | Data Type | Description                                      |
| ----------------- | --------- | ------------------------------------------------ |
| `show_id`         | int64     | Unique numerical identifier for the show.        |
| `showdate`        | object    | The full date of the show (YYYY-MM-DD).          |
| `permalink`       | object    | A URL to the show's page on elgoose.net.         |
| `artist_id`       | int64     | The unique identifier for the artist.            |
| `artist`          | object    | The name of the artist.                          |
| `showtitle`       | object    | A title for the show, if any.                    |
| `venue_id`        | int64     | The unique identifier for the venue.             |
| `venuename`       | object    | The name of the venue.                           |
| `location`        | object    | A combined location string.                      |
| `city`            | object    | The city where the venue is located.             |
| `state`           | object    | The state where the venue is located.            |
| `country`         | object    | The country where the venue is located.          |
| `tour_id`         | int64     | The unique identifier for the tour.              |
| `tourname`        | object    | The name of the tour.                            |
| `showorder`       | int64     | The order of the show within a tour or year.     |
| `show_year`       | int64     | The year of the show.                            |
| `show_day`        | int64     | The day of the month of the show.                |
| `show_dayname`    | object    | The name of the day of the week.                 |
| `show_month`      | int64     | The month of the show (1-12).                    |
| `show_monthname`  | object    | The name of the month.                           |
| `updated_at`      | object    | The timestamp when the record was last updated (string format). |
| `created_at`      | object    | The timestamp when the record was created (string format). |

## 3. Setlists (`/api/v1/setlists.json`)

| Column Name       | Data Type | Description                                      |
| ----------------- | --------- | ------------------------------------------------ |
| `uniqueid`        | object    | A unique identifier for this specific setlist entry. |
| `show_id`         | int64     | Foreign key linking to the `shows` data.         |
| `showdate`        | object    | The full date of the show (YYYY-MM-DD).          |
| `showtitle`       | object    | A title for the show, if any.                    |
| `artist`          | object    | The name of the artist.                          |
| `song_id`         | int64     | Foreign key linking to the `songs` data.         |
| `songname`        | object    | The name of the song.                            |
| `artist_id`       | float64   | The unique identifier for the artist.            |
| `permalink`       | object    | A URL to the show's page on elgoose.net.         |
| `settype`         | object    | The type of set (e.g., 'Set', 'Encore').         |
| `setnumber`       | object    | The set number (e.g., '1', '2', 'E').            |
| `position`        | int64     | The position of the song within the set.         |
| `tracktime`       | object    | The duration of the track (MM:SS).               |
| `transition_id`   | int64     | A numerical code for the transition type.        |
| `transition`      | object    | The transition marker (e.g., '>', '->').         |
| `footnote`        | object    | Any footnote associated with this song performance. |
| `isjamchart`      | int64     | A flag (0 or 1) indicating if the song is on a jam chart. |
| `jamchart_notes`  | object    | Notes associated with the jam chart entry.       |
| `venue_id`        | float64   | The unique identifier for the venue.             |
| `shownotes`       | object    | Any notes associated with the entire show.       |
| `showyear`        | float64   | The year of the show.                            |
| `showorder`       | float64   | The order of the show within a tour or year.     |
| `opener`          | object    | The opening band, if any.                        |
| `tour_id`         | float64   | The unique identifier for the tour.              |
| `tourname`        | object    | The name of the tour.                            |
| `soundcheck`      | object    | The song(s) played during soundcheck.            |
| `isverified`      | float64   | A flag indicating if the setlist is verified.    |
| `slug`            | object    | A URL-friendly version of the song name.         |
| `isoriginal`      | int64     | A flag (0 or 1) indicating if the song is a Goose original. |
| `original_artist` | object    | The original artist of the song, if a cover.     |
| `venuename`       | object    | The name of the venue.                           |
| `city`            | object    | The city where the venue is located.             |
| `state`           | object    | The state where the venue is located.            |
| `country`         | object    | The country where the venue is located.          |
| `isreprise`       | int64     | A flag (0 or 1) indicating if the song is a reprise. |
| `isjam`           | int64     | A flag (0 or 1) indicating if the song contained a jam. |
| `css_class`       | object    | A CSS class associated with the entry, if any.   |
| `isrecommended`   | float64   | A flag indicating if the show is recommended.    |

## 4. Venues (`/api/v2/venues.json`)

| Column Name | Data Type | Description |
| ----------- | --------- | ----------- |
| `venue_id`  | int64     | Unique numerical identifier for the venue. |
| `venuename` | object    | The name of the venue. |
| `city`      | object    | The city of the venue. |
| `state`     | object    | The state or region of the venue. |
| `country`   | object    | The country of the venue. |
| `zip`       | object    | Postal/ZIP code of the venue. |
| `capacity`  | int64     | Stated capacity of the venue (0 if unknown). |
| `slug`      | object    | URL-friendly identifier for the venue. |

Notes:

- Endpoint returns wrapper `{ error, error_message, data }` identical to other endpoints.
- Observed count ~550 venues. Keys consistent across v1 and v2 in testing.