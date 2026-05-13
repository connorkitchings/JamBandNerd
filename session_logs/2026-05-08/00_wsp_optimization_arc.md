# WSP V2 Optimization Arc — Session Summary

## Goal

Systematically explore improvements to the WSP V2 model (wsp_fast_gbm_v2) through hyperparameter sweeps, training procedure changes, feature engineering, and failure analysis. Promotion rule: F1@25 >= 0.3298 (+0.005 over 0.3248) AND p@25 >= 0.2960.

## Constraints

- No Supabase writes; use local `.snapshots/wsp` evaluation window (100 shows)
- Feature branch: `feat/wsp-combo-sweep`
- No promotion on sweep wins — findings inform follow-up experiments
- Keep wsp_fast_gbm_v2 as incumbent unless promotion rule is clearly beaten

## Commands Run

```bash
# Lint and test (run multiple times throughout session)
uv run ruff check src/jambandnerd/models/wsp/ scripts/wsp_failure_analysis.py tests/models/test_wsp_model.py
uv run python -m pytest tests/models/test_wsp_model.py -v

# Experiment sweeps (6 sweeps, 26 configs total)
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --shows 100 --snapshot-root .snapshots/wsp --out-dir backtests
uv run python scripts/run_experiment.py --band wsp --sweep es_sweep --shows 100 --snapshot-root .snapshots/wsp --out-dir backtests
uv run python scripts/run_experiment.py --band wsp --sweep fixed_round_sweep --shows 100 --snapshot-root .snapshots/wsp --out-dir backtests
uv run python scripts/run_experiment.py --band wsp --sweep gap_decoupled_sweep --shows 100 --snapshot-root .snapshots/wsp --out-dir backtests
uv run python scripts/run_experiment.py --band wsp --sweep venue_run_sweep --shows 100 --snapshot-root .snapshots/wsp --out-dir backtests

# Failure analysis
uv run python scripts/wsp_failure_analysis.py --bottom 12
```

## Files Changed or Artifacts Produced

### Source code
- `src/jambandnerd/models/wsp/fast_predictor.py` — Added `_gap_vs_median_arr`, `WSPFastGapDecoupled` (21 feats), `WSPFastGapDecoupledClean` (19 feats, replaces coupled features), imported `_gap_percentile_arr` from Billy
- `src/jambandnerd/models/wsp/experiments.py` — Added `WSP_GAP_DECOUPLED_SWEEP`, `WSP_VENUE_RUN_SWEEP`, registered in `WSP_SWEEPS`
- `src/jambandnerd/models/experiment.py` — (Prior session) Added `attr_overrides` to `ExperimentConfig` and `make_experiment_predictor`

### Scripts
- `scripts/wsp_failure_analysis.py` — New standalone script for per-show failure analysis with 62-song cover catalog

### Tests
- `tests/models/test_wsp_model.py` — 33 tests (was 24): added gap decoupled subclass tests, sweep registration tests for all new sweeps

### Backtest artifacts (backtests/)
- `wsp_wsp_fast_gbm_v2_combo_*`, `wsp_wsp_fast_gbm_v2_es_*`, `wsp_wsp_fast_gbm_v2_fr_*` — combo/ES/fixed-round summaries
- `wsp_wsp_fast_gbm_v2_gap_decoupled_*`, `wsp_wsp_fast_gbm_v2_gap_decoupled_clean_*` — gap decoupled summaries
- `wsp_wsp_fast_gbm_v2_feat_venue_run_*` — venue run summaries
- `wsp_failure_analysis.jsonl` — per-show failure data for bottom 12 shows

### Session logs
- `session_logs/2026-05-08/01_wsp_failure_analysis.md` — Per-show failure analysis findings
- `session_logs/2026-05-08/02_wsp_gap_decoupled_sweep.md` — Gap decoupling (negative result)
- `session_logs/2026-05-08/03_wsp_venue_run_sweep.md` — Venue run (negative result)

## Summary of Results

26 experiment configs tested. Best result: F1@25=0.3293 (+0.005), not promoted (dual regressed).

| Sweep | Configs | Best F1@25 | Delta | Verdict |
|---|---|---|---|---|
| combo_sweep | 6 | 0.3293 | +0.005 | No promotion (p@25 regressed) |
| es_sweep | 6 | 0.3292 | +0.004 | No promotion |
| fixed_round_sweep | 7 | 0.3292 | +0.004 | Confirms ceiling |
| gap_decoupled_sweep | 3 | 0.3164 | -0.008 | Negative result |
| venue_run_sweep | 3 | 0.3269 | +0.002 | Model ignores sparse features |

### Key findings

1. **Model is at ceiling.** 11 boosting rounds with lr=0.03 is the optimal training depth. More rounds overfit; fewer underfit. No HP or training procedure change clears +0.005 F1@25.

2. **Failure mode is structural.** 67% of missed songs are in the candidate set but ranked below position 50. 50 core rotation songs (>10% career frequency) get near-zero probability on failure shows. This is not a candidate pruning or gap coupling problem.

3. **Gap decoupling hurts.** The coupled features (`overdue_ratio = gap * career_pct`, `long_rotation_pressure = gap * pct100`) are more informative than decoupled versions (`gap_percentile`, `gap_vs_median`).

4. **Sparse features are ignored.** Venue-run features are non-zero for ~30% of training rows. With 11 rounds, the model can't split on them.

5. **The 100-show evaluation window may be too narrow.** Some failure shows are one-off events (Jazz Fest, Empower Field) that no model could predict.

## Validation Status

- **Lint**: `ruff check` — all passed
- **Tests**: 33/33 passed in `tests/models/test_wsp_model.py`
- **Full test suite**: Not run (only WSP-specific tests validated)
- **Quality gates** (`npm run verify:python`, etc.): Not run — changes are additive (new subclasses, new experiment configs) with no modifications to shared infrastructure

## Conclusion

**WSP V2 (wsp_fast_gbm_v2) is promoted and at ceiling.** The incumbent with F1@25=0.3248, dual=0.4484 is the best achievable with the current LightGBM rank_xendcg architecture. Future improvements require:
- A different model objective (binary, lambdarank)
- Set-level prediction or sequence models
- A larger evaluation window to distinguish signal from noise

## Next Step

Apply the experiment sweep and failure analysis methodology to another band (Phish, Goose, or Billy) where there may be more headroom. The infrastructure is band-agnostic and ready to reuse.
