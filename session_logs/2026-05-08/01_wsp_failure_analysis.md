# WSP Per-Show Failure Analysis

## Goal

Understand *why* the WSP V2 model fails on the bottom 12% of shows (F1@25 < 0.20). Previous sweeps found the model at ceiling for HP/training procedure tweaks. This analysis digs into the actual per-song prediction failures to identify actionable improvement paths.

## Method

Created `scripts/wsp_failure_analysis.py` — a standalone script that re-runs the backtest for bottom-12 failure shows and captures per-song data including:

- Full predicted song list with ranks, probabilities, gap_shows
- Actual songs played with enrichment
- Cover detection via a 62-song WSP cover catalog
- Rarity classification: core (>10% career), occasional (1-10%), rare (<1%)
- Candidate status: pruned (not in recent-150 or top-100 career) vs in-candidates
- Predicted rank for missed songs (26-50 close, or below top-50 far)

12 failure shows analyzed (F1@25 range: 0.065–0.189).

## Key Findings

### 1. The dominant failure mode is rank>50, not candidate pruning

| Category | Count | % of 198 misses |
|---|---|---|
| Pruned (not in candidate set) | 13 | 7% |
| Candidate, ranked 26-50 (close) | 53 | 27% |
| **Candidate, ranked below 50 (far)** | **132** | **67%** |

**Two-thirds of missed songs are in the candidate set but the model gives them near-zero probability.** This is not a candidate pruning problem — it's a ranking/scoring problem.

### 2. Core rotation songs are catastrophically mis-ranked

68 of 198 missed songs are **core rotation** (>10% career frequency):

| Status | Count | % |
|---|---|---|
| Pruned | 0 | 0% |
| Ranked 26-50 (close) | 18 | 26% |
| **Ranked below 50 (far)** | **50** | **74%** |

50 core rotation songs — including Chilly Water (43.2% of all shows), Pigeons (35.4%), Driving Song (48.8%), Porch Song (37.2%), Conrad (23.3%), Love Tractor (31.7%) — received such low model scores that they didn't even make the top-50 prediction list.

These are songs that are played at roughly 1 in 3–5 shows. The model should predict them for every show. But on failure shows, they score below position 50.

### 3. Covers are 100% missed but are a smaller slice

- 35/238 songs in failure shows are covers (14.7%)
- 35/35 covers were missed (100% miss rate)
- Only 7/35 covers were pruned; 28 were candidates but ranked too low

Covers contribute to failure but are not the primary driver. Even excluding all covers, the core rotation misses alone would tank F1@25.

### 4. Short-set shows are a structural problem

- 1/12 shows had <15 songs (Empower Field, 6 songs)
- Its F1@25 was 0.065 vs 0.153 average for normal shows
- The model predicts ~50 songs regardless of actual set length

### 5. The model appears to overfit to recent rotation

The pattern suggests the model is over-indexing on very recent play patterns. Songs that were played in the last few shows get high scores, while songs that haven't appeared in the last ~5 shows get depressed scores — even if they're core rotation songs played at 20-40% of all shows.

This explains why:
- Songs with gap=3-4 are ranked 26-50 (close but not enough)
- Songs with the same career frequency but higher gaps are ranked below 50
- The model under-boosts (11 rounds average) and relies heavily on `long_rotation_pressure` (40.8% of gain)

## Per-Show Breakdown

