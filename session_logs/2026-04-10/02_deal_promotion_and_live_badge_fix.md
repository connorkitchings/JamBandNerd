# Deal Promotion and Tonight! Badge Fix

## Goal

1. Fix the "LIVE" badge showing one day early due to UTC vs. Eastern timezone mismatch on Vercel.
2. Rename the badge text from "LIVE" to "Tonight!".
3. Fully promote the Deal model to replace CK+ across the entire platform: Supabase RLS, daily pipeline, backfill workflow, and website.

## Constraints

- Do not break Notebook — it stays as the primary model.
- Keep CK+ entry in metadata for historical data retention (just disable all flags).
- `predictions_deal` and `accuracy_deal` tables exist in production; only public read RLS was missing.
- Architecture improvement: future model swaps should require only toggling `enabled` in `config.ts`.

## Commands Run

```bash
uv run pytest tests/models/test_deal_model.py tests/pipeline/test_compare_models.py -q
cd apps/web && npm run build
node --experimental-strip-types --test tests/unit/*.test.ts
```

## Files Changed or Artifacts Produced

**Supabase:**
- `supabase/migrations/20260410_grant_deal_tables_public_read.sql` (new) — public read RLS for `predictions_deal` and `accuracy_deal`; applied manually via Supabase SQL editor

**Backend / pipeline:**
- `src/jambandnerd/models/metadata.py` — CK+ all flags → False; notes retired 2026-04-10
- `.github/workflows/daily-pipeline.yml` — `--model ckplus` → `--model deal` in all 4 places; step name updated
- `.github/workflows/backfill-predictions.yml` — dropdown + "all" fallback updated to `deal`
- `scripts/backfill_predictions.py` — default model `"ckplus"` → `"deal"`
- `scripts/generate_billy_ckplus_predictions.py` — deleted
- `pyproject.toml` — `predict-billy-ckplus` entry point removed

**Website — Tonight! badge timezone fix:**
- `apps/web/src/app/predictions/page.tsx` — UTC → ET date, `"LIVE"` → `"Tonight!"`
- `apps/web/src/lib/data.ts` — all 3 `toISOString().slice(0, 10)` → `toLocaleDateString("en-CA", { timeZone: "America/New_York" })`
- `apps/web/src/components/prediction-hero.tsx` — badge check and text updated to `"Tonight!"`

**Website — Deal rollout:**
- `apps/web/src/lib/config.ts` — CK+ `enabled: false`, Deal `enabled: true`
- `apps/web/src/lib/data.ts` — removed `ckplusScore` from `PredictionRow`; snapshots initializer now derives from `ACTIVE_MODELS`
- `apps/web/src/components/song-board.tsx` — removed `isCkPlus` entirely; always Notebook-style columns
- `apps/web/src/app/replay/page.tsx` — fully generalized; secondary model derived from `ACTIVE_MODELS[1]`
- `apps/web/src/app/compare/page.tsx` — fallback `"ckplus"` → `"notebook"`; renamed `ckplusPerf`/`ckplusValue`
- `apps/web/src/app/about/page.tsx` — Deal description replaces CK+ in FAQ and model card
- `apps/web/src/app/data-use/page.tsx` — Deal replaces CK+ in prose
- `apps/web/src/app/(internal)/preview/tables/page.tsx` — `ckplusScore` removed from mock data
- `apps/web/tests/unit/format-predictions-text.test.ts` — fixture updated
- `apps/web/tests/unit/song-board.test.ts` — fixture updated
- `apps/web/tests/unit/model-agreement.test.ts` — fixture updated
- `apps/web/tests/unit/live-updates.test.ts` — `model_slug: "ckplus"` → `"deal"`

## Validation Status

Passed:
- `uv run pytest tests/models/test_deal_model.py tests/pipeline/test_compare_models.py` — 28/28
- `cd apps/web && npm run build` — compiled successfully, TypeScript clean, all 10 pages generated
- Unit tests: 16/17 pass; 1 pre-existing failure in `song-board.test.ts` (Node `@/` alias not resolvable outside Next.js — unrelated to session changes)

Not run:
- Full backfill of `predictions_deal` — pending merge; will be triggered via `gh workflow run` after PR merges

## Next Step

After merge: run `gh workflow run backfill-predictions.yml -f band=all -f model=deal -f dry_run=false` to populate Deal historical predictions, then verify the site shows Deal data live.
