# Daily Pipeline CI Fix

## Goal

- Diagnose and fix the daily pipeline failures from the 2026-04-25 scheduled run.

## Constraints

- Never work on `main` directly.
- Run quality gates before shipping.
- Keep artifact action versions aligned across all workflows.

## Root Cause

Commit `b909a29` ("Split prediction storage and retained metrics") bumped
`actions/upload-artifact` from `@v7` to `@v8`. The `upload-artifact` action has
no `v8` major tag (latest is `v7.0.1`), so all 6 band matrix jobs failed
instantly with `Unable to resolve action actions/upload-artifact@v8`.

A second issue emerged after the first fix: Fantasy Goose uses
`actions/download-artifact@v8` to read artifacts uploaded by
`actions/upload-artifact@v7`. Cross-version artifact access silently fails with
"Artifact not found", causing Fantasy Goose to skip playing.

## Commands Run

```bash
gh run view 24938590915 --json jobs
gh run view 24938590915 --log
gh api repos/actions/upload-artifact/releases/latest --jq '.tag_name'
uv run pytest tests/pipeline/test_run_optimized_pipeline.py -v
npm run verify:python
npm run verify:docs
```

## Files Changed

- `.github/workflows/daily-pipeline.yml`:
  - `upload-artifact@v8` -> `@v7` (lines 485, 493) — PR #78
  - `download-artifact@v8` -> `@v7` (line 623) — PR #79
- `.github/workflows/fantasy-goose.yml`:
  - `download-artifact@v8` -> `@v7` (line 37) — PR #79

## Validation

- `npm run verify:python`: 340 passed, 6 skipped
- `npm run verify:docs`: clean build
- Re-triggered daily pipeline: 6/6 bands succeeded
- Fantasy Goose triggered automatically after pipeline and succeeded

## Merged PRs

- #78: `fix(ci): revert upload-artifact to v7`
- #79: `fix(ci): align download-artifact to v7 to match upload-artifact`

## Next Step

- Consider adding a CI drift test that asserts all `upload-artifact` and
  `download-artifact` references across workflows share the same major version,
  since the playbook lesson at line 114 documents the cross-version
  incompatibility but the repo has no automated enforcement.
