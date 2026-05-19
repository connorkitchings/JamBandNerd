# Session Log: V1 Site Punch List Completion

Date: 2026-05-18

## Goal

Implement the full 37-item V1 website punch list and prepare a local deployment handoff only. No push, PR, merge, hosted smoke, or production deployment.

## Summary

- Addressed the accessibility blockers: visible focus states, expandable-panel ARIA state/control wiring, mobile select label association, mobile homepage CTAs, song-search no-results feedback, and `DataState` heading-level control.
- Removed implicit server env serialization into the live tracker. Client-side realtime now uses explicit `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`, with a singleton Supabase browser client.
- Added app-level `loading.tsx`, `error.tsx`, and `not-found.tsx` surfaces.
- Consolidated song normalization and Top-K hit/recall helpers in `song-board-core`, reused by replay and last-show, and added unit coverage.
- Cleaned UX and polish items across prediction copy, prediction hero venue priority, mobile song truncation, last-show Top-10/25/50 metrics, chart sizing/computation, performance aggregation, setlist layout, contact copy, FAQ default state, and dead CSS.
- Moved the `@/lib/data` facade from `lib/data.ts` to `lib/data/index.ts` and removed the naming collision.
- Extracted shared band pill rendering into `BandPillGrid`.
- Removed empty preview route directories.
- Kept `src/proxy.ts` because Next.js 16.2 prefers it; renaming to `middleware.ts` produced a deprecation warning.

## Follow-Up Correction

After the first local commit, the punch list was re-audited and three gaps were found:

- `DataGate` had not actually been extracted.
- `PredictionHero` still owned both show context and metric panel rendering.
- Heading hierarchy was improved but not guarded by a test.

Those gaps were closed in the follow-up patch: route status branches now use `DataGate`, prediction metrics are rendered through `PredictionHeroMetrics`, and public-shell smoke tests assert a single `<h1>` on public routes.

## Validation

- `npm run test:web:unit` — passed
- `npm run lint:web` — passed
- `npm run build:web` — passed
- `npm run test:web:smoke:list` — passed
- `npm run test:web:smoke` — passed
- `npm run verify:web` — passed
- `npm run verify:docs` — passed
- `npm run verify:clean` — passed

## Deployment Handoff

- Required Vercel env vars: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET`.
- Next recommended action: run the final local gate, then open a PR to `main` following `docs/operations/main_branch_elevation.md`.
- Hosted smoke was not run because no deployed URL was provided for this prepare-only pass.

## Final Review Adjustments

- Home, About, Data Use, and Contact are considered complete after local review.
- Homepage teaser order is fixed to Phish, WSP, BS, Goose while still reading Supabase display names for show context.
- Mobile homepage hero CTAs are hidden because the permanent bottom nav covers Predictions and Performance.
- Footer utility links now use a tinted chip treatment so About, Data Use, Contact, and Admin separate from the footer background.
- Prediction model performance now spans the same width as the Next Show and Song Board areas, with colored Avg. Hits and Coverage labels/values.
- Prediction song board mobile rows now show show gap, LTP date, Top-50 count, and a compact probability measurement bar.
- Prediction page review deferred non-Goose LTP display because the latest prediction payloads do not serialize LTP data for Phish, WSP, Billy, or UM.
- Performance page latest-show snapshot is compressed, centered, and labels single-show values as Hits instead of Avg. Hits.
- Performance page Recent Show Accuracy now dedupes repeated scored rows by `show_id`, falling back to show date and venue metadata when needed.
- Performance page Accuracy Over Time now separates Measure and Prediction Group controls and renders per-show dots with a flat period-average reference line instead of connecting points.
- Retained completed-show corpus contract is tightened to active model version plus the last 50 completed shows. The sync default is now 50, pruning removes stale model-version rows, and the website filters performance reads to the latest generated model version.

## Open Model Issue

- Goose probability calibration needs follow-up. The current next-show board can show impossible-looking probabilities, for example Hungersite at 100%. A displayed probability should not reach 100% for a song prediction, so the Goose model probability calculation or calibration layer needs investigation before treating those percentages as trustworthy.
- Prediction payload LTP coverage needs follow-up for non-Goose bands. Latest Supabase checks showed Goose has LTP in `setlist_predictions.predictions` and `setlist_prediction_songs.prediction_payload` (`25/25`), but Phish, WSP, Billy, and UM all showed `0/25` LTP coverage in latest prediction payloads. Raw/source data exists for Phish (`phish_songs_raw.last_played_date 964/964`), WSP (`wsp_songs_raw.last_played 709/710`), and Billy (`billy_songs_raw.last_played 1031/1480`), so this is likely a prediction generation/serialization gap rather than a mobile UI issue. UM `um_songs_raw` does not expose a last-played column and may need transform-derived LTP from setlists. Deferred for now; return after V1 review.

## End Session Wrap-Up

### Goal

Pause the V1 review after the Predictions and Performance page refinements, update the handoff notes, and commit the local work.

### Constraints

- Do not push, open a PR, merge to `main`, run hosted smoke, or deploy.
- Preserve the local `dev` branch workflow and keep V1 deployment as a handoff-only state.

### Files Changed

- Website review changes across homepage, predictions, replay, performance, chart controls, mobile song board rows, footer utility links, and accuracy/replay table linking.
- Retained completed-show corpus contract updated in scripts, docs, model metadata, audit defaults, and database pruning helpers.
- Billy V12 model/test updates present in the worktree were included in the final validation and commit.
- New component: `apps/web/src/components/chart-metric-toggle.tsx`.

### Commands Run

- `npm run verify:web`
- `npm run verify:docs`
- `uv run ruff check scripts/sync_retained_prediction_corpus.py scripts/audit_supabase_tables.py src/jambandnerd/db/operations.py src/jambandnerd/models/metadata.py src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py`
- `uv run ruff check --fix tests/models/test_billy_model.py`
- `uv run pytest -q tests/models/test_billy_model.py`

### Validation Status

- Web verification passed, including unit tests, smoke list, lint, build, and smoke tests.
- Docs strict MkDocs build passed.
- Ruff passed after import cleanup in `tests/models/test_billy_model.py`.
- Billy model tests passed (`34 passed`).

### Next Step

Continue the V1 review from the Replay page, then run the final local deployment gate before opening a PR to `main`.
