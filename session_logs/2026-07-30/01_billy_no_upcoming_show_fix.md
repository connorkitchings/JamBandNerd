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

## Follow-Up: Per-Band Future-Show Capture (Same Day)

The initial fix gated predictions on `has_upcoming_show_soon` (14-day window). A per-band investigation (see explore-agent findings) surfaced two problems with that signal and one latent collection gap:

1. **UM structural mismatch (would have broken UM predictions).** UM's `{um_shows_raw}` comes from allthings.umphreys.com (a setlist archive; future shows only). UM's real future-show source is Seated, written to a separate `um_upcoming_shows` table. The preflight only read `{band}_shows_raw`, so `has_upcoming_show_soon` was routinely false for UM. `scripts/generate_live_predictions.py` and `scripts/validate_prediction_tables.py` already special-cased UM with a Seated fallback; the preflight did not. Today (2026-07-30) Seated lists UM shows Aug 8/12/13/14/15 that the 14-day gate could not see.
2. **14-day window was the wrong signal.** `generate_live_predictions._resolve_next_show` looks for *any* future show (unbounded), so the gate was stricter than the script. WSP's next show (2026-08-14) sat 15 days out, so WSP predictions would have falsely idled.
3. **WSP year-boundary blind spot.** The default WSP window was `(current_year - 1, current_year)`, so next year's tours were invisible until Jan 1.

### Changes shipped (same branch)

- `scripts/collection_preflight.py`
  - New `CollectionPreflight.has_upcoming_show` field (unbounded; distinct from `has_upcoming_show_soon`).
  - `compute_band_preflight` short-circuits to `True` when the 14-day window already found a show; otherwise runs an unbounded `show_date >= today` (limit 1) existence check. For UM with no future `{um_shows_raw}` rows, falls back to `um_upcoming_shows` (`starts_at_local >= today`, limit 1), mirroring `scripts/validate_prediction_tables.py:51-77`.
- `.github/workflows/daily-pipeline.yml` (lines 278, 288): gate switched from `has_upcoming_show_soon` to `has_upcoming_show`.
- `scripts/run_wsp_collection.py`: extracted `default_wsp_year_window()` returning `(current_year - 1, current_year + 1)`. Safe because `wsp/collector.py:433-437` treats an unpublished `tour{YY+1}.asp` (404) as a soft skip.
- `docs/operations/github_actions.md`: rewrote the idle-predictions subsection to document both signals + the UM Seated fallback, and added a WSP window subsection.

### Tests added

- `tests/test_collection_preflight.py`: `has_upcoming_show` true when a future show is in raw; false when only past shows; UM Seated fallback fires when `{um_shows_raw}` is empty but `um_upcoming_shows` has a future row (the UM regression test).
- `tests/pipeline/test_run_wsp_collection.py`: `default_wsp_year_window()` extends into next year.

### Validation

- `verify:python`: 616 passed (611 baseline + 5 new), 10 deselected.
- `verify:docs`: exit 0.
- Live dispatches on `fix/billy-no-upcoming-show-pipeline` (all `success`):
  - UM run <https://github.com/connorkitchings/JamBandNerd/actions/runs/30547597954>: preflight `upcoming_soon=0` (allthings has no future shows), yet `Generate Predictions` ran via the Seated fallback and `Saved live next-show prediction for 2026-08-08`.
  - WSP run <https://github.com/connorkitchings/JamBandNerd/actions/runs/30547605845>: preflight `upcoming_soon=0` (next show 15 days out, outside the old 14-day window), yet `Generate Predictions` ran via the unbounded `has_upcoming_show` signal and `Saved live next-show prediction for 2026-08-14`. Collection now scans `2025-2027` (3 tour pages); `tour27.asp` 404-skip is graceful.
  - Billy run <https://github.com/connorkitchings/JamBandNerd/actions/runs/30547613707>: preflight `upcoming_soon=0`, `Generate Predictions` correctly skipped, freshness audit `predictions: fresh (no upcoming show; live prediction not required)`, accuracy fresh.

### Net behavior matrix

| Band | Future-show source | Prediction gate result |
| --- | --- | --- |
| billy | bmfsdb upcoming view -> `billy_shows_raw` | idle when no future show (correct) |
| goose | elgoose.net API -> `goose_shows_raw` | runs when API lists any future show |
| phish | phish.net API -> `phish_shows_raw` | runs when API lists any future show |
| um | Seated -> `um_upcoming_shows` (fallback) | runs when Seated lists any future show (fixed) |
| wsp | everydaycompanion.com -> `wsp_shows_raw`, now spanning next year | runs when any future show collected (fixed window + year-boundary) |
| eggy | thecarton.net API -> `eggy_shows_raw` | n/a (not in daily pipeline yet) |
