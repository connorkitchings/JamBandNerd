# Goose Pipeline Specification

This page describes Goose as a worked example of the current JamBandNerd
pipeline. It should be read alongside the canonical
[Data Strategy](data_strategy.md), not as a separate architecture.

## Source

- API: elgoose.net
- Endpoints:
  - songs
  - shows
  - setlists

## Raw Tables

- `goose_songs_raw`
- `goose_shows_raw`
- `goose_venues_raw`
- `goose_setlists_raw`

Notes:

- Goose follows the standard raw pattern of songs, shows, and setlists.
- Venues are stored as a supporting raw table.
- Shared prediction code still consumes normalized shows/setlists/songs rather
  than reading source-specific Goose fields directly.

## Normalization

Goose participates in the same shared normalization boundary as the other bands.

Current normalization expectations:

- expose `show_id`
- expose `show_date`
- expose `song_name`
- preserve set and song ordering fields
- support deterministic show ordering by `show_date`, then `show_id`

The normalized Goose data is then transformed into `ModelData` in memory.

## Current Commands

Recommended end-to-end pipeline:

```bash
uv run python scripts/run_optimized_pipeline.py --band goose
```

Granular commands:

```bash
uv run python scripts/run_goose_collection.py
uv run python scripts/generate_live_predictions.py --band goose
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 100
```

## Prediction and Storage

- Goose currently uses the Phase B band-owned predictor at
  `src/jambandnerd/models/goose/model.py`.
- The active Goose model version is `goose_phase_b_v1`.
- live next-show predictions are stored in `setlist_predictions` with
  derived rows in `setlist_prediction_songs`
- retained completed-show boards are stored in `setlist_results`
- per-show metrics are stored in `setlist_accuracy`

The active metric corpus is the last 100 eligible completed shows for Goose's
registered model version.

## Local Model Development

Use local raw-table snapshots for Goose model iteration instead of repeatedly
reading or writing Supabase prediction tables:

```bash
uv run python scripts/export_backtest_snapshots.py --band goose --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_backtest.py --band goose --shows 3 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
```

For larger local datasets, prefer Parquet snapshots:

```bash
uv run python scripts/export_backtest_snapshots.py --band goose --snapshot-root .snapshots/goose_phase_b --format parquet
```

For promotion evidence, run the same backtest path with `--shows 50`. Keep
`--dry-run --no-incremental` during model iteration to avoid Supabase writes
and incremental checks.

## Integrity Expectations

- collection writes use explicit conflict targets
- transforms remain in memory
- `reference_date` gates all feature generation and backtests
- Goose-specific source quirks stop at the normalization boundary

## Related Documents

- [Data Strategy](data_strategy.md)
- [Transformations](transformations.md)
- [Predictions Schema](predictions_schema.md)
