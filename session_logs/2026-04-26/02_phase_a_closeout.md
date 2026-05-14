# Phase A Closeout

## Goal

Polish and close out Phase A of `feat/single-model-per-band` before the
frontend cutover and Phase B. No behavioral code changes — docs, config
constants, and CI/script consistency only.

## Changes

### Docs

- `docs/reference/schemas/unified_tables.md`: Added branch note at the top
  framing the `setlist_*` tables as the active write boundary. Reframed legacy
  section heading as "Legacy Tables (read-only on this branch)". Renamed
  "Planned New Tables" to "Setlist Tables (Phase A)". Corrected
  `weighted_precision_score` formula from `0.2/0.5/0.3` to `0.2/0.7/0.1`.
- `docs/reference/specifications/predictions_schema.md`: Added branch-level
  framing note at the top.
- `.agent/AGENTS.md`: Added Phase A write-boundary pointer under Critical Rule 4
  so future sessions know `setlist_*` is the active contract on this branch.

### Config

- `src/jambandnerd/config/models.py`: Added Eggy deferral comment above
  `BAND_TOP_N`. Added Phase B promotion gate constants:
  `PHASE_B_MIN_BACKTEST_SHOWS = 50`, `PHASE_B_MIN_PRECISION_AT_25_DELTA = 0.03`
  (per ADR 0001).

### Audit script

- `scripts/audit_supabase_tables.py`: Removed leftover `model_slug` field
  entirely from `SupabaseModelAudit` dataclass, `as_dict()`, constructor call,
  and print output. Print now uses `model_version` as the model identifier.

### CI workflows

- `.github/workflows/backfill-predictions.yml`: Added inline comment explaining
  Eggy exclusion (parity with `daily-pipeline.yml`).
- `.github/workflows/live-tracker.yml`: Added `billy` and `um` to band choices;
  updated input description to remove stale "(goose or phish)" hint.

## Validation

- `uv run pytest tests/test_audit_supabase_tables.py -q`: 11 passed
- Phase A core suite: 43 passed
- `npm run verify:python`: 341 passed, 6 skipped
- `npm run verify:docs`: MkDocs strict build passed (no broken anchors)

## Next Steps

- **Frontend cutover**: Migrate `apps/web/src/lib/data/*.ts` to read from
  `setlist_*` tables. Drop model picker, compare page, replay page, and
  `MODEL_CONFIG`/`ACTIVE_MODELS`/`ModelSlug` from `apps/web/src/lib/config.ts`
  per ADR 0001 §Frontend.
- **Goose Supabase dry-runs**: Run once `SUPABASE_URL` and
  `SUPABASE_SERVICE_ROLE_KEY` are available locally (blocked from Phase A
  session).
- **Phase B**: Per-band model iteration starting with Goose. Promotion gate:
  `PHASE_B_MIN_PRECISION_AT_25_DELTA = 0.03` over
  `PHASE_B_MIN_BACKTEST_SHOWS = 50` shows vs. best legacy baseline.
