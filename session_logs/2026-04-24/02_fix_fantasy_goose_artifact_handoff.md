# Fix Fantasy Goose Silent Skip (Artifact Version Mismatch)

## Goal

Diagnose and fix why the Fantasy Goose workflow showed green but never submitted picks since Apr 20.

## Constraints

- Only CI workflow changes; no Python code modified
- Must align artifact action versions across workflows without breaking daily pipeline
- Working on feature branch, not main

## Root Cause

`actions/upload-artifact@v7` (daily-pipeline.yml) and `actions/download-artifact@v8` (fantasy-goose.yml) are incompatible for cross-workflow artifact downloads. The download fails with "Artifact not found" every time, the gate gracefully sets `should_play=false`, and the workflow exits green without playing.

The gate job was introduced in commit `731f605` (Apr 20) with `download-artifact@v8` from the start. It never once successfully downloaded the artifact — the last actual play was Apr 10 under the old no-gate workflow.

## Commands Run

```bash
gh run list --workflow fantasy-goose.yml --limit 30
gh run view <run-id> --log  # inspected runs 24907853610, 24854941863, 24798700404, 24675527288, 24583991194
gh run view 24907537858  # confirmed band-status-goose artifact exists in daily pipeline
git log --oneline --all --follow -- .github/workflows/fantasy-goose.yml
git log --oneline --all --follow -- .github/workflows/daily-pipeline.yml
git show bb2e83c -- .github/workflows/daily-pipeline.yml
git show 731f605 -- .github/workflows/fantasy-goose.yml
npm run verify:python   # 340 passed, 6 skipped
npm run verify:docs     # clean
npm run verify:web      # 11 passed, 11 skipped
```

## Files And Artifacts

- `.github/workflows/daily-pipeline.yml` — bumped `upload-artifact` from v7 to v8 (lines 513, 521)
- Branch: `fix/fg-upload-artifact-v8` (commit `17f22f4`)
- No docs changes needed — `docs/operations/github_actions.md` already describes the gate architecture accurately

## Validation

- `npm run verify:python`: 340 passed, 6 skipped
- `npm run verify:docs`: clean build
- `npm run verify:web`: 11 passed, 11 skipped
- No Python code changed; CI-only diff

## Next Step

Merge the branch. Tonight's 19:00 UTC daily pipeline run will produce v8 artifacts; the subsequent Fantasy Goose run should pass the gate and play.
