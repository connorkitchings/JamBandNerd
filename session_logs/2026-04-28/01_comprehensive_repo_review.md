# Comprehensive Repo Review: Docs, Code, and Supabase Directions Audit

## Goal

Review all documentation, code, and Supabase directions to ensure they reflect the changes made in the past 2 weeks (~55 commits). Identify and fix stale, incorrect, or missing information.

## Constraints

- Do not change behavior or add features — only fix accuracy.
- All edits must pass `npm run verify:python` and `npm run verify:docs`.
- Follow the end-session protocol for wrap-up.

## Method

1. Booted via `.agent/skills/start-session/` and read all boot-order files.
2. Gathered 2-week git history and latest session logs for context.
3. Launched 3 parallel explore agents to audit:
   - Docs staleness vs actual code (9 doc files)
   - Code accuracy vs docs (scripts, CLI entrypoints, table references, routes, registry, workflows, website modules)
   - Supabase documentation completeness (data_strategy, migrations, table schemas, RLS, website queries)
4. Compiled findings into a prioritized remediation plan (3 CRITICAL, 5 HIGH, 7 MEDIUM, 4 LOW).
5. Executed all 19 fixes.

## Commands Run

```bash
npm run verify:python   # 384 passed, 6 skipped
npm run verify:docs     # mkdocs build --strict passed
npm run verify:clean    # only expected changes shown
```

## Files Changed

### Docs (11 files)

| File | Change |
|---|---|
| `docs/reference/schemas/unified_tables.md` | Rewrote from legacy tables to current 4 split tables with full DDL, RLS, and legacy reference |
| `docs/operations/github_actions.md` | Rewrote backfill section to match actual workflow; fixed smoke schedule 20:30 → 22:00 UTC |
| `docs/reference/specifications/data_strategy.md` | Fixed unique constraint, added `completed_show_accuracy` column manifest, dual-write section, WSP canonicalizer, `collection_runs`/`wsp_shows_upcoming` |
| `docs/contributor/developer_guide/architecture.md` | Fixed model storage table, removed phantom `venues.ts`, added WSP canonicalizer |
| `docs/reference/specifications/predictions_schema.md` | Updated deferred section with dropped-table status and dual-write state |
| `docs/contributor/model_development.md` | `accuracy_per_show` → `completed_show_accuracy` |
| `docs/operations/tourwrangler_fallback.md` | Added song name canonicalization section |
| `docs/contributor/onboarding.md` | Added env var list and website `.env.local` setup step |
| `docs/contributor/supabase_local_dev.md` | **New file** — Supabase local development guide |
| `README.md` | Added PanicStream to WSP fallback chain + canonicalizer mention |
| `scripts/README.md` | Removed phantom `generate_billy_ckplus_predictions.py` reference |

### Code (2 files)

| File | Change |
|---|---|
| `scripts/wipe_band_data.py` | Added 4 split tables to wipe targets |
| `.github/workflows/live-tracker.yml` | Fixed band description to include `wsp` |

## Validation

- `npm run verify:python`: **384 passed, 6 skipped** (live-band smoke tests skipped without env vars)
- `npm run verify:docs`: **mkdocs build --strict passed**
- `npm run verify:clean`: only expected changes in diff

## Playbook Lesson Added

After rapid multi-session development, run a deliberate docs-vs-code audit across all entrypoint docs, schema docs, and workflow docs. Use parallel explore agents to compare actual code against documentation rather than relying on memory. The test suite catches some stale references (via `test_active_docs_do_not_reference_retired_storage_contract_terms`) but not schema accuracy, wrong schedules, or missing tables.

## Next Step

- Decide whether to remediate the missing recent Goose setlist (`show_id=1762797185`) before expanding split-storage rollout to other bands.
- Consider completing the Python migration to write only to split tables so the dual-write state can be resolved and legacy tables dropped.
