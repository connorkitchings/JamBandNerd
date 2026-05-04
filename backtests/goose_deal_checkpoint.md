# Paused Backtest Checkpoint: Goose Deal Baseline

## Status: PAUSED ⏸️

**Date Paused**: 2026-05-02 20:09  
**Process**: Goose Deal baseline (100 shows)  
**PID**: 76130 (currently STOPPED with SIGSTOP)

## Progress

- **Completed**: 54/100 shows (54%)
- **Last completed**: Show 54/100 - 2025-06-17 (show_id=1738002457)
- **Remaining**: 46 shows (shows 55-100)
- **Runtime so far**: ~62 minutes
- **Estimated time remaining**: ~50 minutes

## Shows Completed (54 total)

Shows 1-54: 2024-09-22 through 2025-06-17
- Includes fall 2024 tour, New Year's run 2024, winter/spring 2025 tour
- Last completed: June 17, 2025

## Shows Remaining (46 total)

Shows 55-100: 2025-06-19 through 2026-04-25
- Summer 2025 tour (June-August)
- Fall 2025 tour (September-November)  
- Holiday 2025 run (December)
- Spring 2026 tour (March-April)

## Files

**Log file**: `backtests/goose_deal_baseline.log`  
**Partial output**: None yet (JSON/JSONL written at end)  
**Expected final outputs**:
- `backtests/goose_deal_v2_summary.json`
- `backtests/goose_deal_v2_100shows.jsonl`

## How to Resume

### Option 1: Resume current process (if system stays on)
```bash
# Resume the paused process
kill -CONT 76130

# Monitor progress
tail -f backtests/goose_deal_baseline.log
```

### Option 2: Kill and restart fresh (recommended if pausing overnight/rebooting)
```bash
# Kill the paused process
kill 76130

# Restart from beginning (incremental mode not supported by this script)
uv run python scripts/run_phase_b_backtest.py \
  --band goose \
  --predictor jambandnerd.models.deal.model.DealPredictor \
  --shows 100 \
  --snapshot-root .snapshots/goose_phase_b \
  --out-dir backtests/
```

**Note**: The backtest script does NOT support incremental/resume from checkpoint. If you kill the process, you'll need to restart from show 1/100.

## Context

**Why this is paused**:
- Distilled notebook results completed (50 shows, dual=0.382)
- Notebook baseline remains winner (100 shows, dual=0.408)
- Deal baseline is slow (~1.1 min/show) and likely won't beat Notebook
- User wants to pause and potentially resume later

**Decision needed**: Whether to complete Deal baseline for completeness or abandon since Notebook already wins.

## Current Results Summary

| Model | Shows | dual | p@10 | r@50 |
|-------|-------|------|------|------|
| **Notebook** | 100 | **0.408** | 0.284 | 0.531 |
| **Distilled (notebook-only)** | 50 | 0.382 | 0.254 | 0.510 |
| Deal | 54/100 | TBD | TBD | TBD |

## Next Steps (When Ready)

1. **Resume Deal baseline**: If you want the complete comparison
2. **Kill and abandon**: If Notebook is sufficient as the standard-bearer
3. **Continue feature distillation**: Add +gap features to distilled model

---

**Checkpoint created**: 2026-05-02 20:09
