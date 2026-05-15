# Session 02: Pre-Merge Planning and Cleanup

## Goal

Organize the pre-merge state of `feat/single-model-per-band` (formerly
`feat/three-stage-forecasting`): fix formatting, update stale docs, rename the
branch, and document decisions before returning to Billy Strings model work.

## Constraints

- Do not touch `dev`, `fix/weekly-correction-sweep`, or other unrelated branches.
- Keep experiment code (Phish/Goose/Billy experiments, ablation, distilled) in
  the branch for now — strip before merge to main.
- Do not promote WSP or UM fast predictors yet (planned for merge-prep phase).

## Decisions Recorded

1. **Experiment code**: Keep in branch for future iteration; strip before merge.
2. **Merge strategy**: Squash to 1 meaningful commit at merge time.
3. **Branch name**: Renamed from `feat/three-stage-forecasting` to
   `feat/single-model-per-band` to match ADR 0001.
4. **Stale branches**: `dev` and `fix/weekly-correction-sweep` left untouched;
   old local `feat/single-model-per-band` (19 commits, superseded) deleted.

## Per-Band Status Snapshot

| Band | Active Predictor | dual | Status |
|------|-----------------|------|--------|
| Phish | PhishFastPlusNotebookRankVenueRun | 0.419 | Promoted, pipeline-tested |
| Goose | GooseFastRankPredictor | 0.409 | Promoted |
| Billy | BillyFastPredictorV3 | 0.377 | Promoted (V4/V5/V6 failed) |
| WSP | BaselinePredictor (Deal fallback) | ~0.408 | Fast predictor exists (0.434) but not registered |
| UM | BaselinePredictor (Deal fallback) | ~0.314 | Fast predictor exists (0.323) but not registered |

## Remaining Pre-Merge Checklist

- [ ] Promote WSP + UM fast predictors (registry + BAND_METADATA + tests)
- [ ] Run pipeline for WSP + UM end-to-end
- [ ] Strip unpromoted experiment code before merge
- [ ] Full quality gate: `npm run verify:clean`
- [ ] Open PR, review, squash-merge to main

## Commands Run

```bash
uv run black src/jambandnerd/ tests/ scripts/
git add -A && git commit -m "chore: fix Black formatting across 15 files"
git branch -D feat/single-model-per-band
git branch -m feat/single-model-per-band
git push origin -u feat/single-model-per-band
```

## Files Changed

- 15 source/test/script files: Black formatting only
- `docs/user/pipeline_usage.md`: window 100→50, removed nonexistent script ref
- `docs/contributor/developer_guide/architecture.md`: removed replay.ts/venues.ts/model-agreement refs, window 100→50, removed nonexistent script ref
- `docs/operations/github_actions.md`: three window 100→50 fixes, last-100→last-50
- `README.md`: fixed Dynamic Matrix description, window 100→50

## Validation

- `uv run black --check src/jambandnerd/ tests/ scripts/` -> 0 files would reformat (was 15)
- Doc references manually verified against actual codebase

## Next Step

Resume Billy Strings model iteration. Current active model is
`BillyFastPredictorV3` (dual=0.377). V4 (HP tuning), V5 (25 features), and V6
(early stopping) all regressed. Need to identify next experiment direction.
