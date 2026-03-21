# Database Utilities and Storage Contract

This page documents the current Supabase-facing utilities and how JamBandNerd
uses the database in the active pipeline.

## Environment

Required environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Database access is validated lazily when the first Supabase interaction occurs.

## Storage Shape

JamBandNerd uses Supabase for raw ingestion, predictions, and evaluation.

### Raw tables

Canonical raw table families:

- `{band}_shows_raw`
- `{band}_setlists_raw`
- `{band}_songs_raw`

Allowed supporting raw tables:

- `{band}_venues_raw`
- source-specific helpers such as `um_upcoming_shows`

Raw tables remain source-faithful. Shared code normalizes them after read, not
by writing derived tables back to Supabase.

### Prediction tables

- `predictions_notebook`
- `predictions_ckplus`
- `prediction_songs` (derived)

`predictions_notebook` and `predictions_ckplus` store one canonical row per
`(band, reference_date, model_version)` with a JSON predictions payload.
`prediction_songs` stores one derived row per predicted song.

### Accuracy tables

- `accuracy_per_show`
- `notebook_accuracy`
- `accuracy_ckplus`

`accuracy_per_show` is the canonical granular evaluation store. Aggregate
accuracy tables are derived summaries.

## Utility Modules

### `src/jambandnerd/db/connection.py`

- validates environment configuration
- creates and returns the shared Supabase client

### `src/jambandnerd/db/operations.py`

Current high-level operations include:

- `get_table_schema()`
- `prepare_dataframe_for_upsert()`
- `validate_and_upsert_dataframe()`
- `bulk_insert_dataframe()`
- `upsert_dataframe()`
- `replace_prediction_projection()`
- `fetch_existing_ids()`
- `fetch_existing_values()`
- `fetch_rows_by_column_values()`
- `fetch_latest_prediction_songs()`
- `check_prediction_staleness()`

These helpers are the write/read boundary used by collection scripts and
pipeline scripts.

### `src/jambandnerd/db/validation.py`

Validation and coercion are performed against the live or cached table schema.

Current behavior:

- safe type coercions are attempted first
- missing required columns fail the write
- nullability violations fail the write
- extra columns are logged as warnings
- non-critical type mismatches are logged as warnings after coercion

This matches the project rule that ingestion should be resilient without
silently accepting structurally broken writes.

## Data Type Conventions

- Postgres `text` -> pandas string/object
- Postgres `integer` and `bigint` -> pandas nullable `Int64`
- Postgres `boolean` -> pandas nullable boolean
- Postgres `timestamptz` -> timezone-aware pandas datetimes

Common coercions:

- empty strings in numeric/boolean columns become `NULL`
- boolean-like strings such as `true`, `false`, `1`, `0`, `yes`, `no` are
  coerced where possible

## Schema Introspection

Schema validation depends on the `get_table_schema` RPC in Supabase. If that
RPC is unavailable, callers degrade gracefully and skip live-schema validation
instead of blocking unrelated reads.

The repo also ships the migration that restricts schema RPC execution to
server-side contexts.

## Operational Expectations

- writes should use explicit conflict targets
- large writes should be chunked
- raw writes should preserve enough source information for reprocessing and
  traceability
- prediction freshness should be validated using `predicted_at`

## Related Documents

- [Data Strategy](data_strategy.md)
- [Predictions Schema](predictions_schema.md)
- [Unified Table Schemas](../schemas/unified_tables.md)
