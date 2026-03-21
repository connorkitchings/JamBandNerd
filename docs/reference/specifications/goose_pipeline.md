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
uv run python scripts/generate_predictions.py --band goose --model notebook
uv run python scripts/generate_predictions.py --band goose --model ckplus
uv run python scripts/run_backtest.py --band goose --model notebook --shows 50
uv run python scripts/save_aggregate_accuracy.py --band goose --model notebook --shows 50
```

## Prediction and Storage

- live predictions are stored in `predictions_notebook` and
  `predictions_ckplus`
- per-show evaluation is stored in `accuracy_per_show`
- aggregate summaries are stored in `notebook_accuracy` and `accuracy_ckplus`

The current design stores one prediction row per
`(band, reference_date, model_version)`, with a ranked JSON predictions array.

## Integrity Expectations

- collection writes use explicit conflict targets
- transforms remain in memory
- `reference_date` gates all feature generation and backtests
- Goose-specific source quirks stop at the normalization boundary

## Related Documents

- [Data Strategy](data_strategy.md)
- [Transformations](transformations.md)
- [Predictions Schema](predictions_schema.md)
