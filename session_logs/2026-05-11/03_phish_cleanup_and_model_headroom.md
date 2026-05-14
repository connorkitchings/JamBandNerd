# Session 03 - Phish Cleanup Ablation + Model Headroom

**Date**: 2026-05-11  
**Branch**: `feat/wsp-combo-sweep`

## Goal

Return to model work without restarting broad Phase B feature/HP sweeps. Add a
narrow Phish cleanup ablation, preserve the registered production baselines, and
create a reusable offline headroom report for deciding future architecture work.

## Changes

- Registered `cleanup_ablation` in `PHISH_SWEEPS`, pointing to the existing
  `PhishFastPredictorV3` cleaned-feature experiment.
- Added tests that keep `cleanup_ablation` experiment-only and verify the V3
  feature set drops `plays_past_10`, `month_play_rate`, and sparse same-venue
  prior-play count/share features.
- Added `scripts/report_model_headroom.py`, an offline report over existing
  `backtests/*_summary.json` and per-show JSONL artifacts.
- Wrote `diagnostics/model_headroom_report.md` and
  `diagnostics/model_headroom_report.json`.
- Updated model-development docs with the current Phase B follow-up policy:
  Phish cleanup first, Goose architecture only with diagnostics support, WSP and
  Billy held for upstream recovery, UM held unless production drift appears.

## Results

### Phish incumbent

Command:

```bash
uv run python scripts/run_phase_b_backtest.py --band phish --predictor jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun --shows 100 --snapshot-root .snapshots/phish_phase_b
```

Metrics:

| model | n | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `phish_fast_gbm_v2_feat_notebook_rank_venue_run` | 99 | 0.4186 | 0.2929 | 0.2453 | 0.5442 | 0.2831 |

### Phish cleanup ablation

Command:

```bash
uv run python scripts/run_experiment.py --band phish --sweep cleanup_ablation --shows 100 --snapshot-root .snapshots/phish_phase_b
```

Metrics:

| model | n | dual | p@10 | p@25 | r@50 | F1@25 | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `phish_fast_gbm_v3` | 99 | 0.4094 | 0.2798 | 0.2436 | 0.5390 | 0.2811 | no promotion |

The cleanup ablation misses the gate: F1@25, p@25, and dual all regress versus
the registered incumbent. The registry remains unchanged.

## Validation

```bash
uv run pytest -q tests/models/test_phish_model.py tests/scripts/test_report_model_headroom.py
uv run ruff check src/jambandnerd/models/phish/experiments.py tests/models/test_phish_model.py scripts/report_model_headroom.py tests/scripts/test_report_model_headroom.py docs/contributor/model_development.md
```

Both passed.

## Next Step

Do not continue Phish cleanup sweeps. Use `diagnostics/model_headroom_report.md`
as the next model triage artifact. Before any architecture spike, fill missing
registered-baseline summaries for Goose and UM or regenerate the report from a
fresh complete backtest set.

## Follow-Up: Goose + UM Baseline Artifact Repair

The exact registered Goose and UM baseline artifacts were regenerated from local
snapshots so the headroom report no longer has `n/a` rows.

Commands:

```bash
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseFastRankPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_phase_b_backtest.py --band um --predictor jambandnerd.models.um.fast_predictor.UMFastPredictorV2 --shows 100 --snapshot-root .snapshots/um_phase_b
uv run python scripts/report_model_headroom.py --backtests-dir backtests --out-dir diagnostics
```

Metrics:

| band | model | n | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Goose | `goose_fast_rank_v1` | 100 | 0.4087 | 0.2740 | 0.2164 | 0.5433 | 0.2801 |
| UM | `um_fast_gbm_v2` | 100 | 0.3431 | 0.1990 | 0.1704 | 0.4872 | 0.2137 |

Revised interpretation:

- Goose remains the only plausible architecture-spike candidate, but only after
  reading the completed worst-show segments and confirming an actionable miss
  pattern.
- UM stays hold/monitor. The regenerated V2 artifact confirms the documented
  Phase B gain over V1, and there is no reason to restart UM sweeps unless
  production drift appears after the schema-sync fixes.

## Follow-Up: Goose Architecture Triage

The registered Goose predictor diagnostic pass completed from the local Phase B
snapshot.

Command:

```bash
uv run python scripts/diagnose_phase_b_features.py --band goose --predictor jambandnerd.models.goose.model.GooseFastRankPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b
```

Artifacts:

- `.snapshots/goose_phase_b/diagnostics/goose_goose_fast_rank_v1_100shows.md`
- `.snapshots/goose_phase_b/diagnostics/goose_goose_fast_rank_v1_100shows.json`

