# Session Log: 2026-03-25 - Replay Top-Level Route And Retention Validation

## Goal

Promote Replay to its own top-level website surface, back it with retained
historical prediction runs for both models, and make replay readiness part of
the normal validation workflow.

## Constraints

- Keep `/explorer` working as a compatibility path
- Use `historical_prediction_runs` as the canonical replay source
- Show both models together on Replay
- Preserve existing performance and compare surfaces
- Do not revert unrelated work already present in the branch

## Commands run

- `npm run lint:web`
- `npm run build:web`
- `uv run pytest tests/test_validate_accuracy_tables.py tests/pipeline/test_run_optimized_pipeline.py`

## Files changed

- `README.md`
- `apps/web/src/app/_venues/page.tsx`
- `apps/web/src/app/explorer/page.tsx`
- `apps/web/src/app/last-show/page.tsx`
- `apps/web/src/app/performance/page.tsx`
- `apps/web/src/app/replay/page.tsx`
- `apps/web/src/components/accuracy-table.tsx`
- `apps/web/src/lib/data.ts`
- `apps/web/src/lib/navigation.ts`
- `apps/web/tests/smoke/public-shell.spec.ts`
- `docs/operations/frontend_strategy.md`
- `docs/operations/mobile_verification.md`
- `docs/operations/website_delivery.md`
- `docs/reference/specifications/cli.md`
- `docs/reference/specifications/data_strategy.md`
- `scripts/README.md`
- `scripts/validate_accuracy_tables.py`
- `tests/test_validate_accuracy_tables.py`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed
- `uv run pytest tests/test_validate_accuracy_tables.py tests/pipeline/test_run_optimized_pipeline.py`: passed

## Notes

- `/replay` is now the canonical historical review route
- `/explorer` now redirects to `/replay`, preserving `band` and `date`
- replay data is loaded from retained `historical_prediction_runs`, not from
  `prediction_songs`
- Replay now shows both Notebook and CK+ boards for the same selected show
- Performance, last-show, and venue pages now link to `/replay`
- accuracy validation now checks that recent `accuracy_per_show` rows retain
  replay lineage through `prediction_run_id`
- I did not run a browser QA pass on the new Replay page in this session
