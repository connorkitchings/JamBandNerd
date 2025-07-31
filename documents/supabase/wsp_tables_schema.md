# WSP Database Schema

This document defines the database schema for a Widespread Panic (WSP) concert tracking system with
three main tables.

## Table: `wsp_songs`

**Purpose**: Stores information about individual songs in WSP's repertoire.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `code` | TEXT | PRIMARY KEY | Unique identifier/code for each song |
| `song` | TEXT | | Song title/name |
| `first_played` | TEXT | | Date when the song was first performed (MM/DD/YYYY) |
| `last_played` | TEXT | | Date when the song was most recently performed (MM/DD/YYYY) |
| `times_played` | INTEGER | | Total number of times the song has been played |
| `aka` | TEXT | | Alternative names or aliases for the song |

**Permissions**: Full public access (SELECT, INSERT, UPDATE, DELETE)

## Table: `wsp_shows`

**Purpose**: Stores information about individual concert performances/shows.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `link` | TEXT | PRIMARY KEY | Unique identifier/URL link for the show |
| `date` | TEXT | | Full date of the show (MM/DD/YYYY) |
| `year` | TEXT | | Year component of the show date |
| `month` | TEXT | | Month component of the show date |
| `day` | TEXT | | Day component of the show date |
| `weekday` | TEXT | | Day of the week for the show |
| `date_ec` | TEXT | | Date in an alternative format (possibly East Coast format) |
| `venue` | TEXT | | Name of the venue where the show took place |
| `city` | TEXT | | City where the show took place |
| `state` | TEXT | | State/province where the show took place |
| `show_index_overall` | INTEGER | | Sequential number of this show in the band's entire history |
| `show_index_withinyear` | INTEGER | | Sequential number of this show within its year |
| `run_index` | INTEGER | | Index indicating show's position within a tour run |
| `venue_full` | TEXT | | Full venue name with additional details |

**Permissions**: Full public access (SELECT, INSERT, UPDATE, DELETE)

## Table: `wsp_setlists`

**Purpose**: Stores detailed setlist information for each song performed at each show.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PRIMARY KEY, AUTO-INCREMENT | Unique identifier for each setlist entry |
| `link` | TEXT | | References the show (foreign key to `wsp_shows.link`) |
| `song_name` | TEXT | | Name of the song performed |
| `set_name` | TEXT | | Which set the song was played in (e.g., "Set 1", "Encore") |
| `song_index_set` | INTEGER | | Position of the song within its set |
| `song_index_show` | INTEGER | | Position of the song within the entire show |
| `is_into` | BOOLEAN | | Whether this song transitions into another song |
| `song_note_detail` | TEXT | | Additional notes or details about the song performance |

**Unique Constraint**: `(link, song_index_show)` - Ensures no duplicate song positions within a show

**Permissions**: Full public access (SELECT, INSERT, UPDATE, DELETE)

## Relationships

- `wsp_setlists.link` relates to `wsp_shows.link` (many-to-one relationship)
- `wsp_setlists.song_name` could potentially relate to `wsp_songs.song` (though no formal foreign
  key is defined)

## Security Model

All tables use Row Level Security (RLS) with public access policies that allow:

- **SELECT**: Anyone can read data
- **INSERT**: Anyone can add new records
- **UPDATE**: Anyone can modify existing records
- **DELETE**: Anyone can remove records

## Usage Notes

This schema appears designed for tracking:

1. **Song catalog**: Complete list of songs with performance statistics
2. **Show details**: Comprehensive information about each concert
3. **Performance tracking**: Detailed setlists linking songs to specific shows and positions

The schema supports analysis of song frequency, venue history, tour patterns, and setlist evolution
over time.
