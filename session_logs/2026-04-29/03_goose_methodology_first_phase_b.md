# Goose Methodology-First Phase B

## Goal

- Implement the methodology-first Phase B plan for Goose model development:
  make blend evidence F1-aware, clarify promotion gate reporting, and update
  active methodology docs without changing Supabase schema, website contracts,
  or registry promotion.

## Constraints

- Keep F1 as offline promotion evidence for this slice.
- Do not promote `GooseGbmNotebookBlendPredictor` or change `models/registry.py`.
- Do not change the Goose blend default alpha unless a completed 100-show
  F1-aware sweep selects a different value.

## Commands Run

```bash
uv run ruff check scripts/evaluate_goose_notebook_blend.py scripts/promote_phase_b_winner.py src/jambandnerd/models/readiness.py tests/scripts/test_evaluate_goose_notebook_blend.py tests/models/test_dual_objective_metrics.py
uv run black --check scripts/evaluate_goose_notebook_blend.py scripts/promote_phase_b_winner.py src/jambandnerd/models/readiness.py tests/scripts/test_evaluate_goose_notebook_blend.py tests/models/test_dual_objective_metrics.py
uv run black scripts/evaluate_goose_notebook_blend.py scripts/promote_phase_b_winner.py src/jambandnerd/models/readiness.py tests/scripts/test_evaluate_goose_notebook_blend.py tests/models/test_dual_objective_metrics.py
uv run pytest tests/scripts/test_evaluate_goose_notebook_blend.py tests/models/test_dual_objective_metrics.py tests/models/test_goose_model.py -q
uv run python scripts/evaluate_goose_notebook_blend.py --band goose --base-predictor jambandnerd.models.goose.model.GooseGbmV2Predictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/blends
pkill -f scripts/evaluate_goose_notebook_blend.py
npm run verify:python
```

## Files And Artifacts

- `scripts/evaluate_goose_notebook_blend.py` now reports F1@10/@25/@50,
  dual F1, average actual set size, average p@25 ceiling, and an explicit
  F1-aware guarded alpha selector.
- `scripts/promote_phase_b_winner.py` now prints F1@25, p@25 guardrail,
  legacy p@10/r@50 thresholds, and dual-F1 deltas.
- `src/jambandnerd/models/readiness.py` exposes `p25_delta` in
  `PromotionDecision`.
- Active methodology docs now describe F1@25 as the Phase B offline promotion
  signal and p@25 as a product-facing/non-regression metric.

## Validation

- Targeted pytest: 30 passed.
- `npm run verify:python`: 451 passed, 6 skipped.
- The 100-show blend regeneration was started but stopped after show 21/100
  because the run was hour-scale with the current per-show GBM retraining path.
  No regenerated 100-show artifact was written in this session.

## Next Step

- Make `scripts/evaluate_goose_notebook_blend.py` resumable or faster before
  rerunning the full 100-show F1-aware sweep. Do not change Goose default alpha
  or registry promotion until that completed artifact selects a candidate and
  `scripts/promote_phase_b_winner.py` passes.

## Runtime Speedup Follow-Up

### Goal

- Make the Goose blend sweep resumable before further model tuning by caching
  alpha-independent per-show scoring evidence, then add opt-in parallel scoring
  for cold-cache runs.

### Files And Artifacts

- `scripts/evaluate_goose_notebook_blend.py` now supports:
  - per-show JSON cache records under
    `<out-dir>/.cache/<band>_<model_version>_<cache_key>/` by default;
  - `--cache-dir`, `--no-cache`, `--force-rebuild-cache`, and `--jobs`;
  - process-pool cold-cache scoring with parent-process atomic cache writes;
  - run metadata in JSON and Markdown reports for cache hits, misses, writes,
    selected cache directory, force rebuild state, and job count.
- `tests/scripts/test_evaluate_goose_notebook_blend.py` covers cache identity,
  cache round-trip reconstruction, cache-hit scorer skipping, force rebuild
  behavior, and stable ordering for out-of-order scoring results.
- Regenerated 100-show blend artifacts:
  - `.snapshots/goose_phase_b/blends/goose_goose_phase_b_v2_gbm_notebook_blend_100shows.json`
  - `.snapshots/goose_phase_b/blends/goose_goose_phase_b_v2_gbm_notebook_blend_100shows.md`

### Commands Run

```bash
uv run pytest tests/scripts/test_evaluate_goose_notebook_blend.py -q
uv run pytest tests/models/test_goose_model.py tests/models/test_dual_objective_metrics.py -q
uv run ruff check scripts/evaluate_goose_notebook_blend.py tests/scripts/test_evaluate_goose_notebook_blend.py
uv run black --check scripts/evaluate_goose_notebook_blend.py tests/scripts/test_evaluate_goose_notebook_blend.py
uv run python scripts/evaluate_goose_notebook_blend.py --band goose --base-predictor jambandnerd.models.goose.model.GooseGbmV2Predictor --shows 2 --snapshot-root .snapshots/goose_phase_b --out-dir /private/tmp/jbn_blend_speedup_probe --jobs 2
uv run python scripts/evaluate_goose_notebook_blend.py --band goose --base-predictor jambandnerd.models.goose.model.GooseGbmV2Predictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/blends --jobs 4
npm run verify:python
```

### Validation

- Two-show cold probe wrote cache; warm probe reported 2 cache hits, 0 misses,
  and 0 writes.
- Full 100-show cold `--jobs 4` sweep wrote 100 cache records plus a manifest.
- Full 100-show warm `--jobs 4` sweep reported 100 cache hits, 0 misses, and
  0 writes.
- Targeted blend tests: 10 passed.
- Targeted model/metric tests: 25 passed.
- `ruff` and `black --check` passed for the edited script and tests.
- `npm run verify:python`: 456 passed, 6 skipped.

### Evidence

- F1-aware guarded selector chose `alpha=0.00` on the completed 100-show sweep,
  which is pure Notebook evidence rather than a GBM blend promotion candidate.
- `alpha=0.00` metrics:
  - `p10=0.2840`
  - `p25=0.2156`
  - `f1_25=0.2790`
  - `r50=0.5311`
  - `dual_f1_score=0.2327`
  - average actual song count `13.19`
  - average p@25 ceiling `0.5276`
- No Goose default alpha, registry metadata, Supabase schema, or website
  contract changes were made.

### Next Step

- Do not promote the current GBM blend. Use the now-cached 100-show evidence to
  compare an offline RRF path or diagnose why the GBM contribution underperforms
  Notebook before any default-alpha or registry change.
