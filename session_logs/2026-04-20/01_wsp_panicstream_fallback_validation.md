# WSP PanicStream Fallback And Validation

**Goal:** Add PanicStream ahead of TourWrangler for recent WSP setlist gaps, preserve hard-fail behavior for unresolved recent completed shows, and validate the fix against the April 17-18, 2026 CI failure mode.
**Constraints:** Keep Everyday Companion as primary, keep TourWrangler as a final fallback, avoid relaxing CI policy, and preserve downstream WSP raw-row contracts.
**Validation Status:** Passed. Focused WSP tests passed locally (`41 passed`). Full Python verification passed locally via `npm run verify:python` (`314 passed, 6 skipped`). Docs verification passed locally via `npm run verify:docs`. Isolated orchestration validation for `2026-04-17` and `2026-04-18` confirmed PanicStream-first selection, TourWrangler fallback when needed, `failed_upstream_stale` when all sources are empty, and no `has_errors()` logging regression.

## Actions Taken
- Deleted merged local branches `audit-supabase-framework` and `pr53-blackfix`, started `codex/wsp-ci-panicstream-fallback` from `dev`.
- Inspected the failed `Daily Data Pipeline` GitHub Actions runs from `2026-04-18` and `2026-04-19` and confirmed the WSP failures were recent-gap EC request failures on `2026-04-17` and `2026-04-18` with empty TourWrangler fallback.
- Verified PanicStream exposes current WSP year-index pages and parseable show-page setlist content for the failing April 2026 dates.
- Added a dedicated WSP PanicStream adapter and a shared recent-gap fallback resolver ordered `panicstream -> tourwrangler`.
- Updated recent-gap diagnostics, recent fallback insertion, EC-over-fallback promotion, and WSP status logging to use the shared resolver and current `CollectionStatus.workflow_state()` API.
- Added PanicStream fixtures and tests plus orchestration/regression coverage for fallback ordering, hard-fail semantics, and the fixed logging path.
- Updated the WSP operations runbook to document the current recent-gap fallback chain.

## Commands Run
- `gh run list --workflow \"Daily Data Pipeline\" --limit 10`
- `gh run view 24611934610 --log-failed`
- `gh run view 24637005978 --log-failed`
- `git branch --merged dev`
- `git branch -d audit-supabase-framework pr53-blackfix`
- `git checkout dev`
- `git checkout -b codex/wsp-ci-panicstream-fallback`
- `curl -sS https://www.panicstream.com/vault/category/2026/`
- `curl -sS https://www.panicstream.com/vault/widespread-panic-04-17-2026-birmingham-al/`
- `uv run pytest -q tests/data_collection/wsp/test_panicstream.py tests/data_collection/wsp/test_wsp_html_parsing.py tests/data_collection/test_wsp_orchestration.py tests/data_collection/test_wsp_collector.py tests/data_collection/wsp/test_status.py tests/pipeline/test_band_collection_regressions.py`
- `npm run verify:python`
- `npm run verify:docs`
- `uv run python -c '...isolated WSP orchestration validation for 2026-04-17/2026-04-18...'`

## Files Changed
- `src/jambandnerd/data_collection/wsp/panicstream.py`
- `src/jambandnerd/data_collection/wsp/orchestration.py`
- `src/jambandnerd/data_collection/wsp/status.py`
- `tests/data_collection/wsp/test_panicstream.py`
- `tests/data_collection/wsp/fixtures/panicstream_show_single_set.html`
- `tests/data_collection/wsp/fixtures/panicstream_show_two_set.html`
- `tests/data_collection/wsp/fixtures/panicstream_year_2026.html`
- `tests/data_collection/test_wsp_orchestration.py`
- `tests/data_collection/test_wsp_collector.py`
- `tests/data_collection/wsp/test_status.py`
- `tests/pipeline/test_band_collection_regressions.py`
- `docs/operations/tourwrangler_fallback.md`
- `docs/index.md`
- `.agent/PLAYBOOK.md`

## Next Step
- Review the branch diff, commit the PanicStream fallback work, and push `codex/wsp-ci-panicstream-fallback` so it can be merged back to `dev` and exercised in GitHub Actions before the `main` PR.
