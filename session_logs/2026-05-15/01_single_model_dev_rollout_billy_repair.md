# Session Log: Single-Model Dev Rollout Billy Repair

## Summary
- Continued the single-model rollout after `feat/single-model-per-band` was merged into `dev`.
- Verified the dev Vercel deployment for the retained public route shape:
  - `/`
  - `/predictions?band=goose`
  - `/performance?band=goose`
  - `/last-show?band=goose`
  - `/compare`, `/replay`, and `/explorer` return 404.
- Confirmed the live `bands` registry exposes only the active rollout bands: `billy`, `goose`, `phish`, `um`, and `wsp`.
- Triggered the post-merge dev daily pipeline. Goose, Phish, UM, and WSP passed; Billy failed during collection on a `billy_songs_raw_song_uuid_idx` duplicate-key conflict.

## Billy Fix
- Added Billy song label reconciliation before upserting `billy_songs_raw`.
- When bmfsdb keeps a stable `song_uuid` but changes only the scraped song label, the collector updates the existing row by UUID before the normal `song_name` upsert.
- When the desired scraped label is already owned by another UUID, the collector preserves the existing label for the stable UUID and recomputes the row `source_hash` so the upsert remains idempotent and does not collide with the unique `song_name` index.
- Added regression coverage for:
  - safe UUID-based label changes;
  - contested label changes where another UUID already owns the desired `song_name`.

## Verification
- `uv run ruff check scripts/run_billy_collection.py tests/pipeline/test_band_collection_regressions.py`
- `uv run pytest -q tests/pipeline/test_band_collection_regressions.py`
- `uv run python scripts/run_billy_collection.py --skip-setlists`
  - Completed successfully against the configured Supabase data.
  - Preserved `Miss the Mississippi and You` for UUID `955a5c50-9783-40d6-91ec-d8e45f938fbb` because `Miss The Mississippi And You` is already owned by UUID `a12143ec-cce8-4ca7-b71e-7c0cbafad7c6`.
- `npm run verify:python`
  - `627 passed, 6 skipped`.

## Next Gate
- Commit and push the Billy repair to `dev`.
- Rerun the dev daily pipeline for Billy, then run an all-band dev dispatch before promoting `dev` to `main`.
