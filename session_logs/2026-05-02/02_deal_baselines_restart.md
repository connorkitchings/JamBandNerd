# Goose Deal Baseline + Feature Distillation — Active

## Session Context

Continued from `01_goose_billy_baseline_review.md`. Billy standard-bearer confirmed (BillyFast V3), so we terminated Billy Deal baseline to focus on Goose where we need answers.

## Commands Executed

### Deal Baseline (Background) — Goose Only

```bash
# Backgrounded Deal baseline run (Goose only)
nohup uv run python scripts/run_phase_b_backtest.py \
  --band goose \
  --predictor jambandnerd.models.deal.model.DealPredictor \
  --shows 100 \
  --snapshot-root .snapshots/goose_phase_b \
  --out-dir backtests/ > backtests/goose_deal_baseline.log 2>&1 &
```

**Terminated**: Billy Deal baseline (PID 76133) — unnecessary since BillyFast V3 is already the clear winner (dual=0.377 vs Notebook dual=0.333).

### Goose Feature Distillation (Background)

```bash
# Step 1: Notebook-only baseline (50 shows for screening)
nohup uv run python scripts/run_phase_b_backtest.py \
  --band goose \
  --predictor jambandnerd.models.goose.distilled.GooseDistilledNotebookPredictor \
  --shows 50 \
  --snapshot-root .snapshots/goose_phase_b \
  --out-dir backtests/ > backtests/goose_distilled_notebook_50.log 2>&1 &
```

## Process Status

| Process | Band/Model | Shows | PID | Started | Status |
|---------|-----------|-------|-----|---------|--------|
| Deal baseline | Goose | 100 | 76129 | 18:55 | Running (~2-3 hrs remaining) |
| Distilled Step 1 | Goose notebook-only | 50 | 76352 | 19:08 | Running (~30 min remaining) |

## Feature Distillation Plan

**Target**: Beat Notebook baseline (dual=0.408)  
**Approach**: Additive feature families, 50-show screening, stop on regression

### Sequence

| Step | Predictor Class | Families | Expected Runtime |
|------|----------------|----------|------------------|
| 1 | `GooseDistilledNotebookPredictor` | notebook | ~1.5-2 hrs |
| 2 | `GooseDistilledNotebookGapPredictor` | +gap | TBD |
| 3 | `GooseDistilledNotebookGapRecencyPredictor` | +recency | TBD |
| 4 | `GooseDistilledNotebookGapRecencyDebutPredictor` | +debut | TBD |
| 5 | `GooseDistilledNoVenuePredictor` | +set_position | TBD |
| 6 | `GooseDistilledFullBasePredictor` | +venue | TBD |
| 7 | `GooseDistilledFullBaseCoocPredictor` | +cooccurrence | TBD |

**Stop Rule**: If `dual_score` drops below current best, halt and backtrack.

## Data Loaded

- **Goose**: 834 shows, 7,136 setlists → 100 target shows (2024-09-22 – 2026-04-25)

## Monitoring

```bash
# Check all running backtests
ps aux | grep phase_b_backtest | grep -v grep

# Watch specific logs
tail -f backtests/goose_deal_baseline.log
tail -f backtests/goose_distilled_notebook_50.log
```

## Expected Output Files

### Deal Baseline
- `backtests/goose_deal_v2_summary.json`
- `backtests/goose_deal_v2_100shows.jsonl`

### Feature Distillation
- `backtests/goose_goose_distilled_notebook_50_summary.json`
- `backtests/goose_goose_distilled_notebook_50shows.jsonl`
- (Subsequent steps TBD based on Step 1 results)

## Billy Status (Decision Made)

| Model | dual | p@10 | r@50 |
|-------|------|------|------|
| **BillyFast V3** | **0.377** | **0.322** | **0.432** |
| Notebook | 0.333 | 0.294 | 0.373 |

✅ **BillyFast V3 confirmed as standard-bearer**. No Deal baseline needed.

## Next Steps

1. Wait for Step 1 (notebook-only 50 shows) to complete (~30 min)
2. Check if `dual_score >= 0.408` (Notebook baseline)
3. If yes, proceed to Step 2 (+gap)
4. If no, investigate feature diagnostics or try RRF approach

## Files Created/Modified

- `backtests/goose_deal_baseline.log`
- `backtests/goose_distilled_notebook_50.log`
- Session log: `session_logs/2026-05-02/02_deal_baselines_restart.md`

## Notes

- Billy Deal baseline terminated at show 1/100 — unnecessary given V3 confirmation
- Focusing all compute on Goose where we need answers
- Goose is the remaining unsolved problem (Notebook beats current model)
