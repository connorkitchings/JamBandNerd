# Deal Batch 1 Execution And Analysis

## Goal

Execute the Deal Batch 1 ablation sweep against the canonical all-band `last_50`
baseline, upgrade the analyzer so it can select Batch 2 candidates against
Notebook, and preserve the current run state in-repo.

## Constraints

- Use the canonical `2026-04-07_deal_baseline_all_last50.json` artifact as the
  comparison anchor.
- Do not start Batch 2 combinations or new feature work until all 10 Batch 1
  ablations are complete.
- Keep the current analyzer selection rule as the release gate for Batch 2:
  positive `Δdeal@10`, non-negative `Δdeal@25`, promotion-gate pass, and
  material Notebook-gap improvement on at least two of Goose, Phish, Billy.

## Summary

- Enhanced `scripts/analyze_ablations.py` to:
  - compare each ablation against the canonical Deal baseline
  - compute Notebook gap deltas
  - count focus-band improvement signals for Goose, Phish, and Billy
  - mark Batch 2 eligibility directly in the markdown output
  - emit suggested Batch 2 combination overrides when any single-factor winners
    qualify
- Added regression coverage in `tests/test_analyze_ablations.py` for both:
  - successful Batch 2 winner selection
  - no-winner stop behavior
- Updated script/report inventory docs to reflect the upgraded analyzer and the
  new `ablations/batch1/` artifact directory.
- Finished the full Batch 1 execution sweep with resumable JSON outputs under
  `docs/reports/model_baselines/ablations/batch1/`.
- Final analyzer outcome: all 10 single-factor ablations still pass the CK+
  promotion gate, but none qualify for Batch 2. The next model iteration should
  be a feature-engineering pass rather than more hyperparameter combinations.

## Commands Run

- `uv run ruff check src tests scripts`
- `uv run pytest tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py`
- `uv run ruff check scripts/analyze_ablations.py tests/test_analyze_ablations.py`
- `uv run pytest tests/test_analyze_ablations.py tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py`
- `uv run python scripts/compare_models.py --candidate-model deal --band all --window 50 --fresh-training --feature-set-label <label> --deal-overrides '<json>' --output docs/reports/model_baselines/ablations/batch1/<label>.json`
- `uv run python scripts/analyze_ablations.py --batch-dir docs/reports/model_baselines/ablations/batch1`

## Validation

- `uv run ruff check src tests scripts`
- `uv run pytest tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py`
- `uv run ruff check scripts/analyze_ablations.py tests/test_analyze_ablations.py`
- `uv run pytest tests/test_analyze_ablations.py tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py`
- Final analyzer run completed against all 10 ablation artifacts.

## Files Changed Or Artifacts Produced

Code/docs/logging:
- `scripts/analyze_ablations.py`
- `tests/test_analyze_ablations.py`
- `scripts/README.md`
- `docs/reports/model_baselines/README.md`
- `docs/reference/models/deal.md`
- `session_logs/2026-04-08/02_deal_batch1_execution_and_analysis.md`

Batch 1 artifacts:
- `threshold_min3`
- `threshold_min8`
- `threshold_retire200`
- `recency_window100`
- `recency_window50`
- `reg_strong`
- `gap_only`
- `freq_only`
- `no_venue`
- `weight_cap10`

## Final Batch Outcome

Best completed single-factor results by analyzer ranking:
- `no_venue`: `Δdeal@10=+0.0014`, `Δdeal@25=+0.0006`, promotion gate still
  passes, but it does not materially close the Notebook gap on two focus bands.
- `reg_strong`: `Δdeal@10=+0.0011`, `Δdeal@25=+0.0006`, promotion gate still
  passes, but also fails the focus-band Notebook-gap rule.
- All other ablations either regress the Deal baseline on `recall@10`,
  `recall@25`, or both.

Decision:
- No single-factor ablation qualifies for Batch 2.
- Do not run Batch 2 combinations.
- Move the next Deal iteration to feature engineering.

## Next Step

Design the next Deal feature-engineering pass around new shared-safe signals
rather than more threshold/regularization/window combinations.
