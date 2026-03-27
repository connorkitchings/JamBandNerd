# Predictions and Accuracy Schema

This document defines the current storage contract for predictions and
evaluation data.

## Current Canonical Tables

Prediction tables:

- `predictions_notebook`
- `predictions_ckplus`
- `predictions_deal` (backend-registered; may be hidden from website surfaces)
- `prediction_songs` (derived per-song projection)
- `historical_prediction_runs` (canonical scored backtest snapshots)

Accuracy tables:

- `accuracy_per_show`
- `notebook_accuracy`
- `accuracy_ckplus`
- `accuracy_deal` (experimental)

Model metadata for table/version/serializer mapping is registered in
`src/jambandnerd/models/registry.py`. Scripts should derive model behavior from
that registry rather than hardcoded slug lists.

## Current Prediction Storage

JamBandNerd currently stores one canonical row per prediction run context in
each `predictions_{model}` table and derives a shared per-song projection from
those rows.

Canonical columns:

- `band`
- `reference_date`
- `model_version`
- `top_k`
- `predictions`
- `predicted_at`

Uniqueness:

- `(band, reference_date, model_version)`

The `predictions` column is a JSON array ordered by rank. The payload shape is
model-specific.

## Derived Per-Song Projection

`prediction_songs` stores one row per predicted song for the canonical
prediction run.

Canonical columns:

- `band`
- `model_slug`
- `model_version`
- `reference_date`
- `predicted_at`
- `rank`
- `song_name`
- `top_k`
- `prediction_payload`

Uniqueness:

- `(band, model_version, reference_date, rank)`

`prediction_payload` preserves the exact model-specific JSON object emitted for
that ranked song.

### Notebook payload fields

Current payload entries contain:

- `rank`
- `song_name`
- `plays_past_year`
- `current_gap`
- `last_played_date`

### CK+ payload fields

Current payload entries contain:

- `rank`
- `song_name`
- `times_played`
- `current_gap`
- `avg_gap`
- `gap_ratio`
- `gap_z_score`
- `ckplus_score`
- `LTP`

## Per-Show Accuracy Storage

`accuracy_per_show` stores one row per evaluated completed show and model
version.

Canonical columns include:

- `band`
- `model_version`
- `show_id`
- `show_date`
- `prediction_run_id`
- `actual_song_count`
- `evaluated_at`
- `k10_*`, `k25_*`, `k50_*` metric families

Uniqueness:

- `(band, model_version, show_id)`

This is the canonical evaluation source for historical performance analysis.
For new backtest rows, `prediction_run_id` links each evaluation row to the
exact stored ranked board that produced it.

## Historical Scored Run Storage

`historical_prediction_runs` stores one canonical row per scored historical
prediction context.

Canonical columns include:

- `band`
- `model_slug`
- `model_version`
- `run_type`
- `reference_date`
- `target_show_id`
- `target_show_date`
- `generated_at`
- `actual_songs`
- `actual_song_count`
- `top_k`
- `predictions`

Uniqueness:

- `(band, model_slug, model_version, reference_date, target_show_id)`

This table is the canonical lineage store for historical backtests. It preserves
the exact ranked board that was scored without overloading the live
`predictions_{model}` tables or `prediction_songs`.

## Aggregate Accuracy Storage

Aggregate tables are derived from `accuracy_per_show`, not by rerunning
predictions.

Current aggregate tables:

- `notebook_accuracy`
- `accuracy_ckplus`

Canonical fields include:

- `band`
- `model_version`
- `window_start`
- `window_end`
- `num_shows`
- `evaluated_at`
- summary metrics for K=10, 25, and 50

## Versioning

The current repo uses explicit model version strings such as:

- `notebook_v1`
- `ckplus_v1`
- `deal_v2`

Changing output semantics, feature logic, or scoring behavior should produce a
new `model_version`.

## Current Decision and Deferred Option

### Active design

The active architecture is hybrid:

- canonical per-run JSON row in `predictions_{model}`
- derived per-song rows in `prediction_songs`

Reasons:

- simple canonical write path from the current pipeline
- stable upsert semantics at the run level
- SQL-friendly song-level reads without replacing the existing contract

### Deferred alternative

A future row-per-song-only prediction schema is still a valid option if
JamBandNerd eventually wants to make the projection table itself the canonical
write boundary.

That alternative is not the current system and should not be documented as if
it already exists.

## Related Documents

- [Data Strategy](data_strategy.md)
- [Database](database.md)
- [Unified Table Schemas](../schemas/unified_tables.md)
