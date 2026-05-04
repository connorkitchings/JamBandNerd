# Session 2026-05-02/04 — WSP Daily Pipeline Hotfix

## Goal

Fix two consecutive prod daily pipeline failures (May 1-2) for WSP band.

## Root Cause Analysis

Two distinct bugs caused the failure:

1. **`status.py` hard-fail on EC unreachable**: When EverydayCompanion is unreachable for a recent show's setlist (Cloudflare blocking the diagnostic probe), `outcome_code()` returned `failed_upstream_stale` unconditionally — even though the collector had gathered 708 songs and 74 shows from other pages. This caused 3 retry attempts and a hard pipeline failure. The dev branch already had the fix (degraded-upstream-stale escape hatch) but it hadn't been promoted to main.

2. **`panicstream.py` single-set detection gap**: PanicStream's meta description for single-set festival shows (e.g. 4/30 Jazz Fest) has no set markers like "Set 1" or "Encore" — just comma-separated songs with `>` segues. The `_looks_like_setlist_text` guard rejected this format, so the fallback chain returned empty even though PanicStream had the data.

## Constraints

- Cherry-pick approach: minimal targeted fixes to `main`, not full dev promotion
- Every logic change needs tests
- Branch: `fix/wsp-degraded-upstream-stale` off `main`

## Commands Run

```bash
npm run verify:python   # 397 passed, 6 skipped, lint clean
uv run pytest tests/data_collection/test_wsp_orchestration.py tests/data_collection/wsp/test_panicstream.py -v
gh run view <run-id> --log --log-failed  # CI log analysis
gh pr create            # PR #93
```

## Files Changed

- `src/jambandnerd/data_collection/wsp/status.py` — added degraded-upstream-stale escape hatch (5 lines)
- `src/jambandnerd/data_collection/wsp/panicstream.py` — extended `_looks_like_setlist_text` to accept text with 4+ song separators and no set markers
- `tests/data_collection/test_wsp_orchestration.py` — added `TestCollectionStatusOutcomeCode` (6 tests)
- `tests/data_collection/wsp/test_panicstream.py` — added `test_parse_single_set_festival_from_meta_description`

## Validation Status

- `npm run verify:python`: 397 passed, 6 skipped, lint clean
- `npm run verify:docs`: not run (no doc changes)
- `npm run verify:web`: not run (no web changes)
- PR #93 CI: Repo Quality passed, Website Quality passed

## PR

https://github.com/connorkitchings/JamBandNerd/pull/93

## Next Step

Merge PR #93, then re-run the daily pipeline via `workflow_dispatch` to verify both fixes work end-to-end. The PanicStream fix should populate the 4/30 setlist, making WSP predictions fresh and clearing the 48h freshness enforcement gate. After that, promote the full dev branch (PR #91) with diagnostic logging and other improvements.
