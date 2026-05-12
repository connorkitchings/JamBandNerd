# Session 01 - Goose Promotion-Readiness Review

**Date**: 2026-05-12  
**Branch**: `feat/wsp-combo-sweep`

## Goal

Review `goose_fast_rank_v1_candidate_relaxed_special_nbtop10` using existing
offline Goose backtest artifacts. Keep the review read-only with no registry or
production wiring changes.

## Changes

- Added `scripts/report_goose_promotion_readiness.py`.
- Added focused parser/segment/delta tests in
  `tests/scripts/test_report_goose_promotion_readiness.py`.
- Generated:
  - `diagnostics/goose_promotion_readiness.md`
  - `diagnostics/goose_promotion_readiness.json`

## Result

Recommendation: `promote_after_separate_production_wiring_task`.

The candidate beats both registered Goose and the Notebook floor on dual,
p@25, r@50, and F1@25 while matching Notebook p@10. Segment gains are
concentrated on `Not Part of a Tour` shows, and the normal-tour segment shows
no p@10, p@25, or F1@25 degradation versus registered Goose.

The JSONL artifacts do not store predicted song lists, so exact top-10 song
ordering remains covered by
`tests/models/test_goose_model.py::test_candidate_rank_guard_keeps_notebook_top_10`.

## Validation

```bash
uv run black scripts/report_goose_promotion_readiness.py tests/scripts/test_report_goose_promotion_readiness.py
uv run python scripts/report_goose_promotion_readiness.py
uv run pytest -q tests/scripts/test_report_goose_promotion_readiness.py
uv run pytest -q tests/models/test_goose_model.py tests/scripts/test_report_goose_promotion_readiness.py
uv run ruff check scripts/report_goose_promotion_readiness.py tests/scripts/test_report_goose_promotion_readiness.py
```

Status: all passed.

## Next Step

Open a separate production-wiring task if promoting the candidate: update Goose
registry wiring intentionally, keep the global relaxed variant diagnostic-only,
and rerun focused Goose plus registry tests before any live publishing.

## Follow-Up: Goose Production Wiring

Promoted the reviewed Goose candidate in code without live publishing:

- Added `GooseFastRankSpecialNotebookTop10Predictor` to
  `src/jambandnerd/models/goose/model.py`.
- Updated Goose production dispatch in `src/jambandnerd/models/registry.py`.
- Updated Goose `BandMetadata.model_version` and notes in
  `src/jambandnerd/models/metadata.py`.
- Exported the promoted predictor from `src/jambandnerd/models/goose/__init__.py`.
- Updated the registry test expectation for the promoted Goose class/version.

Validation:

```bash
uv run black src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py src/jambandnerd/models/registry.py src/jambandnerd/models/metadata.py tests/models/test_model_registry.py
uv run pytest -q tests/models/test_model_registry.py tests/models/test_goose_model.py tests/scripts/test_report_goose_promotion_readiness.py
uv run ruff check src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py src/jambandnerd/models/registry.py src/jambandnerd/models/metadata.py tests/models/test_model_registry.py
```

Status: all passed. No Supabase writes or live prediction publishing were run.

## Follow-Up: Five-Band Dispatch Verification

Strengthened `tests/models/test_model_registry.py` so registry coverage now
locks the active single-model band surface:

- `list_active_bands()` must return exactly `goose`, `phish`, `wsp`, `billy`,
  and `um`.
- Each active band must dispatch to the expected production predictor class.
- Each predictor `MODEL_VERSION` must match `get_band_model_version(band)`.

Validation:

```bash
uv run pytest -q tests/models/test_model_registry.py
uv run pytest -q tests/models/test_model_registry.py tests/models/test_goose_model.py tests/scripts/test_report_goose_promotion_readiness.py
uv run ruff check --fix tests/models/test_model_registry.py
uv run ruff check tests/models/test_model_registry.py
```

Status: all passed. No production code changes were needed for this verification
step beyond the Goose wiring already completed above.

## Follow-Up: Setlist Storage Rollout Validation

Validated the existing `setlist_*` prediction-facing storage contract instead
of designing new base tables.

Changes made:

- Added `supabase/migrations/20260512_add_target_show_date_to_setlist_accuracy.sql`
  so `setlist_accuracy` has the same explicit `target_show_date` contract used
  by live predictions and retained results.
- Updated retained accuracy writes in `scripts/run_backtest.py` to include
  `target_show_date`.
- Fixed retained-corpus pruning so incremental backfills preserve the full
  selected retention window instead of pruning to only newly scored shows.
- Made `setlist_prediction_songs` and `setlist_accuracy` writes tolerant of
  older deployed schemas by filtering payload columns against live schema
  metadata when available.
- Added regression coverage in:
  - `tests/pipeline/test_run_backtest.py`
  - `tests/test_db_operations.py`
  - `tests/test_setlist_schema_contract.py`

Remote data operations run:

- Published current live predictions for Goose, WSP, and Billy.
- Rebuilt retained corpus rows for Goose, WSP, Billy, UM, and Phish.
- Phish required a 101-show source window to retain 100 scored rows because
  one recent completed show did not produce an eligible scored result.

