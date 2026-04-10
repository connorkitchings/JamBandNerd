# Deal Model (Experimental Logistic Ranker)

## Overview

Deal is the experimental third model in JamBandNerd. The current implementation
is `deal_v2`: an explainable logistic ranking model trained on shared,
band-agnostic historical-rotation features.

It is fully registered in the backend and supports predictions/backtests, but it
remains hidden from pipeline and website surfaces until it clears the model
comparison gate against CK+.

## Current Implementation

- Predictor: `src/jambandnerd/models/deal/model.py`
- Feature builder: `src/jambandnerd/models/deal/features.py`
- Serializer: `src/jambandnerd/models/deal/serialization.py`
- Model version: `deal_v2`
- Prediction table: `predictions_deal`
- Aggregate accuracy table: `accuracy_deal`
- Artifact path: `models/deal/{band}_deal_v2.json`

The current Deal implementation does **not** use XGBoost. Older XGBoost notes
remain in session history only and should not be treated as current behavior.

## Shared Feature Set

Deal only uses features that can be derived from the shared historical play
contract. The active feature set includes:

- current gap and last-time-played gap summaries
- overdue and gap z-score signals
- recent-play frequency windows
- recent-vs-long-term play-rate deltas
- optional normalized show-context counts when present in shared inputs

All feature generation is gated by the same anti-leakage rule used elsewhere in
the platform: only data strictly before the scoring reference date may be used.

## Historical Scoring Rule

Historical comparisons use a conservative reference date of **the calendar day
before** the target show date. This prevents same-day and double-header leakage
from entering features, backtests, or comparison reports.

That rule now applies consistently across:

- `scripts/run_backtest.py`
- `scripts/compare_models.py`
- Deal training-frame generation

## Comparison Workflow

Deal should be evaluated through the generic model-comparison workflow rather
than a Deal-only backtest script.

Canonical comparison run:

```bash
uv run python scripts/compare_models.py --candidate-model deal --band all --fresh-training --include-candidate-diagnostics
```

This emits a JSON report with:

- `candidate_model`
- `baseline_models`
- `windows`
- `metrics_by_band`
- `cross_band_summary`
- `deltas`
- `promotion_gate`
- `experiment_metadata`

The current standard comparison window is:

- `last_50`

If the comparison scope is expanded later, the next supported window should be
`last_100`. `all_history` is not part of the active comparison workflow.

The standard metric bundle is reported at `K=10/25/50`:

- `hit_rate`
- `avg_matches`
- `precision`
- `recall`
- `f1`

## Latest Ablation Result

Batch 1 single-factor ablations are now complete under
`docs/reports/model_baselines/ablations/batch1/`.

Outcome:

- every Batch 1 config retained a passing CK+ promotion gate
- no single-factor config satisfied the stricter Batch 2 rule of improving the
  Deal baseline while materially closing the Notebook gap on at least two of
  Goose, Phish, and Billy

The next Deal iteration should therefore focus on new shared-safe features,
not additional Batch 2 hyperparameter combinations from the current search
space.

## Promotion Gate

Deal remains experimental until the comparison report shows it clearing the
explicit CK+ gate:

- beat CK+ on cross-band average `recall@10`
- beat CK+ on cross-band average `recall@25`
- win enough bands on `recall@10` to satisfy the configured gate
- avoid any severe `recall@25` regression by band

Notebook remains the aspirational benchmark, not the release gate for this
cycle.

## Shared-Input Audit

Before adding new Deal features, audit shared field availability:

```bash
uv run python scripts/audit_shared_model_inputs.py --band all
```

Only fields that can be normalized across all active bands should be added to
the shared Deal core.

The current audit shows:

- `venue_name` is universal in historical normalized inputs
- `city`, `state`, and `country` are not universal

`venue_name` should still remain out of the Deal core until a separate audit
confirms target-show/upcoming-show venue availability is prediction-time safe
for every active band.

## Operational Notes

- Deal is registered but disabled for regular pipeline, backfill, aggregate
  accuracy, and website exposure via model metadata flags.
- The compatibility wrapper `scripts/evaluate_deal_model.py` still exists, but
  it now delegates to the generic comparison workflow.
- When running historical comparisons, prefer `--fresh-training` so Deal uses
  newly trained in-memory artifacts rather than stale files on disk.