Feature diagnostics show the core recency/rank signals are healthy:
`plays_past_50`, `notebook_rank_score`, `plays_past_year`,
`plays_past_25`, `current_gap`, and `avg_ltp_recent` all have coherent lift.
`plays_past_3` is always zero under the current exclusion policy, and venue/run
context is weak, but there is no broad “dead feature cleanup” path analogous to
Phish.

Worst-show decomposition:

| show | context | actual | top-50 hits | candidate-missing actuals | ranked below 50 |
| --- | --- | ---: | ---: | ---: | ---: |
| `1745515491` / 2025-07-25 | Newport, Not Part of a Tour | 4 | 0 | 3 | 1 |
| `1754580823` / 2025-08-15 | World Cafe Live, Not Part of a Tour | 8 | 0 | 7 | 1 |
| `1737731867` / 2025-06-22 | Belleayre Mountain tour show | 12 | 5 | 4 | 3 |

The missing-candidate pattern is actionable. Many missed actual songs were
filtered by the strict recent-song exclusion (`gap < 3`) despite being played
again on short or special shows; two songs on the World Cafe Live show were
never seen in prior Goose history. This points to a Goose architecture/candidate
policy problem for atypical short shows and same-run repeats, not a generic
LightGBM feature/HP sweep opportunity.

Decision: a separate Goose architecture spike is justified, scoped narrowly to
candidate policy / short-show handling and measured against the Notebook floor.
Do not resume broad Goose feature or hyperparameter sweeps.

## Follow-Up: Goose Candidate-Policy Architecture Spike

The Goose candidate-policy spike added protected hooks on the fast predictor so
experiments can vary candidate eligibility without duplicating the full model:

- `_candidate_recent_gap_floor(target_show_context)` defaults to the current
  `exclusion_window`.
- `_candidate_min_plays(target_show_context)` defaults to the current
  `min_plays_threshold`.
- `target_show_context` now controls both training-frame eligibility and live
  prediction eligibility.

Experiment-only candidates were registered under `candidate_policy_sweep`:

- `candidate_relaxed_special`: allow immediate repeats only for `Not Part of a
  Tour` Goose targets.
- `candidate_relaxed_global`: allow immediate repeats for all Goose targets as a
  risk-control variant.
- `candidate_minplay1_special`: lower prior-play threshold to 1 only for `Not
  Part of a Tour` Goose targets.

Commands:

```bash
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseNotebookFloorPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseFastRankPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_experiment.py --band goose --sweep candidate_policy_sweep --shows 100 --snapshot-root .snapshots/goose_phase_b
```

Aggregate results:

| model | n | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `goose_notebook_floor_v1` | 100 | 0.408 | 0.284 | 0.216 | 0.531 | 0.279 |
| `goose_fast_rank_v1` | 100 | 0.409 | 0.274 | 0.216 | 0.543 | 0.280 |
| `goose_fast_rank_v1_candidate_relaxed_special` | 100 | 0.439 | 0.277 | 0.229 | 0.601 | 0.297 |
| `goose_fast_rank_v1_candidate_relaxed_global` | 100 | 0.477 | 0.277 | 0.239 | 0.677 | 0.311 |
| `goose_fast_rank_v1_candidate_minplay1_special` | 100 | 0.408 | 0.273 | 0.217 | 0.542 | 0.281 |

Targeted worst-show check:

| show | baseline top-50 hits | special-relaxed top-50 hits | global-relaxed top-50 hits | minplay-only top-50 hits |
| --- | ---: | ---: | ---: | ---: |
| `1745515491` / 2025-07-25 Newport, Not Part of a Tour | 0 / 4 | 3 / 4 | 3 / 4 | 0 / 4 |
| `1754580823` / 2025-08-15 World Cafe Live, Not Part of a Tour | 0 / 8 | 5 / 8 | 5 / 8 | 0 / 8 |
| `1737731867` / 2025-06-22 Belleayre tour show | 5 / 12 | 5 / 12 | 7 / 12 | 5 / 12 |

Interpretation:

- The spike confirms the prior diagnosis: strict recent-repeat exclusion is the
  main candidate-set failure for short/special Goose shows. Lowering the prior
  play threshold does not address the misses.
- The special-show policy improves dual, p@25, r@50, and F1@25 while repairing
  the two worst `Not Part of a Tour` misses.
- The global relaxed control performs best on aggregate, including the Belleayre
  tour show, but that broader win is exactly the leakage/noise-risk signal this
  spike was meant to isolate.
