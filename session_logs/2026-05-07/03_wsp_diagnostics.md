# WSP V2 Diagnostics: Per-Show Performance & Feature Importance

## Goal

Analyze the promoted WSPFastPredictor V2 (wsp_fast_gbm_v2) through two lenses:
1. Per-show performance distribution to identify systematic failure modes
2. Feature importance from the actual trained LightGBM booster

## Key Findings

### 1. Severe Under-Boosting (Critical)

The model trains for an average of **11 boosting rounds** (range 2-28) out of 700 max.

| Show Date | best_iteration |
|---|---|
| 2023-03-04 | 4 |
| 2023-04-22 | 10 |
| 2023-07-30 | 2 |
| 2023-10-28 | 5 |
| 2024-04-14 | 5 |
| 2024-06-23 | 28 |
| 2025-05-16 | 8 |
| 2025-07-26 | 22 |
| 2025-10-24 | 5 |
| 2025-12-31 | 19 |

Config: lr=0.03, max_rounds=700, early_stopping=25, 20% validation split.

The lr=0.03 + rounds=700 strategy never activates. Early stopping kills training almost immediately. The model is a 2-28 tree ensemble — feature-driven, not boosting-driven.

**Implication**: HP tuning of LightGBM rounds/learning_rate is moot for WSP. The model's power comes entirely from feature quality, not ensemble depth.

### 2. Feature Importance (from trained booster)

| Feature | Gain | Gain% | Split | Split% |
|---|---|---|---|---|
| long_rotation_pressure | 19 | 40.8% | 79 | 16.5% |
| plays_past_100 | 10 | 20.9% | 44 | 9.2% |
| plays_past_50 | 7 | 15.8% | 30 | 6.2% |
| ltp_diff_recent | 2 | 4.4% | 49 | 10.2% |
| month_play_rate | 2 | 4.3% | 70 | 14.6% |
| diff_25_to_50 | 1 | 2.9% | 36 | 7.5% |
| diff_50_to_100 | 1 | 1.9% | 28 | 5.8% |
| career_play_pct | 1 | 1.8% | 31 | 6.5% |
| overdue_ratio | 1 | 1.7% | 30 | 6.2% |
| plays_past_2yr | 1 | 1.3% | 20 | 4.2% |
| gap_shows | 1 | 1.2% | 15 | 3.1% |
| All others (8 features) | 0 | <1% each | low | low |

**WSP long-rotation features**: 63.6% of total gain. The V2 architectural bet was correct — these features dominate.

**PhishFast V2 extras** (plays_past_3/5, overdue_ratio, avg_ltp_recent, ltp_diff_recent): 6.7% of total gain. Marginal.

**gap_shows**: Only 1.2% gain despite being the core recency signal. The long-rotation features effectively supersede it.

### 3. Per-Show Performance Distribution

F1@25 across 100 shows:
- min=0.0645  p25=0.2609  median=0.3111  p75=0.3913  max=0.6087
- 12% of shows have F1@25 < 0.20
- 22% >= 0.40, 7% >= 0.50

**Bottom 3 shows:**
- 2024-06-20: 6 songs, F1@25=0.065 — likely partial/abbreviated show
- 2025-02-15: 19 songs, F1@25=0.091 — missed badly
- 2025-03-23: 21 songs, F1@25=0.130 — missed badly

**Song count vs F1@25:**
| Range | n | avg F1@25 | avg p@25 |
|---|---|---|---|
| <=18 songs | 6 | 0.2219 | 0.1867 |
| 19-22 songs | 78 | 0.3315 | 0.3010 |
| >=23 songs | 16 | 0.3306 | 0.3250 |

Correlation(song_count, F1@25) = 0.14 — weak. No systematic failure by show size.

**Time trend:**
- First half (2023-03 to 2024-06): F1@25=0.3154, p@25=0.2904
- Second half (2024-06 to 2026-03): F1@25=0.3342, p@25=0.3056
- Slight improvement over time. No degradation.

**K=10 zero-hit rate**: 5/100 shows (5%). These are the hardest-to-predict shows.

### 4. Diagnostic Frame Coverage Gap

The existing `diagnose_phase_b_features.py` only captured 11 of 19 features. The `_build_training_frame` method doesn't produce WSP V2 long-rotation features or PhishFast V2 plays_past_3/5/overdue/ltp features. Feature importance was extracted directly from the LightGBM booster instead.

## Artifacts

- backtests/wsp_wsp_fast_gbm_v2_100shows.jsonl — per-show metrics (incumbent V2)
- backtests/wsp_wsp_fast_gbm_v2_summary.json — aggregate summary
- diagnostics/wsp/wsp_wsp_fast_gbm_v2_100shows.md — feature diagnostic report (11/19 features)
- diagnostics/wsp/wsp_wsp_fast_gbm_v2_100shows.json — feature diagnostic JSON

## Implications for Next Steps

1. **The model is feature-driven, not boosting-driven.** 2-28 trees at lr=0.03 means the ensemble is trivially shallow. Future gains come from better features or a different model architecture, not HP tuning.

2. **Long-rotation features were the correct bet.** 63.6% of gain. But the model may be over-reliant on `long_rotation_pressure` (40.8%). More diverse features could improve robustness.

3. **The worst shows aren't explained by show size or recency.** The 12% of shows below F1@25=0.20 are distributed across the timeline and show sizes. These may have unusual setlist compositions (covers, rarities, special events) that the candidate pruning or features don't capture.

4. **Future WSP directions:**
   - Per-show failure analysis: what songs did the model miss on the worst shows? Are they rare songs, covers, or surprise rotations?
   - Architecture change: consider whether the ranking formulation is well-suited, or if a different approach (e.g., multi-label classification, set-level prediction) would better capture show-level structure.
   - Candidate generation: the 150-recent + 100-career pruning may be cutting off rare-but-played songs on bad-show days.
   - Validation strategy: the 20% validation split with early_stopping=25 is very aggressive. A larger validation set or different early stopping strategy might allow more boosting rounds.
