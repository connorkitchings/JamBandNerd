# Predictions and Accuracy Schema

This document defines the current storage contract for predictions and
evaluation data.

## Current Canonical Tables

Prediction tables:

- `setlist_predictions` (canonical live next-show storage)
- `setlist_prediction_songs` (derived live per-song projection)
- `setlist_results` (canonical retained completed-show snapshots)

Accuracy tables:

- `setlist_accuracy`

Band metadata for active model version/serializer mapping is registered in
`src/jambandnerd/models/metadata.py` and exposed through
`src/jambandnerd/models/registry.py`. Scripts should derive model behavior from
that registry rather than hardcoded slug lists.

## Live Next-Show Storage

JamBandNerd stores active live predictions separately from completed-show
history. `setlist_predictions` contains one active run per
`(band, model_version, target_show_key)`, and the pipeline deletes
older live rows once the target is no longer the next known show.

Canonical columns:

- `band`
- `target_show_key`
- `target_show_date`
- `reference_date`
- `model_version`
- `top_k`
- `predictions`
- `generated_at`

Uniqueness:

- `(band, model_version, target_show_key)`

The `predictions` column is a JSON array ordered by rank. The payload shape is
band-model-specific.

`setlist_prediction_songs` is the live per-song projection consumed by the
website prediction board and realtime refresh logic. It is derived from
`setlist_predictions`.

## Retained Completed-Show Storage

`setlist_results` stores the exact ranked boards for the active
last-50 completed-show corpus per band model version. It is the replay source
of truth.
Rows outside the retained 50-show corpus are hard-deleted by the retained corpus
sync.

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

`setlist_accuracy` stores one row per retained evaluated completed show and
model version.

Canonical columns include:

- `band`
- `model_version`
- `show_id`
- `target_show_key`
- `show_date`
- `prediction_run_id`
- `actual_song_count`
- `evaluated_at`
- `p10`, `p25`, `p50`
- `recall_10`, `recall_25`, `recall_50`
- `weighted_precision_score`

Uniqueness:

- `(band, model_version, target_show_key)`

This is the only active evaluation source for historical performance analysis.
For retained rows, `prediction_run_id` links each evaluation row to the exact
stored ranked board that produced it.

## Historical Scored Run Storage

`historical_prediction_runs` remains a legacy lineage table for older rows.
New website-facing scored history is written to `setlist_results`.

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
`predictions` table or `prediction_songs`.

## Versioning

The active single-model path uses explicit per-band model version strings such as:

- `goose_baseline_v1`
- `phish_baseline_v1`
- `wsp_baseline_v1`

Changing output semantics, feature logic, or scoring behavior should produce a
new `model_version`.

## Current Decision and Deferred Option

### Active design

The active product architecture is split by intent:

- live next-show rows in `setlist_predictions` plus
  `setlist_prediction_songs`
- retained last-50 completed-show rows in `setlist_results` plus
  `setlist_accuracy`

Reasons:

- live prediction reads cannot fall back to completed-show history
- all model metrics share the same retained 50-show corpus
- replay rows carry exact stored boards and actual setlists

### Deferred alternative

The legacy `predictions`, `prediction_songs`, `historical_prediction_runs`, and
`accuracy_per_show` tables may remain temporarily for compatibility and
migration safety, but they are not the active website-facing source of truth.

That alternative is not the current system and should not be documented as if
it already exists.

## Related Documents

- [Data Strategy](data_strategy.md)
- [Database](database.md)
- [Unified Table Schemas](../schemas/unified_tables.md)
