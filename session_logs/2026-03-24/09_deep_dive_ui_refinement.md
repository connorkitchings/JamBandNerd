# Session Log: 2026-03-24 - Deep Dive UI Refinement

## Goal

Streamline the JamBandNerd Deep Dive section to focus on model evaluation and prediction transparency, following the pivot from general analytics to a specialized validation suite.

## Constraints

- Archive redundant "Venue Analytics" features.
- Ensure the "Compare" page is dynamic and future-proof for additional models.
- Support both Precision and Recall metrics across all evaluation views.

## Commands run

- `npm run build:web`

## Files changed

- `apps/web/src/app/compare/page.tsx`: Refactored to be dynamic (using `ACTIVE_MODELS`) and added head-to-head precision/recall tracking.
- `apps/web/src/app/explorer/page.tsx`: Added real-time precision calculation and UI display.
- `apps/web/src/app/performance/page.tsx`: Pivoted primary view to Precision (Hit Rate) for better user intuition.
- `apps/web/src/lib/data.ts`: Updated `getRecentAccuracy` to fetch Precision columns from Supabase.
- `apps/web/src/app/(internal)/preview/tables/page.tsx`: Fixed mocked data for type safety.

## Validation status

- **Successful build**: `npm run build:web` passed after all refactors.
- **Dynamic Models**: The Compare page now automatically handles any models in `ACTIVE_MODELS` without hardcoding.
- **Metric Clarity**: Distinguishing between Recall (coverage) and Precision (hit rate) across all deep-dive screens.

## Next step

- Performance Pass: Audit `RecallChart` and `AccuracyTable` components to explicitly support switching between Precision and Recall modes for advanced users.
