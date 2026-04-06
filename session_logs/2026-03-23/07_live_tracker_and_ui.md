# Session Log: 2026-03-23

## Goal

Implement Real-Time Show Tracking (Phase 2 feature) and refine the predictions page UI.

## Constraints

- Phish and Goose do not have push-based webhooks, so API polling logic is required to bypass standard data collection caching.
- Widespread Panic tracking relies on the Bluesky AT Protocol for keyless, auth-free public feed access since the site does not provide real-time updates.
- Twitter integration for Umphrey's McGee was skipped due to missing API keys.
- The web app UI must isolate historical performance metrics from next-show predictions to reduce user cognitive load and strictly define the purpose of the home page.

## Commands run

- `npm run lint:web`
- `npm run build:web`
- `uv run python scripts/run_live_tracker.py --help`
- `uv run ruff check scripts/run_live_tracker.py --fix`

## Files changed or artifacts produced

- `scripts/run_live_tracker.py` (Created and enhanced with WSP Bluesky support)
- `.github/workflows/live-tracker.yml` (Created manually triggered GH action for tracking)
- `supabase/migrations/20260323_enable_realtime.sql` (Enabled supabase realtime push)
- `apps/web/src/components/live-tracker.tsx` (Subscribes to DB changes and refreshes Next.js router)
- `apps/web/src/components/prediction-hero.tsx` (Removed track record and hidden redundant desktop info)
- `apps/web/src/app/page.tsx` (Refactored to remove DashboardAnalysis)

## Validation status

- All TS/Next.js builds pass cleanly.
- Python scripts format perfectly and type checks are verified.

## Next step

- Begin Phase 2 Community Games (Pick 5, Fantasy Sets, Jamble) or Analytics deep-dives when the user returns.
