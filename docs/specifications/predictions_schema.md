# Predictions and Accuracy Schema

This document defines the storage schemas for predictions and accuracy tracking.

## Table Names (Unified by Model)

- Predictions: `predictions_{model_slug}`
- Accuracy: `accuracy_{model_slug}`

Examples: `predictions_notebook`, `accuracy_notebook`.

## Predictions Table (current implementation -> band/model-specific)

Granularity: one row per predicted song candidate for a given show and context, with rank and probability.

Columns:

- `id` (serial) - Unique identifier for the row.
- `band` (text) — e.g., `goose`, `phish`.
- `model_slug` (text) — e.g., `notebook`, `ckplus`.
- `model_version` (text) — semantic or date-based version string.
- `run_id` (uuid) — identifier for the prediction run.
- `generated_at` (timestamptz) — when the prediction was created.
- `show_id` (bigint)
- `show_date` (date)
- `context` (jsonb, nullable) — optional, e.g., `{ "set_index": 1 }`.
- `predicted_song_id` (bigint, nullable) — if available from standardized songs.
- `predicted_song_name` (text)
- `rank` (integer) — 1 is highest.
- `probability` (double precision) — 0.0–1.0.
- `explanations` (jsonb, nullable) — optional feature contributions/notes.

Indexes/Constraints:

- Primary key: `id`
- Indexes: `(band, model_slug, show_id)`, `(run_id)`

## Accuracy Table (per-show) — planned

Granularity: accuracy metrics per show.

Columns:

- `id` (serial) - Unique identifier for the row.
- `band` (text)
- `model_slug` (text)
- `model_version` (text)
- `run_id` (uuid) — correlates with the prediction run.
- `evaluated_at` (timestamptz)
- `show_id` (bigint)
- `show_date` (date)
- `top_1` (boolean) — whether the correct next song was rank 1.
- `top_3` (boolean)
- `top_5` (boolean)
- `top_10` (boolean)
- `top_25` (boolean)
- `top_50` (boolean)
- `notes` (text, nullable)

Indexes/Constraints:

- Primary key: `id`
- Unique constraint: `(band, show_id, model_slug, model_version, run_id)`

## Model Slug

- Definition: short, lowercase identifier used in table names and rows (e.g., `notebook`, `ckplus`).
- The slug appears in both the table name and the data to simplify queries and lineage.

## Versioning

- `model_version` should reflect either semantic versioning (e.g., `1.0.0`) or a date tag (e.g., `2025-08-17`).
- Changing features, parameters, or training data requires a new version.

## Run Identity

- Each prediction execution emits a `run_id` and shared timestamps so predictions and accuracy rows
  can be correlated.

## Data Quality & Validation

- Before insert, validate types and required columns.
- Probabilities must be 0.0–1.0; ranks must be positive integers.
- Ensure exactly one ground-truth label per show when evaluating.
