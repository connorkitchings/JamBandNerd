# Session 05 — Phish Diagnostics (Feature Analysis + Error Cases)

**Date**: 2026-05-07
**Branch**: `feat/single-model-per-band`

## Goal

Run comprehensive feature diagnostics on Phish incumbent (`PhishFastPlusNotebookRankVenueRun`, dual=0.4186) to understand:
1. Which features drive predictions (importance ranking)
2. Feature health (zero rates, correlations, monotonicity)
3. Error patterns (worst-predicted shows)

## Command Run

```bash
uv run python scripts/diagnose_phase_b_features.py \
    --band phish \
    --predictor jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun \
    --shows 50 \
    --snapshot-root .snapshots/phish_phase_b
```

**Output**: `.snapshots/phish_phase_b/diagnostics/phish_phish_fast_gbm_v2_feat_notebook_rank_venue_run_50shows.md`

---

## Key Findings

### 1. Dataset Characteristics

- **Shows analyzed**: 50 (2025-04-27 to 2026-05-02)
- **Training rows**: 1,330,740 (avg ~26,600 candidate songs per show)
- **Overall positive rate**: 6.25% (low due to large Phish catalog ~500-800 songs)
- **Feature count**: 14 diagnostic features

**Observation**: Phish's positive rate (6.25%) is much lower than other bands due to catalog size. Billy's is ~8-10%, WSP's is ~10-12% (smaller catalogs). This makes precision inherently harder.

---

### 2. Feature Importance Ranking (by Gain)

| Rank | Feature | Gain | Split | Label Corr | Monotonicity | Zero% |
|---|---|---|---|---|---|---|
| 1 | `plays_past_2yr` | 640 | 648 | **+0.233** | **+1.000** ✅ | 1.4% |
| 2 | `gap_shows` | 563 | 1132 | -0.118 | -0.588 ⚠️ | 0.0% |
| 3 | `month_play_rate` | 262 | 1034 | -0.000 | +0.067 ⚠️ | 10.3% |
| 4 | `career_play_pct` | 262 | 1061 | +0.120 | +0.964 ✅ | 0.0% |
| 5 | `tour_position` | 219 | 612 | +0.011 | +0.238 | 0.0% |
| 6 | `plays_past_50` | 184 | 283 | **+0.222** | **+0.964** ✅ | 16.8% |
| 7 | `same_venue_run_position` | 95 | 285 | +0.015 | +0.400 | 0.0% |
| 8 | `diff_25_to_50` | 79 | 370 | -0.049 | -0.214 | 35.5% |
| 9 | `same_venue_run_prior_played` | 56 | 79 | -0.070 | +0.000 ⚠️ | **93.0%** ❌ |
| 10 | `plays_past_25` | 50 | 209 | +0.190 | +0.900 ✅ | 33.5% |
| 11 | `show_position_in_run` | 32 | 146 | +0.019 | +0.000 ⚠️ | 0.0% |
| 12 | `plays_past_10` | 30 | 141 | +0.107 | -0.500 ⚠️ | 53.7% |
| 13 | `same_venue_run_prior_play_count` | 0 | 0 | -0.070 | +0.000 ⚠️ | **93.0%** ❌ |
| 14 | `same_venue_run_prior_play_share` | 0 | 0 | -0.062 | +0.000 ⚠️ | **93.0%** ❌ |

---

### 3. Critical Issues Identified

#### ❌ Issue #1: Venue-Run Features Are Dead Weight

**Features affected**: `same_venue_run_prior_played`, `same_venue_run_prior_play_count`, `same_venue_run_prior_play_share`

**Evidence**:
- **93% zero rate**: Phish rarely plays same venue multiple nights in a row in modern era (mostly festivals + 1-2 night runs)
- **Zero gain importance**: Model assigns no predictive value
- **Flat decile lift**: No monotonic relationship with label
- **Negative label correlation**: -0.06 to -0.07 (slightly harmful)

**Root cause**: Venue-run features were designed for bands like Billy Strings (multi-night theater runs) and WSP (amphitheater residencies). Phish's touring pattern is different:
- Summer tour: mostly 1-night stands
- Multi-night runs: typically 2-3 nights at same venue, but setlists vary dramatically night-to-night
- Festivals: single-night appearances

**Recommendation**: **Remove all 3 venue-run features from Phish model**. This reduces feature count from 14 to 11, removes noise, and may improve generalization.

---

#### ⚠️ Issue #2: `month_play_rate` Has Zero Predictive Power

