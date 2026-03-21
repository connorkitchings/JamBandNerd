# Session 10: Frontend Strategy, UX Polish, Backfill, and Deployment

## Goal

Build out the frontend strategy (Phase 1 of 2): uncertainty communication, UX improvements, accessibility, backfill infrastructure, and production deployment.

## Constraints

- Predictions are probabilistic signals, not certain outcomes — must communicate uncertainty honestly
- Mobile-first
- Notebook model should be primary
- Random baseline comparisons explicitly ruled out
- Only one accuracy metric (Recall) with K=10 as primary
- Accuracy drivers are only what the algorithms use

## Commands Run

### Python backend
```bash
# Lint
uv run ruff check src tests scripts  # All checks passed

# Tests
uv run pytest tests/ -v --tb=short  # 129 passed, 6 skipped
```

### GitHub Actions
```bash
# Backfill predictions (6 combinations)
gh workflow run backfill-predictions.yml --field band=goose --field model=ckplus
gh workflow run backfill-predictions.yml --field band=goose --field model=notebook
gh workflow run backfill-predictions.yml --field band=phish --field model=ckplus
gh workflow run backfill-predictions.yml --field band=phish --field model=notebook
gh workflow run backfill-predictions.yml --field band=wsp --field model=ckplus
gh workflow run backfill-predictions.yml --field band=wsp --field model=notebook

# Backtest accuracy (6 combinations)
python scripts/run_backtest.py --band X --model Y --shows 100
```

### Vercel deployment
```bash
# Set env vars via API
curl -X PATCH "https://api.vercel.com/v1/projects/prj_pg3ADjJrEH1dSRLRbK7tLuvqYAKZ/env/..."

# Trigger deployment
curl -X POST "https://api.vercel.com/v13/deployments" -H "Authorization: Bearer $VERCEL_TOKEN" ...
```

## Files Changed / Artifacts Produced

### Backend
- `src/jambandnerd/transformations/gaps.py` — Added `recent_avg_gap` field (avg over last 25 plays)
- `src/jambandnerd/models/ckplus/model.py` — Added `recent_avg_gap` to `CKPlusPrediction` dataclass and output
- `scripts/generate_predictions.py` — Write `recent_avg_gap` field to predictions JSON

### Frontend
- `apps/web/src/lib/data.ts` — `recentAvgGap` field in `PredictionRow` type; `ModelAgreement` type with tiered structure; `calculateModelAgreement` returns top-10/25/50 + weighted composite
- `apps/web/src/lib/config.ts` — Reordered `MODEL_CONFIG` so Notebook is first
- `apps/web/src/components/prediction-hero.tsx` — Tiered model agreement display; Show Outlook uses `recentAvgGap`; cleaner labels
- `apps/web/src/components/song-board.tsx` — Per-song both-models checkmark icon; aria attributes on tier sections
- `apps/web/src/app/page.tsx` — Passes secondary songs to SongBoard for agreement indicators
- `apps/web/src/app/explorer/page.tsx` — Model agreement badge updated to composite score
- `apps/web/src/app/performance/page.tsx` — K=10/25/50 toggle; all stats update with selected K
- `apps/web/src/app/globals.css` — `@media (prefers-reduced-motion: reduce)` block
- `apps/web/src/app/layout.tsx` — Skip-to-content link
- `apps/web/src/app/about/page.tsx` — FAQ expanded with Recall definition, prediction drivers, band variability
- `apps/web/src/components/global-search.tsx` — `focus-visible:ring` on dropdown items
- `apps/web/src/components/song-search.tsx` — `focus-visible:ring` on input
- `apps/web/src/components/k-toggle.tsx` — New K toggle component for performance page
- `apps/web/src/components/recall-chart.tsx` — `k` prop for configurable K display

### CI/CD
- `.github/workflows/backfill-predictions.yml` — Manual workflow for backfilling predictions with `band`, `model`, `dry_run` inputs
- `scripts/get_prediction_dates.py` — Query prediction dates from Supabase

### Docs
- `docs/operations/frontend_strategy.md` — Comprehensive frontend strategy document

## Validation Status

- Ruff: All checks passed
- Pytest: 129 passed, 6 skipped
- Web build: Clean
- Vercel deployment: Live at jambandnerd.com
- GitHub Actions backfill: All 6 combinations completed
- Backtests: All 6 combinations completed
- Python tests: Not re-run (not modified in this session)
- Web smoke tests: Not re-run (not modified in this session)

## Next Step

Phase 2 frontend strategy: RecallChart baseline annotations (if desired), further About/FAQ polish, and any remaining UX refinements based on real user feedback.