| Date | Venue | Songs | Covers | F1@25 | Core Miss | Close (26-50) | Far (>50) |
|---|---|---|---|---|---|---|---|
| 2023-03-05 | Virgin Hotels, LV | 22 | 4 | 0.170 | 5 | 3 | 2 |
| 2023-07-29 | Orion Amphitheater, Huntsville | 21 | 0 | 0.174 | 5 | 2 | 3 |
| 2023-10-28 | Enmarket Arena, Savannah | 28 | 8 | 0.189 | 3 | 2 | 1 |
| 2024-04-25 | Jazz Fest, NOLA | 18 | 1 | 0.140 | 9 | 1 | 8 |
| 2024-05-25 | Radiane Amphitheater, Memphis | 20 | 4 | 0.178 | 5 | 0 | 5 |
| 2024-06-20 | Empower Field, Denver | 6 | 0 | 0.065 | 4 | 1 | 3 |
| 2024-06-22 | Red Rocks | 23 | 3 | 0.167 | 7 | 3 | 4 |
| 2025-02-15 | Hard Rock Live, AC | 19 | 2 | 0.091 | 4 | 0 | 4 |
| 2025-03-23 | St. Augustine Amphitheatre | 21 | 2 | 0.130 | 6 | 2 | 4 |
| 2025-06-28 | Red Rocks | 21 | 3 | 0.130 | 6 | 1 | 5 |
| 2025-09-13 | Allianz Amphitheater, Richmond | 21 | 4 | 0.174 | 6 | 3 | 3 |
| 2026-01-22 | Hard Rock, Riviera Maya | 18 | 4 | 0.140 | 8 | 2 | 6 |

Jazz Fest (2024-04-25) is the worst — 9 core rotation songs missed, 8 ranked below 50. This show had an unusually short set (18 songs) with heavy rotation staples (Pigeons, Pleas, Radio Child, Wondering, Walkin') all ranked below 50.

## Root Cause Hypothesis

The model's early stopping (avg 11 rounds) combined with `long_rotation_pressure`'s dominance (40.8% of gain) creates a fragile ranking:

1. `long_rotation_pressure = gap * plays_pct_100` is a strong feature but is highly gap-sensitive
2. With only 11 rounds of boosting, the model can't learn nuanced interactions between gap and career frequency
3. Songs with gap > 5-6 shows get their `long_rotation_pressure` score suppressed, pushing them below songs with lower career frequency but shorter gaps

This creates a "recency bias" where the model over-prioritizes recently-played songs at the expense of core rotation songs that happen to have a gap of 5+ shows.

## Actionable Next Steps

### High-impact (address 50 core songs ranked >50)

1. **Gap decoupling**: Add features that separate "career rotation strength" from "recent gap". E.g., a `career_play_pct` feature (independent of gap), or a `rotation_tier` categorical feature. The current architecture ties rotation strength to gap via `long_rotation_pressure = gap * plays_pct_100`.

2. **Set-length estimation**: For short-set shows (festival sets), the model wastes prediction slots on 50 songs when only 6-18 will be played. A set-length regression head or a feature encoding venue type (festival/arena/theater/club) could help.

3. **More boosting rounds with stronger regularization**: The fixed-round sweep showed 50 rounds at lr=0.03 gave F1@25=0.329 (+0.004). This suggests more rounds help the model learn nuanced gap-career interactions, but overfitting kicks in beyond 50. A different regularization strategy (e.g., `path_smooth`, `max_depth`) might allow more rounds.

### Medium-impact (address 18 core songs ranked 26-50)

4. **Score calibration**: These songs are close. A post-hoc calibration step (e.g., isotonic regression on validation data) might push them into the top 25.

5. **Venue-run features**: `WSPFastVenueRun` already exists but wasn't promoted. It adds `same_venue_run_prior_played/count/share` which could help with Red Rocks runs (3 failure shows are Red Rocks or Red Rocks-adjacent).

### Low-impact (structural issues)

6. **Cover detection**: 100% miss rate on covers. A binary `is_cover` feature could help the model learn that covers follow different patterns, but covers are only 14.7% of failure songs and most are rare enough that no feature can reliably predict them.

## Artifacts

- `scripts/wsp_failure_analysis.py` — standalone failure analysis script (62-song cover catalog, per-song enrichment)
- `backtests/wsp_failure_analysis.jsonl` — per-show JSONL with full prediction data
- `backtests/wsp_wsp_fast_gbm_v2_100shows.jsonl` — existing backtest results (used to identify bottom-12)