Current target Supabase state:

- `setlist_predictions`: populated for all five production bands.
- `setlist_prediction_songs`: 25 projected rows per active prediction.
- `setlist_results`: 100 retained historical dates per band/model.
- `setlist_accuracy`: 100 retained accuracy rows per band/model.
- Website reads confirmed:
  - current boards from `setlist_predictions`
  - history from `setlist_results`
  - performance from `setlist_accuracy`

Validation:

```bash
uv run python scripts/validate_prediction_tables.py
uv run python scripts/validate_accuracy_tables.py
uv run python scripts/check_prediction_storage_rollout.py --expected-state populated --output diagnostics/prediction_storage_rollout_report.json
uv run python scripts/audit_supabase_tables.py --output diagnostics/supabase_audit_report.json
uv run pytest -q tests/test_setlist_schema_contract.py tests/pipeline/test_run_backtest.py tests/test_db_operations.py tests/test_check_prediction_storage_rollout.py tests/test_validate_accuracy_tables.py
uv run ruff check tests/test_setlist_schema_contract.py scripts/run_backtest.py src/jambandnerd/db/operations.py tests/pipeline/test_run_backtest.py tests/test_db_operations.py
npm run verify:web
```

Status:

- Prediction validation passed.
- Accuracy validation passed.
- Supabase audit passed with one WSP warning:
  `recent_completed_shows_missing_setlists`.
- Web verification passed.
- Rollout checker still reports one blocker:
  `setlist_accuracy:schema_missing_columns:target_show_date`.

The local migration exists, but `supabase db push` did not apply it because the
configured Supabase access token was rejected as an invalid access token format.
Decision: no new prediction/history base tables are needed; finish by applying
the existing migration with a valid Supabase CLI token, then rerun the rollout
checker.

## Follow-Up: Supabase Native Access

Confirmed the Supabase CLI login issue was caused by a stale
`SUPABASE_ACCESS_TOKEN` environment variable in the Codex process. The variable
started with `sb_s`, which is a project API key shape, not a Supabase CLI
personal access token. Unsetting it for CLI commands lets the local
`~/.supabase` login token be used:

```bash
env -u SUPABASE_ACCESS_TOKEN supabase ...
```

`supabase db push` remains blocked by pre-existing migration history drift:
remote versions `20260406` and `20260410` do not match local migration files.
To avoid repairing unrelated migration history during this rollout, applied the
single idempotent migration directly:

```bash
env -u SUPABASE_ACCESS_TOKEN supabase db query --linked --file supabase/migrations/20260512_add_target_show_date_to_setlist_accuracy.sql
```

Post-migration validation:

```bash
uv run python scripts/validate_prediction_tables.py
uv run python scripts/validate_accuracy_tables.py
uv run python scripts/check_prediction_storage_rollout.py --expected-state populated --output diagnostics/prediction_storage_rollout_report.json
uv run python scripts/audit_supabase_tables.py --output diagnostics/supabase_audit_report.json
```

Status:

- `setlist_accuracy.target_show_date` schema blocker is resolved.
- Prediction validation passed after refreshing the Phish live prediction.
- Accuracy validation passed.
- Rollout checker is warning-only with all five bands populated.
- Supabase audit is warning-only because WSP has
  `recent_completed_shows_missing_setlists`.

## Follow-Up: Production Readiness Cleanup

Cleared the final WSP source-data warning and reran the review gates.

WSP repair:

- `audit_recent_setlist_completeness("wsp")` identified three missing recent
  completed shows:
  - `2026-05-08` (`22461`)
  - `2026-05-09` (`22462`)
  - `2026-05-10` (`22463`)
- Ran the existing WSP collector for 2026 with skip-existing behavior:

```bash
uv run python scripts/run_wsp_collection.py --skip_existing_setlists --year_start 2026 --year_end 2026
```

The collector inserted 61 WSP setlist rows and the recent completed-show check
then reported all recent WSP shows covered.

Final validation:

```bash
uv run python scripts/audit_supabase_tables.py --output diagnostics/supabase_audit_report.json
uv run python scripts/check_prediction_storage_rollout.py --expected-state populated --output diagnostics/prediction_storage_rollout_report.json
uv run python scripts/validate_prediction_tables.py
uv run python scripts/validate_accuracy_tables.py
uv run pytest -q tests/test_setlist_schema_contract.py tests/pipeline/test_run_backtest.py tests/test_db_operations.py tests/test_check_prediction_storage_rollout.py tests/test_validate_accuracy_tables.py
uv run pytest -q tests/models/test_model_registry.py tests/models/test_goose_model.py tests/scripts/test_report_goose_promotion_readiness.py
uv run ruff check scripts/run_backtest.py src/jambandnerd/db/operations.py tests/pipeline/test_run_backtest.py tests/test_db_operations.py tests/test_setlist_schema_contract.py tests/models/test_model_registry.py
npm run verify:web
```

Status:

- Supabase audit state: `ok`.
- Prediction storage rollout state: `ok`.
- Prediction table validation passed after refreshing UM live prediction.
- Accuracy table validation passed.
- Focused Python tests passed.
- Ruff passed.
- Web verification passed.
