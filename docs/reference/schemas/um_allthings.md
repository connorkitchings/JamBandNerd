# Umphrey's McGee API Data Schema

This document captures the structure of the Umphrey's McGee ingestion outputs as fetched from
the official [allthings.umphreys.com](https://allthings.umphreys.com) JSON API (v2).
The pipeline transitioned to this strict API-driven model on 2026-04-27 to improve
reliability and support future show ingestion.

## 1. Songs (`um_songs_raw`)

Collected via `/api/v2/songs.json`.

| Column              | Type    | Description                                     |
| ------------------- | ------- | ----------------------------------------------- |
| `song_id`           | bigint  | API song identifier (Primary Key)               |
| `song_name`         | string  | Primary song title                              |
| `song_slug`         | string  | API song slug                                   |
| `original_artist`   | string  | Original artist attribution (nullable)          |
| `is_original`       | bool    | True if the song is an Umphrey's McGee original |
| `api_created_at`    | datetime | API creation timestamp                         |
| `api_updated_at`    | datetime | API update timestamp                           |
| `source_hash`       | string  | Deterministic hash of the raw record payload    |

## 2. Venues (`um_venues_raw`)

Collected via `/api/v2/venues.json`.

| Column          | Type   | Description                                         |
| --------------- | ------ | --------------------------------------------------- |
| `venue_id`      | bigint | API venue identifier (Primary Key)                  |
| `venue_name`    | string | Venue name                                          |
| `venue_slug`    | string | API venue slug                                      |
| `venue_city`    | string | City                                                |
| `venue_state`   | string | State/province abbreviation                         |
| `venue_country` | string | Country                                             |
| `venue_zip`     | string | Postal/ZIP code                                     |
| `capacity`      | int    | Venue capacity when provided by the API             |
| `source_hash`   | string | Deterministic hash of the raw record payload        |

## 3. Shows (`um_shows_raw`)

Collected via the `/api/v2/shows/` endpoint.

| Column        | Type   | Description                                         |
| ------------- | ------ | --------------------------------------------------- |
| `show_id`     | bigint | API show identifier (Primary Key)                   |
| `source_url`  | string | Canonical show URL on allthingsum (unique key)      |
| `show_date`   | date   | Performance date (YYYY-MM-DD)                       |
| `venue_name`  | string | Venue name                                          |
| `venue_city`  | string | City                                                |
| `venue_state` | string | State/province                                      |
| `venue_country` | string | Country                                          |
| `show_notes`  | string | Optional show notes                                 |
| `show_year`   | int    | Extracted show year                                 |
| `show_month`  | int    | Extracted show month                                |
| `show_day`    | int    | Extracted show day                                  |
| `tour_name`   | string | Official tour name (if part of a tour)              |
| `source_hash` | string | Deterministic hash of the raw record payload        |

## 4. Setlists (`um_setlists_raw`)

Collected via the `/api/v2/setlists/` endpoint.

| Column            | Type    | Description                                                |
| ----------------- | ------- | ---------------------------------------------------------- |
| `id`              | bigint  | Internal sequential ID (Primary Key)                       |
| `show_id`         | bigint  | Foreign key to `um_shows_raw.show_id`                      |
| `song_id`         | bigint  | API song identifier                                        |
| `song_name`       | string  | Track title                                                |
| `set_label`       | string  | Normalized set label (`Set 1`, `Encore`, etc.)             |
| `set_sequence`    | int     | Order of the set within the show                           |
| `song_position`   | int     | Song index within the set (calculated)                     |
| `show_position`   | int     | Song index within the entire show (from API)               |
| `transition`      | string  | Raw transition symbol from API (e.g., `->`, `,`)           |
| `is_segue`        | bool    | True when the transition indicates a segue (`>`)           |
| `encore`          | bool    | True for encore sets                                       |
| `footnote_text`   | string  | Resolved footnote text                                     |
| `source_hash`     | string  | Deterministic hash of the raw record payload               |
