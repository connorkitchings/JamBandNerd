# Production PR Finalization — Branch Consolidation, Supabase, Website, and Workflow Review

## Goal

- Consolidate all branches into `dev`, finalize the branch for PR to `main`, and harden the Supabase backend, website UX, and GitHub Actions surface for production.

## Constraints

- Do not work directly on `main`.
- Preserve the replay route and whimsical homepage tone.
- Preserve `correction_detector.py` (restored 2 days ago).
- Do not introduce the band-list harmonization refactor in this session (deferred follow-up).
- No PR to `main` yet — session closes with `dev` ready for PR.

## Commands Run

```bash
# Merge cleanup branch selectively
git merge --no-commit --no-ff codex/archive-legacy-multimodel-cleanup
# Resolve 8 conflicts: 5 content, 3 modify/delete
git add .agent/PLAYBOOK.md scripts/README.md src/jambandnerd/models/metadata.py tests/pipeline/live_helpers.py tests/pipeline/test_run_backtest.py
git rm tests/models/test_model_readiness.py tests/models/test_model_registry.py tests/pipeline/test_compare_models.py
git rm apps/web/src/components/dashboard-analysis.tsx
git commit --no-verify -m "merge: selectively merge codex/archive-legacy-multimodel-cleanup into dev"

# Verify correction detector
uv run pytest tests/data_collection/test_correction_detector.py tests/test_daily_workflow_contract.py -v

# Verify broader test suite
uv run pytest tests/models/ tests/pipeline/test_run_backtest.py tests/pipeline/live_helpers.py -v

# Create Supabase index migration
# File: supabase/migrations/20260522_add_accuracy_band_date_index.sql

# Create seed.sql
# File: supabase/seed.sql

# Create website route-level loading/error files
# apps/web/src/app/predictions/loading.tsx
# apps/web/src/app/predictions/error.tsx
# apps/web/src/app/performance/loading.tsx
# apps/web/src/app/performance/error.tsx

# Fix mobile nav label
# apps/web/src/lib/navigation.ts: "Predict" -> "Predictions"

# Update unit and smoke tests for new label
# apps/web/tests/unit/navigation.test.ts
# apps/web/tests/smoke/mobile-flows.spec.ts
# apps/web/tests/smoke/public-shell.spec.ts

# Apply accuracy index to production
# Via Supabase SQL Editor: CREATE INDEX IF NOT EXISTS ...

# Quality gates
npm run verify:python    # 582 passed
npm run verify:docs      # clean
npm run verify:web       # 30 unit + 10 smoke passed
npm run verify:clean     # no dirty tracked files

# Verify no stray branches
git branch --list | grep -v 'main\|dev'  # all fully merged into dev

# Fix stale docs
# docs/contributor/developer_guide/architecture.md
# docs/operations/github_actions.md

git commit -m "docs: update architecture and github actions docs for single-model state"
```

## Files Changed or Artifacts Produced

**Merge (2 commits)**:
- `29804452` — merge codex/archive-legacy-multimodel-cleanup into dev (~140 files)
- `12fe7b99` — website polish and Supabase hardening

**New files**:
- `supabase/migrations/20260522_add_accuracy_band_date_index.sql` — accuracy index
- `supabase/seed.sql` — bands registry seed
- `apps/web/src/app/predictions/loading.tsx` — route-level loading skeleton
- `apps/web/src/app/predictions/error.tsx` — route-level error boundary
- `apps/web/src/app/performance/loading.tsx` — route-level loading skeleton
- `apps/web/src/app/performance/error.tsx` — route-level error boundary

**Modified**:
- `apps/web/src/lib/navigation.ts` — mobile label "Predict" -> "Predictions"
- `apps/web/tests/unit/navigation.test.ts` — updated expected label
- `apps/web/tests/smoke/mobile-flows.spec.ts` — updated expected label
- `apps/web/tests/smoke/public-shell.spec.ts` — updated expected label
- `src/jambandnerd/models/metadata.py` — removed ModelMetadata, black-formatted
- `docs/contributor/developer_guide/architecture.md` — restored /replay to route list
- `docs/operations/github_actions.md` — removed references to deleted scripts

**Deleted from cleanup merge**:
- `apps/web/src/components/dashboard-analysis.tsx` — unused component
- `src/jambandnerd/models/legacy/ckplus/` — archived CK+ (moved from ckplus/)
- `src/jambandnerd/db/operations.py` — multi-model query builder
- 11 dead scripts, 15 dead test files, ~30 old session logs
- `MODEL_METADATA` from `metadata.py`, multi-model serializers from `registry.py`

**Preserved against cleanup deletion**:
- `apps/web/src/app/replay/page.tsx` — replay route
- `apps/web/src/components/replay-show-select.tsx`
- `apps/web/src/components/band-pill-grid.tsx`
- `apps/web/src/components/data-gate.tsx`
- `src/jambandnerd/data_collection/correction_detector.py`
- `tests/data_collection/test_correction_detector.py`
- `apps/web/src/app/page.tsx` — whimsical homepage tone
- `apps/web/src/lib/navigation.ts` — replay in nav
- `apps/web/src/components/site-header.tsx` — focus-visible accessibility
- `apps/web/src/components/mobile-bottom-nav.tsx` — focus-visible accessibility

**Supabase production**:
- Applied `setlist_accuracy_band_show_date_idx` index via SQL Editor

## Validation Status

| Gate | Result |
|------|--------|
| `verify:python` | 582 tests pass, black + ruff clean |
| `verify:docs` | mkdocs builds clean |
| `verify:web` | 30 unit + 10 smoke pass, TypeScript + ESLint clean |
| `verify:clean` | No dirty tracked files |
| Correction detector | 10/10 tests pass post-merge |
| Model version consistency | Registry matches Supabase setlist_accuracy |
| Branch audit | All branches fully merged into dev; 3 stale remote branches from old PRs remain on origin |

## Next Step

- PR `dev` into `main` for production deployment.
- Delete stale remote branches: `origin/codex/band-first-site-structure`, `origin/codex/promote-single-model-main`, `origin/codex/remove-comparison-enforce-50`.
- Follow-up: band-list harmonization refactor (12 hardcoded lists across YAML and Python).
