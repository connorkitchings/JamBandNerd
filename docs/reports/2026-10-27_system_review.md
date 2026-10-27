# 2026-10-27 System Review: Findings Backlog

A review of the data pipeline, prediction system and website after a long gap. The confirmed bugs were fixed in the same session (see `session_logs/2026-10-27/01.md`). This page records the larger items that were deliberately deferred.

## Pipeline duplication

The daily workflow (`.github/workflows/daily-pipeline.yml`) and `scripts/run_optimized_pipeline.py` diverge in flags, retries and freshness gating. Plan one `run_band_pipeline` entrypoint, and move the roughly 150 lines of inline Python in `daily-pipeline.yml` into tested scripts.

## Unused band policies

`src/jambandnerd/config/bands.py` policy fields (`rolling_window_days`, `skip_existing_setlists`, the verify-only paths) are not read by the collectors. Wire them up or delete them.

## Atomic prediction-board replace

`replace_setlist_prediction_projection` (`db/operations.py:417-449`) deletes and re-inserts the board without a transaction. Build a transactional RPC, following the pattern of `replace_show_setlist` (migration `20261027000000`).

## Fragile IDs

- Billy matches shows by date plus venue.
- UM and WSP assign max+1 IDs, which can race.
- WSP falls back to `next_id=1`.
- Billy `collect_songs` returns `[]`.
- `_assign_show_ids` is unpaginated.

## Website caching

`revalidate=3600` has no effect: each page renders per request with about 10 queries. Consider `unstable_cache` or `"use cache"` with per-band tags, plus pipeline-triggered `revalidateTag`.

## Band metadata

Move per-band schema details (setlist table, position and set columns, venue column style) into the `bands` table, and remove the hardcoded branches and the teaser band list from the frontend. The correction sweep now carries its own per-band column mapping, which is another copy to fold in.

## Admin hardening

- Add a login rate limit and session revocation.
- Add CSP and HSTS headers.
- Admin routes still trust a client-supplied `showId` without checking it belongs to the band.

## Model code health

- Split the 1.7k-line `billy/fast_predictor.py` and the other experiment-heavy files into a registered class plus an `experiments.py`.
- Move the shared context-feature code into `models/shared/` (started with `venue_context.py`).
- Make LightGBM fully deterministic.
- Make `reference_date` storage consistent: backtests store target minus one day, live stores the target. `get_evaluation_reference_date` survives only to keep that label stable.
- `--exclusion-window` does nothing for four bands.
- Billy's song catalog query in `__init__` is unpaginated.
- The missing-setlist guard can block predictions for up to 7 days.
- `col_venues` is still computed in the phish, billy and um matrix caches but no longer read there.
- Experiment-variant subclasses (`WSPFastVenueRun`, `UMFastPredictorV2VenueRun`, `BillyFastV10*`) have no direct parity tests.

## Package imports

The package is imported two ways (`src.jambandnerd` in 32 files vs `jambandnerd` in 64), which creates two copies of each module. Tests that patch module attributes must patch both.

## Noise and false alarms

- WSP "DOM fingerprint mismatch" warnings fire on future 2027 show pages.
- The "stale accuracy" freshness warning fires for bands that are off tour.

Quiet both so real warnings stand out.

## Correction sweep follow-ups

- The shows, songs and venues tables still log "not implemented" and produce no corrections.
- Phish encore markers normalize to a null `set_number`, which is lossy.
- The wsp, billy, um and phish upstream adapters are tested only with fake collectors.
- Scheduled runs are dry-run. Flip them to live only after reviewing a manual `dry_run=true` run for every band.

## Stale docs

- `docs/reference/models/ckplus.md` is still in the mkdocs nav and linked from `docs/index.md`, though the CK+ code is gone.

## Unused web exports

`apps/web/src/lib/navigation.ts` (`NavItem`, `isDetailPath`), `show-status.ts` (`DAILY_INGESTION_CUTOFF_UTC_MINUTES`), `song-board-core.ts` (`SongBoardTier`, `SONG_BOARD_TIER_ORDER`), `admin/bands.ts` (`ADMIN_BAND_SLUGS`), `admin/session.ts` (`createAdminSessionToken`), plus barrel type exports with no consumers (`MissingSetlistShow`, `PredictionSnapshot`, `SetlistSnapshot`, `ShowDetails`).

## Unused scripts

Referenced only by their own file or by tests:

- `scripts/check_prediction_storage_rollout.py`
- `scripts/diagnose_goose_features.py`
- `scripts/wsp_failure_analysis.py`
- `scripts/admin/fix_wsp_duplicate_songs.py`
- `scripts/admin/delete_setlist_data.py`
- `scripts/admin/add_setlist.py`

Referenced only by `scripts/README.md` (and some tests):

- `scripts/check_recent_avg_gap.py` (marked legacy)
- `scripts/diagnose_phase_b_features.py`
- `scripts/report_goose_promotion_readiness.py`
- `scripts/evaluate_goose_notebook_blend.py`
- `scripts/run_goose_ablation.py`
- `scripts/run_notebook_ablation.py`
- `scripts/promote_phase_b_winner.py`
- `scripts/manual/data_quality_check.py`
- `scripts/manual/test_enhanced_collectors.py`
- `scripts/manual/goose/run_goose_transformations.py`
- `scripts/manual/validation/test_validation_comprehensive.py`
