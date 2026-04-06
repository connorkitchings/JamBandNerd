# Session Log: 2026-03-25 - Replay Backfill Completed With Buffered Recent Window

## Goal

Backfill retained historical prediction runs so Replay has coverage for the
recent window across all supported bands and both models.

## Constraints

- Keep older performance history intact
- Guarantee a replayable 50-show window even when sparse recent shows are skipped
- Use the new `historical_prediction_runs` / `prediction_run_id` lineage path

## Commands run

- `env -u SUPABASE_ACCESS_TOKEN supabase db push` (failed due remote migration history mismatch)
- manual remote schema verification via Python client
- `uv run pytest tests/test_validate_accuracy_tables.py`
- `uv run python scripts/rebuild_derived_data.py --band goose --recent-shows 60 --aggregate-shows 100`
- `uv run python scripts/rebuild_derived_data.py --band all --recent-shows 75 --aggregate-shows 100`
- post-run replay coverage audit via Python client

## Files changed

- `scripts/validate_accuracy_tables.py`
- `tests/test_validate_accuracy_tables.py`

## Validation status

- `uv run pytest tests/test_validate_accuracy_tables.py`: passed
- all-band rebuild command: passed
- post-run replay audit:
  - Goose notebook/ckplus: `50 / 50`
  - Eggy notebook/ckplus: `50 / 50`
  - Phish notebook/ckplus: `50 / 50`
  - WSP notebook/ckplus: `50 / 50`
  - Billy notebook/ckplus: `50 / 50`
  - UM notebook/ckplus: `50 / 50`

## Notes

- The original `--recent-shows 50` plan was too tight because some completed
  shows are intentionally skipped during backtest when the setlist is too sparse
  to score.
- Goose exposed a second issue: replay-lineage validation must reason per
  `show_date`, not per raw `accuracy_per_show` row, because older duplicate
  rows can coexist beside a newly lineaged row.
- Final operational command used a buffered window:

```bash
uv run python scripts/rebuild_derived_data.py --band all --recent-shows 75 --aggregate-shows 100
```

- That produced a reliable 50-show replayable window for all 6 bands and both
  models without clearing older history.

## Next step

Run a browser pass on `/replay`, then commit and merge the completed web + replay-retention work.
