# Goose Pipeline Specification (Phase 2)

Scope: Define the end-to-end Goose pipeline for initial backfill and daily runs: collect →
transform → predict. No automation yet; CLI is designed to be schedulable later.

## Data Sources

- API: elgoose.net
- Reference: `documents/data/goose_api_schema.md`
- Endpoints:
  - Songs: `/api/v2/songs.json`
  - Shows: `/api/v2/shows.json`
  - Setlists: `/api/v1/setlists.json`

## Raw Tables (Supabase)

- `goose_songs_raw`
  - Primary key: `id`
  - Notable fields: `id`, `name`, `slug`, `isoriginal`, `original_artist`, `created_at`, `updated_at`
- `goose_shows_raw`
  - Primary key: `show_id`
  - Notable fields: `show_id`, `show_date`, `permalink`, `venue_id`, `venuename`, `city`,
    `state`, `country`, `tour_id`, `updated_at`, `created_at`
- `goose_setlists_raw`
  - Primary key: `uniqueid`
  - Notable fields: `uniqueid`, `show_id`, `song_id`, `songname`, `settype`,
    `setnumber`, `position`, `transition_id`, `transition`, `footnote`, `isjam`, `isreprise`,
    `isjamchart`, `tracktime`, `tour_id`, `venuename`, `city`, `state`, `country`, `shownotes`

Notes:

- Use `updated_at` (when present) for incremental detection; otherwise rely on unique keys and
  existence checks.
- Store API response hash (optional) for future change detection.

## Standardized Data (In-Memory)

The transformation from raw data to a standardized format occurs in-memory.
The resulting DataFrames are used directly by the prediction models and are
not persisted to the database.

Transformation rules:

- Normalize booleans (0/1, strings) to true/false with NULL for empties.
- Normalize integers; coerce numeric-like strings; NULL on empty.
- Standardize set labels: map `settype`/`setnumber` to `set_name` and `set_index`.
- Parse `tracktime` (`MM:SS`) to seconds (int) when possible.
- Ensure consistent `show_date` as `date`.

## Orchestration

- Initial backfill (no dates):
  - `jbn collect goose` → fetch all and load into raw tables.
  - `jbn transform goose` → (In-memory step, no command needed)
  - `jbn predict goose --model notebook` → compute predictions for all eligible shows.

- Daily run (incremental):
  - `jbn run goose --stages collect,predict --model notebook --incremental`
  - Collect: filter by `updated_at`/latest known showdate if available; otherwise deduplicate using keys.
  - Transform: performed in-memory by the predict step.
  - Predict: run for new/changed shows; can recompute recent window if needed.

## Idempotency & Integrity

- Use upserts with conflict targets on primary keys for raw and standardized tables.
- Maintain a `run_id` and `generated_at` for predict stage rows.
- Validation step before writes: compare DataFrame schema to table schema; coerce types where safe.

## Error Handling

- API failures: retry (exponential backoff, 3 attempts); on persistent failure, skip endpoint and
  continue others.
- Partial failures: collect and report; ensure pipeline returns non-zero exit code when critical.
- Logging: stage start/end, counts, durations, failure summaries.

## Inputs/Outputs (per stage)

- Collect
  - Input: none (API)
  - Output: `goose_songs_raw`, `goose_shows_raw`, `goose_setlists_raw`
- Transform
  - Input: `goose_*_raw` tables
  - Output: In-memory pandas DataFrames for the predict step.
- Predict
  - Input: In-memory pandas DataFrames from the transform step.
  - Output: `predictions_notebook`, `notebook_accuracy`, `predictions_ckplus`, `accuracy_ckplus`

## Open Questions

- Do we maintain a lightweight change-log table for API pulls (for auditing)?
- Prediction scope: next-song vs multiple contexts (e.g., set position)? MVP assumes next-song.