**Evidence**:
- Label correlation: -0.000 (exactly zero)
- Monotonicity: +0.067 (essentially flat)
- Gain importance: 262 (mid-tier, but not earning its keep)

**Root cause**: Phish does not have strong seasonal patterns in setlist construction. Unlike bands that tour seasonally or have holiday traditions, Phish plays year-round with no month-specific song preferences.

**Recommendation**: **Remove `month_play_rate` feature**.

---

#### ⚠️ Issue #3: Short-Window Recency Features Underperform

**Features affected**: `plays_past_10` (53.7% zero, negative monotonicity), `plays_past_25` (33.5% zero)

**Evidence**:
- `plays_past_10`: Negative monotonicity (-0.500), high zero rate
- `plays_past_25`: Better (+0.900 monotonicity) but still 33.5% zeros

**Comparison**: `plays_past_50` (+0.964 monotonicity, 16.8% zero) and `plays_past_2yr` (+1.000 monotonicity, 1.4% zero) are much stronger.

**Root cause**: Phish's rotation is too large for 10-show windows to capture meaningful signal. Songs can go 20-50 shows between plays and still be "in rotation."

**Recommendation**: **Test removing `plays_past_10`, keep `plays_past_25` as bridge to `plays_past_50`**.

---

#### ✅ Strength: Long-Window Features Dominate

**Top performers**:
- `plays_past_2yr`: Gain=640, corr=+0.233, mono=+1.000 (perfect)
- `plays_past_50`: Gain=184, corr=+0.222, mono=+0.964
- `career_play_pct`: Gain=262, corr=+0.120, mono=+0.964