- No variant clears the full promotion gate because p@10 remains below the
  Notebook floor (`0.277` vs `0.284`).

Decision: do not promote or registry-wire a challenger. The next Goose work, if
continued, should be a second architecture spike that preserves top-10 precision
while selectively repairing candidate-set misses, starting from the special-show
recent-repeat policy rather than global relaxation.

## Follow-Up: Goose Rank-Guard Candidate Spike

The second Goose spike kept the candidate-policy repair but added a Notebook
top-10 rank guard so the board preserves the simple rule-based precision floor
while filling ranks 11-50 from the relaxed candidate model. These remain
experiment-only classes and are registered only under
`candidate_rank_guard_sweep`.

Commands:

```bash
uv run python scripts/run_experiment.py --band goose --sweep candidate_rank_guard_sweep --shows 100 --snapshot-root .snapshots/goose_phase_b
```

Aggregate results:

| model | n | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `goose_notebook_floor_v1` | 100 | 0.408 | 0.284 | 0.216 | 0.531 | 0.279 |
| `goose_fast_rank_v1` | 100 | 0.409 | 0.274 | 0.216 | 0.543 | 0.280 |
| `goose_fast_rank_v1_candidate_relaxed_special_nbtop10` | 100 | 0.443 | 0.284 | 0.228 | 0.602 | 0.296 |
| `goose_fast_rank_v1_candidate_relaxed_global_nbtop10` | 100 | 0.480 | 0.284 | 0.240 | 0.677 | 0.312 |

Targeted worst-show check:

| show | baseline top-50 hits | special guarded top-50 hits | global guarded top-50 hits |
| --- | ---: | ---: | ---: |
| `1745515491` / 2025-07-25 Newport, Not Part of a Tour | 0 / 4 | 3 / 4 | 3 / 4 |
| `1754580823` / 2025-08-15 World Cafe Live, Not Part of a Tour | 0 / 8 | 5 / 8 | 5 / 8 |
| `1737731867` / 2025-06-22 Belleayre tour show | 5 / 12 | 5 / 12 | 7 / 12 |

Interpretation:

- The Notebook top-10 guard fixes the prior promotion blocker: p@10 returns to
  the Notebook floor (`0.284`) while the special-show candidate repair keeps
  most F1@25 and recall gains.
- `candidate_relaxed_special_nbtop10` is the cleanest follow-up candidate
  because its eligibility change is scoped to the diagnosed `Not Part of a Tour`
  failures and it beats both the registered Goose fast model and Notebook floor
  on dual, p@25, r@50, and F1@25.
- `candidate_relaxed_global_nbtop10` is the best aggregate variant, but it
  changes all targets and should remain a diagnostic/control result until tour
  show degradation and leakage/noise risk are reviewed.

Decision: still no automatic registry change in this session. The next Goose
step should be a promotion-readiness review for
`candidate_relaxed_special_nbtop10`: compare normal-vs-special segments,
inspect top-10 song churn, and decide whether the Notebook top-10 guard is an
acceptable production architecture or just an offline ranking patch.

## End Session Wrap-Up

Goal: preserve the branch's production-readiness fixes, complete the Phish
cleanup/headroom pass, repair Goose/UM baseline evidence, and run a Goose-only
candidate-policy architecture spike without broad feature or HP sweeps.

Constraints:

- Stayed on `feat/wsp-combo-sweep`.
- Used local snapshots only for model work.
- No Supabase writes.
- No model registry promotion or production wiring for Goose challengers.

Validation run:

```bash
uv run pytest -q tests/models/test_goose_model.py tests/scripts/test_report_model_headroom.py
uv run ruff check src tests scripts
npm run verify:docs
npm run verify:python
```

Status: all validation passed. Final `verify:python` result was `613 passed, 6
skipped`.

Files changed / artifacts produced:

- Branch docs/session logs for upstream blockers, single-model production
  rollover, Phish cleanup/headroom, Goose candidate-policy diagnostics, and
  Goose rank-guard diagnostics.
- Supabase contract migration and docs for `setlist_prediction_songs`
  projection metadata.
- Web prediction selection/live-update handling for target-show-date based
  next/tonight/previous state.
- UM collection/schema-sync and extra-column upsert handling.
- Phish cleanup experiment scaffolding and diagnostics artifacts.
- Goose candidate-policy hooks, experiment-only sweeps, rank-guard variants,
  and focused tests.

Next step: run a Goose promotion-readiness review for
`candidate_relaxed_special_nbtop10`, with normal-vs-special segment comparison
and top-10 churn review before any registry change.
