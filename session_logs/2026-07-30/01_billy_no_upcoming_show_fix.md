# Billy Daily Pipeline — No Upcoming Show Fix

## Goal

- Diagnose why the `Daily Data Pipeline - billy` job failed on 2026-07-29 and ship a fix.

## Constraints

- Do not work directly on `main`. Use a feature branch.
- No database schema, model behavior, or website API changes.
- Keep `npm run verify:python` and `npm run verify:docs` green.
- No change to `scripts/generate_live_predictions.py` behavior (workflow-only fix).

## Diagnosis

Run `30484568049` (scheduled 2026-07-29) failed in the `Daily Pipeline - billy` job (`90686930730`).

Failure chain (from `gh run view --job 90686930730 --log-failed`):

1. Preflight: `[billy] mode=window_refresh execution=bounded_refresh run_collection=True recent_completed=5 missing_recent_setlists=2 upcoming_soon=0`.
2. Collection succeeded (`Upserted 27 rows into billy_setlists_raw`); the only data note was show_id=27105 (2026-07-24) missing its setlist upstream — informational, the `Alert on Data Issues` step just prints `::error::` and does not `exit 1`.
3. `Generate Predictions` ran because its gate was `should_run_collection == 'true' && workflow_state != 'degraded'` (both true).
4. `scripts/generate_live_predictions.py --band billy --require-output` raised `RuntimeError: [BILLY/billy_fast_gbm_v12_gap_scaled_p50] No upcoming show found; no live board written.` at `scripts/generate_live_predictions.py:164` and exited 1.
5. The exit 1 cascaded: backtest/accuracy steps were skipped (implicit `if: success()`), accuracy aged to 72h, and `Enforce Supported Model Freshness` escalated stale accuracy as a second `::error::`.

Root cause: a workflow-gate mismatch. `should_run_collection` fires on recent-completed-show activity, but `Generate Predictions --require-output` assumes a target show exists. Jul 28 passed only because `upcoming_soon=1` (a same-day Billy show). The downstream freshness auditor already understands this — it logged `predictions: fresh (no upcoming show; live prediction not required)` — but the upstream prediction step did not gate on the same condition. This affects any band in an off-tour window (Phish, Goose, etc.).

## Fix

Gate `Generate Predictions` and `Validate Prediction Tables` on the preflight `has_upcoming_show_soon` output (already computed by `scripts/collection_preflight.py`). Leave `Run Backtest and Save Per-Show Accuracy` ungated so per-show accuracy still regenerates and stays within the 48h freshness window.

## Commands Run

```bash
# Branch off latest main
git fetch origin main
git checkout -b fix/billy-no-upcoming-show-pipeline origin/main

# Edit (.github/workflows/daily-pipeline.yml, docs/operations/github_actions.md)
# then verify on the branch
npm run verify:python     # 611 passed, 10 deselected
npm run verify:docs       # exit 0
uv run pytest tests/test_daily_workflow_contract.py -q   # 5 passed

# Ship and confirm
git commit -m "fix(ci): idle predictions gracefully when a band has no upcoming show"
git push -u origin fix/billy-no-upcoming-show-pipeline
gh workflow run daily-pipeline.yml --ref fix/billy-no-upcoming-show-pipeline --raw-field band=billy
gh run watch 30545379994 --exit-status --interval 15
```

## Files And Artifacts

- `.github/workflows/daily-pipeline.yml` — added `&& steps.preflight.outputs.has_upcoming_show_soon == 'true'` to the `if:` of `Generate Predictions` (line 278) and `Validate Prediction Tables` (line 288). `Run Backtest and Save Per-Show Accuracy` (line 296) intentionally left ungated.
- `docs/operations/github_actions.md` — new subsection "Bands With No Upcoming Show (Idle Predictions)" under Daily Data Pipeline.
- Branch `fix/billy-no-upcoming-show-pipeline` (commit `b29eca7`).
- Confirmation run: <https://github.com/connorkitchings/JamBandNerd/actions/runs/30545379994> — `Daily Pipeline - billy` conclusion `success`.

## Validation

- `verify:python`: 611 passed, 10 deselected.
- `verify:docs`: docs build clean, exit 0.
- `test_daily_workflow_contract.py`: 5 passed (the `--require-output` command-line assertion at line 62 is unaffected — the command line itself did not change).
- Live confirmation run `30545379994` with `band=billy`: Billy preflight reported `upcoming_soon=0` (same condition as the failure), `Generate Predictions` was skipped, backtest ran, freshness audit reported `predictions: fresh (no upcoming show; live prediction not required)` and `accuracy: fresh (age=0.0h)`, `stale_prediction_models=none stale_accuracy_models=none`, job conclusion `success`.

## Next Step

- Open PR `fix/billy-no-upcoming-show-pipeline` -> `main`, watch CI, merge.
- Watch the next scheduled runs for Phish/Goose/UM off-tour windows to confirm the same idle-prediction path keeps them green.
- The pre-existing numbering gap in the "Steps per band" list in `docs/operations/github_actions.md` (jumps 6 -> 8) is out of scope here; fix separately if desired.
- The upstream lag on Billy 2026-07-24 (show_id 27105) is unrelated to this fix; it will age out of the recent window naturally.
