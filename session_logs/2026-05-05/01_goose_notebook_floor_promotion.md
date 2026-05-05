# Session 01: Goose Notebook Floor Promotion

## Goal
Implement the Goose single-band next step: promote a Goose-owned predictor that
matches the Notebook 1-year quality floor while fitting the single-model
registry and serializer contracts.

## Constraints
- Preserve the `reference_date` anti-leakage boundary.
- Do not run Supabase publication commands in this session.
- Keep unrelated Black formatting drift out of this commit.
- Document the strict promotion-gate mismatch instead of hiding it.

## Changes
- Added `GooseNotebookFloorPredictor` in `src/jambandnerd/models/goose/model.py`.
- Registered Goose to `GooseNotebookFloorPredictor` in `models/registry.py`.
- Updated Goose `BandMetadata` to `goose_notebook_floor_v1`.
- Exported the predictor from `models/goose/__init__.py`.
- Added focused tests for defaults, band validation, Notebook ranking parity,
  and registry dispatch.
- Updated Goose/prediction reference docs for the active model version.

## Files Changed or Artifacts Produced
- `src/jambandnerd/models/goose/model.py`
- `src/jambandnerd/models/goose/__init__.py`
- `src/jambandnerd/models/metadata.py`
- `src/jambandnerd/models/registry.py`
- `tests/models/test_goose_model.py`
- `tests/models/test_model_registry.py`
- `docs/reference/specifications/goose_pipeline.md`
- `docs/reference/specifications/predictions_schema.md`
- `backtests/goose_goose_notebook_floor_v1_summary.json`
- `backtests/goose_goose_notebook_floor_v1_100shows.jsonl`
- `session_logs/2026-05-05/01_goose_notebook_floor_promotion.md`

## Commands Run
- `uv run pytest tests/models/test_goose_model.py -q`
- `uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseNotebookFloorPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests`
- `uv run python scripts/promote_phase_b_winner.py --incumbent backtests/goose_goose_phase_b_v1_summary.json --candidate backtests/goose_goose_notebook_floor_v1_summary.json`
- `uv run pytest tests/models/test_goose_model.py tests/models/test_model_registry.py tests/models/test_per_band_template.py -q`
- `npm run verify:python`
- `uv run black src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py`
- `uv run black --check src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py`
- `uv run ruff check src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py`
- `uv run ruff check --fix src/jambandnerd/models/registry.py tests/models/test_model_registry.py`
- `npm run verify:docs`

## Backtest Result
Command:

```bash
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseNotebookFloorPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests
```

Result:

| Metric | Value |
| --- | ---: |
| n | 100 |
| p@10 | 0.284 |
| p@25 | 0.216 |
| r@50 | 0.531 |
| F1@25 | 0.279 |
| dual | 0.408 |
| dual F1 | 0.233 |

The new summary exactly matches `backtests/goose_notebook_1yr_summary.json`.

## Promotion Gate Note
`scripts/promote_phase_b_winner.py` against `goose_phase_b_v1` reported not
eligible under the strict improvement gate:

- `p10_delta=+0.0190`, threshold `+0.0200`
- `f1_25_delta=+0.0092`, threshold `+0.0200`
- `r50_delta=-0.0026`, threshold `+0.0200`

The model was still registered because this session's acceptance criterion was
Notebook-floor parity with no regression against the best Notebook artifact.

## Validation
- `uv run pytest tests/models/test_goose_model.py -q` -> passed
- `uv run pytest tests/models/test_goose_model.py tests/models/test_model_registry.py tests/models/test_per_band_template.py -q` -> 51 passed
- `uv run black --check ...changed python files...` -> passed
- `uv run ruff check ...changed python files...` -> passed
- `npm run verify:docs` -> passed
- `npm run verify:python` -> blocked by pre-existing Black formatting drift in 16 unrelated files

## Publication and Validation Plan
Do not run these in this commit. They are the next implementation session.

1. Confirm `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are available.
2. Probe live Goose prediction generation without writing:

   ```bash
   uv run python scripts/generate_live_predictions.py --band goose --dry-run
   ```

3. If an upcoming Goose show exists, publish the live board:

   ```bash
   uv run python scripts/generate_live_predictions.py --band goose --require-output
   ```

4. Populate the retained 100-show completed corpus:

   ```bash
   uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 100 --require-results
   ```

5. Validate live prediction storage and song projection:

   ```bash
   uv run python scripts/validate_prediction_tables.py --band goose --max-age-hours 72
   ```

6. Validate retained historical replay and accuracy lineage:

   ```bash
   uv run python scripts/validate_accuracy_tables.py --band goose --max-age-hours 72 --replay-window 100
   ```

7. Separately clear the existing Black drift, then rerun:

   ```bash
   npm run verify:python
   npm run verify:docs
   ```

## One-Line Next Step
Publish and validate Goose `goose_notebook_floor_v1` Supabase outputs, then clear unrelated Python formatting drift so full verification can run.
