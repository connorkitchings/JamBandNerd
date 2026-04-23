# Data Strategy

This document is the canonical data strategy for JamBandNerd. It defines how
ingestion, storage, normalization, prediction, and evaluation fit together
across all supported bands.

## Summary

JamBandNerd is a show-centric prediction system with a two-stage data contract:

1. Collect source-faithful raw data into band-specific Supabase tables.
2. Normalize those raw entities into one shared internal contract for
   transformations, models, predictions, and backtests.

The required predictive entities are:

- `shows`
- `setlists`
- `songs`

Supporting entities are allowed when a source requires them, but they are not
part of the core predictive contract:

- `venues`
- `upcoming_shows`
- source-specific helper data

## Core Principles

- **Show-centric first**: all downstream modeling is organized around ordered
  shows and the songs performed in them.
- **Two-stage contract**: raw storage may stay source-specific; transforms and
  models may not.
- **No intermediate Supabase transforms**: standardized data lives in memory,
  not in derived database tables.
- **Deterministic sequence**: every band must support a stable historical show
  ordering.
- **No leakage**: feature generation and backtests must honor `reference_date`.
- **Band-specific quirks stay at the edge**: collector and config layers absorb
  source differences so shared transforms and models remain generic.

## Canonical Data Flow

```text
External Source
  -> collector normalization
  -> {band}_*_raw tables
  -> shared normalization boundary
  -> ordered historical show sequence
  -> ModelData
  -> model prediction
  -> predictions/accuracy tables
  -> website reads
```

## Required Entity Contracts

### Shows

Each band must persist enough show data to answer:

- what show this record represents
- when the show occurred
- which band it belongs to
- how to sort it deterministically among other shows on the same date

Raw schemas may differ by source. The normalized show contract used by shared
code must expose:

- `show_id`: stable normalized show identifier
- `show_date`
- any deterministic secondary ordering key needed during normalization

### Setlists

Each band must persist enough setlist data to reconstruct a show sequence.

The normalized setlist contract used by shared code must expose:

- `show_id`
- `song_name`
- `set_number`
- song ordering field such as `song_position` or an equivalent normalized field

### Songs

Songs provide the shared song catalog and the canonical names consumed by
predictors. The exact raw source fields may vary, but each band must support:

- stable song identity where available
- canonical `song_name`

### Supporting Tables

Supporting tables are allowed when they help collection or reference-date
resolution, for example:

- `{band}_venues_raw`
- `um_upcoming_shows`

These remain optional support tables, not mandatory predictive inputs.

## Raw Ingestion Contract

Raw ingestion is intentionally source-faithful.

- Collectors write to `{band}_*_raw` tables.
- Required raw families for a fully supported band are `shows`, `setlists`, and
  `songs`.
- Additional supporting raw tables are allowed when justified by the source.
- Raw tables preserve source-specific IDs and fields where helpful for
  traceability and reprocessing.
- Schema validation happens at write time; missing required fields and
  nullability violations fail writes, while non-critical mismatches are logged.

Current examples in the repo:

- Active raw-table consumers normalize to `show_id` across all supported bands.
- UM also uses `um_upcoming_shows` to help resolve next-show predictions.

## Normalization Boundary

Shared prediction code must not depend directly on source-specific raw columns.

The normalization boundary currently lives in the shared script and
transformation layer:

- `scripts/common.py`
- `src/jambandnerd/transformations/gaps.py`

Normalization is responsible for:

- aliasing source-specific IDs and date columns into the shared contract
- coercing date types
- ensuring `show_id` and `song_name` are available to shared transforms
- preparing data for deterministic historical ordering

This is where source-specific column differences stop. Everything after this
boundary should behave as if every band exposes the same internal data model.

## Canonical Sequencing Rules

Prediction and backtest logic depends on a deterministic show sequence.

The canonical ordering rule is:

1. sort by `show_date`
2. break same-date ties with a stable deterministic secondary key

In current shared code, that secondary key is typically the normalized
`show_id`. If a source cannot guarantee that on its own, the collector or
normalization layer must preserve some equivalent deterministic key.

The derived `show_index` is the canonical historical sequence used for:

- gap features
- recent-show exclusion windows
- backtests
- model diagnostics

`show_index` is an internal derived feature, not a persisted source-of-truth
database column.

## Prediction Methodology Contract

All models consume the same normalized historical foundation:

1. load raw shows and setlists for a band
2. normalize them into the shared contract
3. sort historical shows deterministically
4. apply the `reference_date` cutoff
5. build `ModelData`
6. generate top-K predictions
7. store predictions
8. evaluate against held-out completed shows for backtests

The current shared `ModelData` handoff includes:

- `historical_plays`
- `master_feature_set`
- `reference_date`
- `reference_index`
- `recently_played_songs`
- diagnostics metadata

Any new model must consume the same leakage-safe ordering and cutoff rules.

## Storage Strategy

### Raw storage

- Canonical pattern: `{band}_shows_raw`, `{band}_setlists_raw`,
  `{band}_songs_raw`
- Supporting raw tables are allowed for source-specific needs

### Prediction storage

