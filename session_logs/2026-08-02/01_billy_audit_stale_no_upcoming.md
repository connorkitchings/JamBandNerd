# Billy Daily Pipeline — Audit Stale Without Upcoming Show

## Goal

- Close out the Billy daily-pipeline failure thread. After #190 (prediction gate) and #191 (Livewire scraper), the scheduled Billy job was still failing on the Audit Website Supabase Tables step.

## Constraints

- No DB schema, model behavior, or website API changes.
- Keep `npm run verify:python` and `npm run verify:docs` green.
- Do not work on `main`; feature branch off main.

## Diagnosis

Scheduled runs on 2026-07-30, 07-31, 08-01 all failed in the `Daily Pipeline - billy` job. The prediction gate (#190) was working — `Generate Predictions` was correctly skipped (`upcoming_soon=0`) — but the failure had **moved downstream** to `Audit Website Supabase Tables`:

```
Supabase audit failed with 1 blocker(s)
billy_fast_gbm_v12_gap_scaled_p50:canonical_predictions_stale
latest_prediction_age_hours: 95.93   (reference_date 2026-07-28, max_age 72h)
```

The audit's own `freshness` block already understood "no upcoming show -> live prediction not required" (it uses `_has_upcoming_show`), but the model-level `canonical_predictions_stale` blocker in `_derive_setlist_model_audit` fired purely on age (`audit_supabase_tables.py:255`). With Billy's regeneration intentionally idle, the stale prediction for the last show was wrongly flagged. `validate_prediction_tables.py` had the same latent pattern (its `Validate` step is workflow-gated on `has_upcoming_show`, so it wasn't surfacing, but the staleness check was equally inconsistent).

Root cause: a multi-layer freshness/audit stack where one validator (#190 gate + `check_supported_model_freshness`) learned the "no upcoming show" semantics but two others (`audit_supabase_tables`, `validate_prediction_tables`) did not.

## Fix

Gate the staleness check on `_has_upcoming_show` in both scripts, mirroring the existing `canonical_predictions_missing` guard and `check_supported_model_freshness.live_prediction_required`. With no upcoming show, regeneration is intentionally idle and the existing prediction for the last show is allowed to age.

- `scripts/audit_supabase_tables.py` — `canonical_predictions_stale` only fires when a fresh prediction is required.
- `scripts/validate_prediction_tables.py` — parallel fix for consistency (manual ops + defense in depth).

## Commands Run

```bash
# Branch off latest main
git checkout -b fix/billy-audit-stale-no-upcoming origin/main

# Verify on the branch
npm run verify:python   # 622 passed (619 baseline + 3 new), 10 deselected
npm run verify:docs     # exit 0
uv run black scripts/validate_prediction_tables.py scripts/audit_supabase_tables.py tests/test_audit_supabase_tables.py tests/test_validate_prediction_tables.py

# Ship + confirm
git push -u origin fix/billy-audit-stale-no-upcoming
gh workflow run daily-pipeline.yml --ref fix/billy-audit-stale-no-upcoming --raw-field band=billy
gh run watch 30767520325 --exit-status --interval 15   # job success, audit state=ok blockers=0
gh pr create ...   # -> PR #192
gh pr checks 192 --watch --interval 20                 # all green
gh pr merge 192 --merge --delete-branch
```

## Files And Artifacts

- Branch `fix/billy-audit-stale-no-upcoming` (merged via PR #192, deleted on merge).
- `scripts/audit_supabase_tables.py` — gated `canonical_predictions_stale` on `_has_upcoming_show`.
- `scripts/validate_prediction_tables.py` — parallel staleness fix.
- `tests/test_audit_supabase_tables.py` — 2 new tests: stale+upcoming blocks; stale+no-upcoming allows.
- `tests/test_validate_prediction_tables.py` — 1 new test: stale+no-upcoming allows.
- Confirmation dispatch: <https://github.com/connorkitchings/JamBandNerd/actions/runs/30767520325>.

## Validation

- `verify:python`: 622 passed (619 baseline + 3 new), 10 deselected.
- `verify:docs`: exit 0.
- Live `band=billy` dispatch on the branch: job `success`, `Supabase audit state=ok blockers=0`.
- Bonus: the dispatch also confirmed #191's Livewire scraper is now capturing Billy's fall tour in production (`upcoming_soon=4`, prediction regenerated for `2026-08-04`, `predictions: fresh age=0.0h`). The stale-prediction fix is covered by unit tests for the next no-upcoming-show window.

## Next Step

- The Billy failure thread is closed (root cause -> latent scraper -> downstream audit consistency). Tonight's scheduled run should be fully green; watch it to confirm.
- Three durable lessons captured in `.agent/PLAYBOOK.md` for this thread: (1) Livewire/SPA migrations break `requests`+BeautifulSoup scrapers silently, (2) a fix that moves a failure downstream isn't complete — every layer that checks the same condition needs the same semantics, (3) per-band upcoming-show source splits (UM `um_upcoming_shows` via Seated) must be reflected in any gate/validator that reads future shows.
