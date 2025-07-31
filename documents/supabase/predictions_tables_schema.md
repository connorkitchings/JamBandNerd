# Model-Specific Prediction Table Schemas

This document defines the standardized, model-specific schemas for storing
predictions in the Supabase database. This approach uses a separate table for each
prediction model (e.g., `predictions_ckplus`, `predictions_notebook`) to ensure a
clean, normalized structure.

## Rationale

A model-specific table approach was chosen over a single unified table for the
following reasons:

- **Schema Purity:** Each table's schema perfectly matches the output of its
  corresponding model. This avoids `NULL` values for features that don't apply,
  leading to a cleaner, more normalized design.
- **Model Isolation:** Changes to one model's output only require migrating a
  single, dedicated table. Adding a new model is a clean operation involving the
  creation of a new table.
- **Clear Separation of Concerns:** This design aligns well with the principle of
  separating different data domains, making the database structure easier to
  understand and maintain.

## Daily Prediction Management

To prevent duplicate entries from daily pipeline runs, each table uses a composite
unique constraint on `(prediction_date, band, song_id)`. The data export logic
will use Supabase's `upsert` functionality with this constraint. This ensures that
for any given day, band, and song, there is only one prediction record. If the
pipeline is run again for the same day, the existing record will be updated
instead of a new one being inserted.

---

## CK+ Model Schema

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

```sql
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
```

---

## Notebook Model Schema

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

```sql
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
```