**Interpretation**: Phish setlists are driven by:
1. **Long-term rotation** (2-year window captures "core repertoire" vs. "deep cuts")
2. **Career frequency** (staples like "Tweezer", "You Enjoy Myself" always in play)
3. **Gap since last play** (negative correlation = songs unplayed longer are NOT more likely — Phish doesn't "owe" songs)

---

### 4. Error Case Studies

#### Worst 10 Shows by F1@25

| Date | F1@25 | P@10 | R@50 | Actual Songs |
|---|---|---|---|---|
| 2024-08-14 | 0.000 | 0.000 | 0.000 | 8 |
| 2025-01-28 | 0.000 | 0.000 | 0.000 | 3 |
| 2026-04-17 | 0.000 | 0.000 | 0.263 | 19 |
| 2025-09-20 | 0.047 | 0.100 | 0.222 | 18 |
| 2026-01-27 | 0.071 | 0.000 | 0.333 | 3 |
| 2025-07-16 | 0.091 | 0.000 | 0.421 | 19 |
| 2024-10-27 | 0.140 | 0.200 | 0.333 | 18 |
| 2025-06-28 | 0.140 | 0.300 | 0.389 | 18 |
| 2025-07-12 | 0.140 | 0.000 | 0.333 | 18 |
| 2025-09-14 | 0.140 | 0.100 | 0.444 | 18 |

**Pattern**: 3 of the worst 10 shows have **≤8 actual songs** (8, 3, 3). These are likely:
- **Acoustic/striped-down sets** (e.g., solo performances, non-full-band shows)
- **Festival sets** (shorter time slots, atypical song selection)
- **Special events** (Halloween, NYE warm-ups)

**Model failure mode**: The model predicts for "typical" full-band Phish shows (~17-22 songs). When the actual show is 3-8 songs (acoustic, festival), the model's top-25 predictions have near-zero overlap.

#### Best 10 Shows by F1@25

| Date | F1@25 | P@10 | R@50 | Actual Songs |
|---|---|---|---|---|
| 2024-08-06 | 0.444 | 0.400 | 0.650 | 20 |
| 2024-09-01 | 0.455 | 0.600 | 0.789 | 19 |
| 2024-08-09 | 0.465 | 0.500 | 0.722 | 18 |
| 2025-09-12 | 0.465 | 0.400 | 0.778 | 18 |
| 2024-04-20 | 0.476 | 0.500 | 0.706 | 17 |
| 2025-09-16 | 0.478 | 0.600 | 0.667 | 21 |
| 2024-08-17 | 0.489 | 0.500 | 0.600 | 20 |
| 2024-12-31 | 0.519 | 0.500 | 0.690 | 29 |
| 2025-12-31 | 0.538 | 0.600 | 0.704 | 27 |
| 2025-07-22 | 0.571 | 0.700 | 0.882 | 17 |

**Pattern**: Best shows have:
- **Typical setlist size**: 17-22 songs (except NYE 27-29 songs, which the model still nails)
- **Full-band electric sets**: No acoustic/festival outliers
- **Standard tour context**: Not opening/closing night extremes

---

## Recommendations

### Immediate Actions (Low Risk)

1. **Remove venue-run features** (3 features):
   - `same_venue_run_prior_played`
   - `same_venue_run_prior_play_count`
   - `same_venue_run_prior_play_share`
   
   **Expected impact**: Cleaner signal, reduced overfit risk, minimal performance change (already zero importance)

2. **Remove `month_play_rate`** (1 feature):
   - Zero correlation, no predictive value
   
   **Expected impact**: Neutral

3. **Test removing `plays_past_10`** (1 feature):
   - Negative monotonicity, high zero rate
   
   **Expected impact**: Possible small improvement (remove noise)

**Net change**: 14 features → 10-11 features

---

### Medium-Term Experiments (Moderate Risk)

4. **Add "show type" indicator features**:
   - Binary flag for "acoustic/stripped-down" shows (if detectable from context)
   - Binary flag for "festival" vs. "headliner" shows
   - Use case: Down-weight predictions or adjust top-K for atypical shows

5. **Extend short-window recency**:
   - Replace `plays_past_10` with `plays_past_30` (better coverage)
   - Keep `plays_past_25`, `plays_past_50`, `plays_past_2yr` ladder

6. **Add "staple song" indicator**:
   - Top 50 career plays binary flag
   - Capture Phish's "core repertoire" vs. "rotation" distinction

---

### Architecture Changes (Higher Risk)

7. **Two-stage model**:
   - Stage 1: Classify show type (typical vs. acoustic/festival)
   - Stage 2: Route to appropriate predictor (or adjust top-K)

8. **Temporal attention**:
   - Model sequence patterns (Phish is known for thematic runs, teases, callbacks)
   - Requires rethinking feature engineering from scratch

---

## Validation Plan

**Next session**: Test feature removal (recommendations 1-3):

```bash
# Create PhishFastV3 with reduced feature set
# Backtest on same 100-show window
uv run python scripts/run_phase_b_backtest.py --band phish \
    --predictor jambandnerd.models.phish.fast_predictor.PhishFastPredictorV3 \
    --shows 100 --snapshot-root .snapshots/phish_phase_b
```

**Success criteria**:
- dual ≥ 0.4186 (maintain incumbent performance with fewer features)
- p@10 ≥ 0.2929 (no regression on primary product metric)
- Cleaner feature importance ranking (no dead weight)

---

## Files Changed

- Diagnostic output: `.snapshots/phish_phase_b/diagnostics/phish_phish_fast_gbm_v2_feat_notebook_rank_venue_run_50shows.md`
- Diagnostic JSON: `.snapshots/phish_phase_b/diagnostics/phish_phish_fast_gbm_v2_feat_notebook_rank_venue_run_50shows.json`

---

## Band Status

| Band | Model | dual | Status |
|---|---|---|---|
| Goose | GooseFastRankPredictor | 0.409 | Promoted |
| Phish | PhishFastPlusNotebookRankVenueRun | 0.419 | **Incumbent held, feature cleanup planned** |
| UM | UMFastPredictorV2 | 0.343 | Promoted |
| WSP | WSPFastPredictor V2 | 0.448 | Promoted |
| Billy | BillyFastPredictorV10 | 0.388 | Local optimum |
| Eggy | — | — | Excluded from Phase B |

---

## Next Steps

1. ✅ Implement `PhishFastPredictorV3` with reduced feature set (remove 4-5 features)
2. ✅ Backtest V3 vs. V2 incumbent
3. ❌ **V3 REGRESSED** — keep incumbent, document findings
4. Proceed to medium-term experiments (show type flags, extended windows) IF pursuing further Phish work

### V3 Backtest Results

**V3 (9 features)** vs. **Incumbent (14 features)**:

| Metric | Incumbent | V3 | Delta |
|---|---|---|---|
| dual | 0.4186 | 0.4094 | **-0.0092** ❌ |
| p@10 | 0.2929 | 0.2798 | **-0.0131** ❌ |
| r@50 | 0.5442 | 0.5390 | -0.0052 |
| F1@25 | 0.2831 | 0.2811 | -0.0020 |

**Conclusion**: Feature removal hurt performance. Even low-importance features contribute value in combination. **Keep incumbent.**

**Lesson**: Diagnostics identify weak features, but removal can hurt ensemble diversity. Better approach: keep features, focus on new signal (show type, extended windows, pairing patterns).
