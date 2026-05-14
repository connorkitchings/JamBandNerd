# Goose Phase B Local Model Start

## Goal

Begin Goose-first Phase B model development after confirming whether the new
`setlist_*` Supabase tables were required before model iteration.

## Constraints

- Stay on `feat/single-model-per-band`.
- Do not use `main` for development.
- Preserve the `reference_date` anti-leakage boundary.
- Keep shared infrastructure band-agnostic; Goose-specific model behavior lives
  under `src/jambandnerd/models/goose/`.
- Avoid Supabase prediction/history writes during model iteration unless
  explicitly moving to release-readiness or promotion evidence.

## Key Decision

Supabase `setlist_*` population is a website/storage release-readiness step,
not a prerequisite for local Goose model development. Goose model iteration
should use local raw-table snapshots and dry-run backtests until promotion
evidence is ready.

## Local Dataset

Exported Goose raw snapshots:

```bash
uv run python scripts/export_backtest_snapshots.py --band goose --snapshot-root .snapshots/goose_phase_b
```

Snapshot contents:

- `goose_shows_raw`: 834 rows
- `goose_setlists_raw`: 7136 rows

Validated local dry-run path:

```bash
uv run python scripts/run_backtest.py --band goose --shows 3 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
```

Initial `goose_phase_b_v1` 3-show smoke metrics:

- K=10: hit_rate=1.000, avg_matches=3.667, precision=0.367, recall=0.273, f1=0.313
- K=25: hit_rate=1.000, avg_matches=6.667, precision=0.267, recall=0.490, f1=0.345
- K=50: hit_rate=1.000, avg_matches=6.667, precision=0.133, recall=0.490, f1=0.210

## Files Changed

- `src/jambandnerd/models/goose/model.py` — new Goose Phase B predictor.
- `src/jambandnerd/models/goose/__init__.py` — package export.
- `src/jambandnerd/models/registry.py` — Goose dispatches to the band-owned predictor; other bands remain on `BaselinePredictor`.
- `src/jambandnerd/models/metadata.py` — Goose model version updated to `goose_phase_b_v1`.
- `tests/models/test_goose_model.py` — new Goose predictor tests.
- `tests/models/test_model_registry.py` — added single-band dispatch coverage.
- `docs/reference/specifications/goose_pipeline.md` — documented local snapshot model workflow.
- `docs/reference/specifications/predictions_schema.md` — updated active Goose model-version example.

## Artifacts Produced

- `.snapshots/goose_phase_b/goose_shows_raw.json`
- `.snapshots/goose_phase_b/goose_setlists_raw.json`
- `.snapshots/goose_phase_b/manifest.json`

## Commands Run

```bash
uv run python scripts/audit_supabase_tables.py
uv run python scripts/export_backtest_snapshots.py --band goose --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_backtest.py --band goose --shows 50 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
uv run python scripts/run_backtest.py --band goose --shows 3 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
uv run pytest tests/models/test_goose_model.py tests/models/test_model_registry.py -q
uv run pytest tests/models -q tests/pipeline/test_generate_live_predictions.py tests/pipeline/test_run_backtest.py
uv run ruff check src/jambandnerd/models/goose src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py
uv run black tests/models/test_goose_model.py
uv run black --check src/jambandnerd/models/goose src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py
npm run verify:docs
```

## Validation

```bash
uv run pytest tests/models/test_goose_model.py tests/models/test_model_registry.py -q
uv run pytest tests/models -q tests/pipeline/test_generate_live_predictions.py tests/pipeline/test_run_backtest.py
uv run ruff check src/jambandnerd/models/goose src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py
uv run black --check src/jambandnerd/models/goose src/jambandnerd/models/metadata.py src/jambandnerd/models/registry.py tests/models/test_goose_model.py tests/models/test_model_registry.py
npm run verify:docs
uv run python scripts/run_backtest.py --band goose --shows 3 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
```

All listed validation completed successfully. Full `npm run verify:python`,
`npm run verify:web`, and `npm run verify:clean` were not run because this was
a focused backend model-start session with no web code changes.

## Notes

- A Supabase population attempt was stopped after the user clarified the local
  model-development preference. The stopped backtest was still in scoring and
  had not reached its write phase.
- The local 50-show dry run was also stopped because it is too slow as an
  iteration smoke. Use `--shows 3` for quick checks and reserve `--shows 50`
  for promotion evidence.

## Next Step

Run a full Goose `--shows 50` snapshot dry-run for `goose_phase_b_v1`, compare
precision@25 against the legacy Notebook/Deal baseline, then tune only if the
promotion gate is not met.
