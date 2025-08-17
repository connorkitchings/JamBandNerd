# JamBandNerd Database Schema

This document provides a consolidated overview of all database tables used in the JamBandNerd
project, stored in Supabase.

---

## Prediction Model Tables

This section defines the standardized, model-specific schemas for storing predictions. This approach
uses a separate table for each prediction model (e.g., `predictions_ckplus`, `predictions_notebook`)
to ensure a clean, normalized structure.

### Rationale

A model-specific table approach was chosen over a single unified table for the following reasons:

- **Schema Purity:** Each table's schema perfectly matches the output of its corresponding model.
  This avoids `NULL` values for features that don't apply, leading to a cleaner, more normalized
  design.
- **Model Isolation:** Changes to one model's output only require migrating a single, dedicated
  table. Adding a new model is a clean operation involving the creation of a new table.
- **Clear Separation of Concerns:** This design aligns well with the principle of separating
  different data domains, making the database structure easier to understand and maintain.

### Daily Prediction Management

To prevent duplicate entries from daily pipeline runs, each table uses a composite unique constraint
on `(prediction_date, band, song_id)`. The data export logic will use Supabase's `upsert` functionality
with this constraint. This ensures that for any given day, band, and song, there is only one prediction
record. If the pipeline is run again for the same day, the existing record will be updated instead of a
new one being inserted.

---

### CK+ Model Schema

**Table Name:** `predictions_ckplus`

| Column Name          | Data Type     | Constraints     | Description      |
| -------------------- | ------------- | ---------------- | ---------------- |
| `id`                 | `BIGINT`      | `PK, IDENTITY`   | Auto-incrementing unique ID            |
| `prediction_date`    | `TEXT`        | `NOT NULL`       | Prediction date (MM/DD/YYYY)           |
| `band`               | `TEXT`        | `NOT NULL`       | Band for which the prediction is made  |
| `song_name`          | `TEXT`        | `NOT NULL`       | Name of the song                       |
| `last_played_date`   | `TEXT`        |                    | Last played date (MM/DD/YYYY)        |
| `times_played_total` | `INTEGER`     |                    | Total times the song has been played |
| `current_gap`        | `INTEGER`     |                    | Shows since the song was last played |
| `avg_gap`            | `FLOAT`       |                    | Historical average show gap          |
| `gap_ratio`          | `FLOAT`       |                    | Ratio of current gap to average gap  |
| `gap_z_score`        | `FLOAT`       |                    | The z-score of the gap               |
| `ckplus_score`       | `FLOAT`       |                    | Final calculated score from CK+ model|
| `created_at`| `TIMESTAMPTZ` | `DEFAULT now() NOT NULL` | Timestamp of when the record was created|

**SQL Implementation:**

'''sql
-- CK+ Model Table
CREATE TABLE predictions_ckplus (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    prediction_date TEXT NOT NULL,
    band TEXT NOT NULL,
    song_name TEXT NOT NULL,
    last_played_date TEXT,
    times_played_total INTEGER,
    current_gap INTEGER,
    avg_gap FLOAT,
    gap_ratio FLOAT,
    gap_z_score FLOAT,
    ckplus_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT unique_ckplus_prediction UNIQUE (prediction_date, band, song_name)
);

-- Add RLS policies for CK+ table
ALTER TABLE predictions_ckplus ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public access" ON predictions_ckplus FOR ALL USING (true) WITH CHECK (true);
'''

---

### Notebook Model Schema

**Table Name:** `predictions_notebook`