The current canonical prediction write boundary is one row per prediction run
context in a unified `predictions` table with a `model_slug` discriminator:

- `band`
- `model_slug`
- `reference_date`
- `model_version`
- `top_k`
- `predicted_at`
- JSON `predictions` payload

JamBandNerd also maintains a derived `prediction_songs` table with one row per
predicted song for SQL-friendly reads and analytics. That table is rebuildable
from the canonical run-level rows.

Historical scored backtests are stored separately in
`historical_prediction_runs`. This preserves the exact ranked board used for a
completed-show evaluation without mixing historical replay snapshots into the
live prediction tables. The website's `/replay` surface treats this table as
its canonical historical source and assumes each promoted model retains its
registry-defined replay window. In the current promoted set, Notebook targets
roughly the last 50 completed shows per band while Deal has a 10-show
readiness floor for replay coverage. The daily workflow still backtests both
promoted models across the last 50 completed shows.

### Accuracy storage

- `accuracy_per_show` is the canonical granular evaluation store.
- new `accuracy_per_show` rows link to `historical_prediction_runs` through
  `prediction_run_id`
- pipeline validation now checks that recent `accuracy_per_show` rows retain
  replay lineage, so replay readiness is part of normal data health.

## Current Decision: Prediction Storage

JamBandNerd is intentionally documenting the current JSON-row prediction storage
as canonical now, while keeping the main future alternative explicit.

### Current design: hybrid canonical row plus derived projection

Pros:

- simple canonical writes from the current pipeline
- easy upsert key by `(band, model_slug, reference_date, model_version)`
- SQL-friendly per-song querying via the derived projection table

Tradeoffs:

- one extra derived write path to maintain
- projection consistency now needs validation during rebuilds and diagnostics

### Future alternative: row-per-song as the canonical write path

Potential benefits:

- simpler read model if all consumers eventually converge on song-level rows
- cleaner lineage if the projection ever becomes the only storage shape

Potential costs:

- larger behavior change for scripts, validations, and website consumers
- less direct continuity with the current run-level upsert contract

This remains a future implementation decision, not the active architecture.

## Current Gaps To Address Later

- prediction storage may later move to row-per-song tables if the website or
  analytics layer requires it

## Band Registry

Band metadata (slug, display name, raw table names, ID columns) is maintained
in the `bands` Supabase table for runtime consumers such as the website. Repo
workflow support is defined separately in `src/jambandnerd/config/bands.py`.
The website fetches active bands dynamically from the `bands` table rather than
maintaining a hardcoded static list.

The `bands` table schema:

```sql
CREATE TABLE public.bands (
    slug text NOT NULL,
    display_name text NOT NULL,
    shows_table text NOT NULL,
    id_column text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT bands_pkey PRIMARY KEY (slug)
);
```

Current supported bands:
- `goose` / Goose / goose_shows_raw / show_id
- `phish` / Phish / phish_shows_raw / show_id
- `eggy` / Eggy / eggy_shows_raw / show_id
- `billy` / Billy Strings / billy_shows_raw / show_id
- `wsp` / Widespread Panic / wsp_shows_raw / show_id
- `um` / Umphrey's McGee / um_shows_raw / show_id

New band onboarding workflow:
1. Write the band's collector script → creates `{band}_shows_raw`, `{band}_setlists_raw`
2. Update the repo-authoritative workflow/config surface in `src/jambandnerd/config/bands.py`
3. Insert a row into the `bands` table
4. The website automatically discovers and surfaces the new band

## Historical Prediction Runs (Replay Lineage)

The `historical_prediction_runs` table preserves exact prediction boards for completed shows,
enabling the Replay feature. Each row stores:

- `band`, `model_slug`, `model_version`: prediction context
- `reference_date`: when the prediction was made
- `target_show_id`, `target_show_date`: the show being predicted
- `actual_songs`: JSON snapshot of the setlist at scoring time
- `predictions`: exact ranked JSON payload emitted by the model
- `run_type`: either 'backtest' or 'live'

The `accuracy_per_show` table links back to `historical_prediction_runs` via
`prediction_run_id`, creating full lineage from evaluation back to the original prediction.

The website's `/replay` surface assumes each promoted model's registry-defined
replay window remains queryable. In the current promoted set, Notebook's
readiness target is 50 recent shows while Deal's readiness floor is 10.

## Per-Song Prediction Projection

`prediction_songs` is a derived table storing one row per predicted song for SQL-friendly
reads and analytics. It is rebuildable from the canonical run-level rows in
the unified `predictions` table.

Schema:
- `band`, `model_slug`, `model_version`, `reference_date`: prediction context
- `predicted_at`: when the prediction was generated
- `rank`, `song_name`, `top_k`: song position in the prediction board
- `prediction_payload`: model-specific JSON object for that ranked song

Unique constraint on `(band, model_slug, model_version, reference_date, rank)`
ensures deterministic upserts.

## Files To Treat As Current References

- `README.md`
- `docs/contributor/developer_guide/architecture.md`
- `docs/reference/specifications/database.md`
- `docs/reference/specifications/predictions_schema.md`
- `docs/reference/schemas/unified_tables.md`
