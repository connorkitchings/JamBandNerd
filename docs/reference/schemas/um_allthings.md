# Umphrey's McGee Web Scrape Data Schema

This document captures the structure of the Umphrey's McGee ingestion outputs as scraped from
[allthings.umphreys.com](https://allthings.umphreys.com). These definitions mirror the working schema
maintained alongside the canonical CSV snapshots in
`saved for later/data/um/collected/DATA_SCHEMA.md`.

## 1. Songs (`um_songs_raw`)

| Column              | Type    | Description                                     |
| ------------------- | ------- | ----------------------------------------------- |
| `song_name`         | string  | Primary song title                              |
| `original_artist`   | string  | Original artist attribution (nullable)          |
| `debut_date`        | date    | First known performance (YYYY-MM-DD)            |
| `last_played`       | date    | Most recent performance (YYYY-MM-DD)            |
| `times_played_live` | int     | Total performances counted by allthingsum       |
| `avg_show_gap`      | float   | Average number of shows between performances    |
| `source_hash`       | string  | Deterministic hash of the raw record payload    |

## 2. Venues (`um_venues_raw`)

| Column          | Type   | Description                                         |
| --------------- | ------ | --------------------------------------------------- |
| `id`            | int    | Auto-incremented primary key assigned by Supabase   |
| `venue_name`    | string | Venue name as displayed on allthingsum              |
| `venue_city`    | string | City                                                |
| `venue_state`   | string | State/province abbreviation                         |
| `venue_country` | string | Country                                             |
| `times_played`  | int    | Total performances at the venue                     |
| `last_played`   | date   | Most recent performance at the venue                |
| `source_hash`   | string | Deterministic hash of the raw record payload        |

## 3. Shows (`um_shows_raw`)

| Column        | Type   | Description                                         |
| ------------- | ------ | --------------------------------------------------- |
| `source_url`  | string | Canonical show URL on allthingsum (unique key)      |
| `show_date`   | date   | Performance date (YYYY-MM-DD)                       |
| `venue_name`  | string | Venue name                                          |
| `venue_city`  | string | City                                                |
| `venue_state` | string | State/province                                      |
| `venue_country` | string | Country                                          |
| `show_notes`  | string | Optional show notes scraped from the footer         |
| `show_year`   | int    | Extracted show year                                 |
| `show_month`  | int    | Extracted show month                                |
| `show_day`    | int    | Extracted show day                                  |
| `source_hash` | string | Deterministic hash of the raw record payload        |

Supabase assigns the integer `show_id` primary key on insert, which downstream collectors use when
scraping setlists.

## 4. Setlists (`um_setlists_raw`)

| Column            | Type    | Description                                                |
| ----------------- | ------- | ---------------------------------------------------------- |
| `show_id`         | int     | Foreign key to `um_shows_raw.show_id`                      |
| `source_url`      | string  | Show URL for traceability                                  |
| `show_date`       | date    | Show date for convenience                                 |
| `venue_name`      | string  | Venue name (denormalized for quick reference)              |
| `venue_city`      | string  | City (denormalized)                                       |
| `venue_state`     | string  | State/province (denormalized)                             |
| `venue_country`   | string  | Country (denormalized)                                    |
| `set_label`       | string  | Normalized set label (`1`, `2`, `E`, `E2`, `SC`, etc.)      |
| `set_sequence`    | int     | Order of the set within the show                           |
| `song_position`   | int     | Song index within the set                                  |
| `show_position`   | int     | Song index within the entire show                          |
| `song_name`       | string  | Track title                                                |
| `is_segue`        | bool    | True when the source contained a segue marker (`>`)        |
| `encore`          | bool    | True for encore sets                                       |
| `footnote_symbol` | string  | Footnote indicator `[n]` when present                      |
| `footnote_text`   | string  | Resolved footnote text                                     |
| `song_notes`      | string  | Alias of `footnote_text` for model compatibility           |
| `source_hash`     | string  | Deterministic hash of the raw record payload               |

These structures are intentionally aligned with the historical CSV exports under
`saved for later/data/um/collected/` so the new ingestion pipeline can act as a drop-in replacement
for earlier manual processes.