| Column Name              | Data Type     | Constraints              | Description                |
| ------------------------ | ------------- | ------------------------ | -------------------------- |
| `id`                     | `BIGINT`      | `PK, IDENTITY`           | Auto-incrementing unique ID|
| `prediction_date`       | `TEXT`        | `NOT NULL`               | Prediction date (MM/DD/YYYY)|
| `band`         | `TEXT`        | `NOT NULL`               | Band for which the prediction is made|
| `song_name`         | `TEXT`        | `NOT NULL`               | Name of the song for readability|
| `last_played_date`       | `TEXT`        |                        | Last played date (MM/DD/YYYY)|
| `times_played_last_year` | `INTEGER`     |                    | Times played in the last 365 days|
| `current_gap`            | `INTEGER`     |                 | Shows since the song was last played|
| `avg_gap`                | `FLOAT`       |                        | Historical average show gap|
| `median_gap`             | `FLOAT`       |                        | Historical median show gap|
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now() NOT NULL`| Timestamp of when the record was created|

**SQL Implementation:**

'''sql
-- Notebook Model Table
CREATE TABLE predictions_notebook (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    prediction_date TEXT NOT NULL,
    band TEXT NOT NULL,
    song_name TEXT NOT NULL,
    last_played_date TEXT,
    times_played_last_year INTEGER,
    current_gap INTEGER,
    avg_gap FLOAT,
    median_gap FLOAT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT unique_notebook_prediction UNIQUE (prediction_date, band, song_name)
);

-- Add RLS policies for Notebook table
ALTER TABLE predictions_notebook ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public access" ON predictions_notebook FOR ALL USING (true) WITH CHECK (true);
'''

---

## Widespread Panic (WSP) Tables

This section defines the database schema for the Widespread Panic (WSP) concert tracking system.

### Table: `wsp_songs`

**Purpose**: Stores information about individual songs in WSP's repertoire.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `code` | TEXT | PRIMARY KEY | Unique identifier/code for each song |
| `song` | TEXT | | Song title/name |
| `first_played` | TEXT | | Date when the song was first performed (MM/DD/YYYY) |
| `last_played` | TEXT | | Date when the song was most recently performed (MM/DD/YYYY) |
| `times_played` | INTEGER | | Total number of times the song has been played |
| `aka` | TEXT | | Alternative names or aliases for the song |

### Table: `wsp_shows`

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

### Table: `wsp_setlists`

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

---

## Pipeline Metadata Table

This section defines the enhanced schema for the `pipeline_metadata` table, which tracks pipeline
execution metadata and supports database-based caching for data collection pipelines.

### Purpose

The `pipeline_metadata` table serves two primary purposes:

1. **Pipeline Execution Tracking**: Records when each band's data collection pipeline was last executed
2. **Database-Based Caching**: Enables intelligent caching decisions for scraping-based pipelines
   (particularly WSP) by storing last scrape timestamps and metadata

### Schema

**Table Name:** `pipeline_metadata`

| Column Name          | Data Type     | Constraints              | Description                           |
| -------------------- | ------------- | ------------------------ | ------------------------------------- |
| `id`                 | `BIGINT`      | `PK, IDENTITY`           | Auto-incrementing unique ID           |
| `pipeline_name`      | `TEXT`        | `NOT NULL, UNIQUE`       | Name of the pipeline (e.g., 'wsp', 'phish', 'goose') |
| `last_updated`       | `TIMESTAMPTZ` | `NOT NULL`               | Timestamp of last pipeline execution  |
| `metadata`           | `JSONB`       |                          | Additional metadata (cache info, counts, etc.) |
| `created_at`         | `TIMESTAMPTZ` | `DEFAULT now() NOT NULL` | Timestamp of when the record was created |

### Metadata JSON Structure

The `metadata` JSONB column stores pipeline-specific information:

#### For WSP Pipeline

'''json
{
  "cache": {
    "shows": {
      "last_scraped": "2025-08-06T12:30:00Z",
      "count": 3247,
      "scrape_type": "full"
    },
    "songs": {
      "last_scraped": "2025-08-06T12:30:00Z",
      "count": 698,
      "scrape_type": "full"
    }
  },
  "performance": {
    "execution_time_seconds": 532.99,
    "setlist_count": 89013
  }
}
'''

#### For API-Based Pipelines (Phish, Goose)

'''json
{
  "performance": {
    "execution_time_seconds": 45.2,
    "records_processed": {
      "songs": 956,
      "shows": 2194,
      "setlists": 38948
    }
  }
}
'''

### SQL Implementation

'''sql
-- Enhanced Pipeline Metadata Table
CREATE TABLE IF NOT EXISTS pipeline_metadata (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    pipeline_name TEXT NOT NULL UNIQUE,
    last_updated TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Add RLS policies
ALTER TABLE pipeline_metadata ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public access" ON pipeline_metadata FOR ALL USING (true) WITH CHECK (true);

-- Create index on pipeline_name for fast lookups
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_name ON pipeline_metadata(pipeline_name);

-- Create index on JSONB metadata for cache queries
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_cache ON pipeline_metadata USING GIN ((metadata->'cache'));
'''
