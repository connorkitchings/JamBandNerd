# Session Log: WSP Drums/Jam Exclusion + Cryptography Security Fix + Post-Merge Verification

Date: 2026-06-23
Branches: `fix/wsp-exclude-drums-jam-predictions` (#168), `fix/dependency-audit-cryptography-49` (#167), `docs/session-log-2026-06-23`

## Goal

1. WSP predictions must never include `Drums` or `Jam` (structural markers / billed co-performers, not real songs), and removing them must not shrink top_k.
2. Review all workflows (daily + weekly) for correctness.
3. Fix the failing weekly Dependency Audit.
4. Post-merge: verify the live site and Supabase data reflect both fixes.

## Constraints

- Never work on `main` (AGENTS.md rule 6).
- Preserve top_k depth: exclusion must backfill the next-ranked real song, not truncate the board.
- Apply consistently to live + backtest + diagnostic paths.
- Phish behavior unchanged (parent-class identity contract).
- No intermediate Supabase tables; in-memory transforms only.

## Root Cause: WSP Exclusion

`EXCLUDED_SONGS["wsp"]` was already populated in `src/jambandnerd/config/bands.py:159-167` (jam, drums, + 4 artist-collision names). Goose, Notebook, Deal, and GBM predictors all call `get_excluded_songs(self.band)` in their eligibility masks. **PhishFastPredictor (parent of WSPFastPredictor) never did** — so the existing filter was bypassed for the entire Phish-family inheritance chain.

Pre-regen production data confirmed the leak: `Drums` was at rank 1 (probability 0.529) on the live `/predictions?band=wsp` board.

## Files Changed

### PR #168 — `fix/wsp-exclude-drums-jam-predictions` (merged 2026-06-23 16:02 UTC)

- `src/jambandnerd/models/phish/fast_predictor.py`
  - Added `_eligible_mask_filter(candidates, eligible_mask) -> pd.Series` template-method hook (no-op identity default) on `PhishFastPredictor`.
  - Called the hook at all three eligibility-mask sites: `build_diagnostic_training_frame`, `train`, `predict`.
- `src/jambandnerd/models/wsp/fast_predictor.py`
  - Imported `get_excluded_songs` from `config.bands`.
  - Overrode `_eligible_mask_filter` to drop the WSP exclusions from the candidate mask before the top-K slice.
- `tests/models/test_wsp_model.py`
  - New `TestWSPExcludedSongs` class: hook unit test (case-insensitive, whitespace-tolerant), Phish no-op guard, end-to-end train+predict test verifying Drums/Jam absent and top_k preserved.
- `docs/operations/github_actions.md`, `docs/operations/website_delivery.md`
  - F1: hosted-web-smoke cron `30 20 * * *` → `0 22 * * *` (workflow was correct; docs were stale).
  - F2: weekly sweep summary `14:00-19:00 UTC` → `13:00-18:00 UTC`.
  - F5: live-tracker Playwright wording reworded (uses WSP `parser.py` directly, not Playwright).
- `.github/workflows/backfill-predictions.yml`
  - F10: summary `needs.setup.result` → `needs.backfill.result` (cosmetic but misleading).

### PR #167 — `fix/dependency-audit-cryptography-49` (merged 2026-06-23 16:00 UTC)

- `uv.lock`: `cryptography` 46.0.7 → 49.0.0 (single-package bump).
- Resolves **GHSA-537c-gmf6-5ccf** (High, CVSS 7.5): vulnerable OpenSSL statically linked in wheels prior to 48.0.1.

## Commands Run

```bash
# Implementation
uv run pytest tests/models/test_wsp_model.py tests/models/test_phish_model.py tests/models/test_notebook_model.py tests/test_daily_workflow_contract.py -v
uv run black --check src tests scripts
uv run ruff check src tests scripts
npm run verify:docs

# Security
uv lock --upgrade-package cryptography
tmpfile=$(mktemp /tmp/jbn-audit.XXXXXX)
uv export --format requirements-txt --locked --no-hashes --no-emit-project --output-file "$tmpfile"
uv run --with pip-audit python -m pip_audit -r "$tmpfile" --cache-dir /tmp/pip-audit-cache --no-deps --disable-pip

# CI triggers
gh workflow run daily-pipeline.yml -f band=wsp       # run 28039885012 → success
gh workflow run dependency-audit.yml                  # run 28039884840 → success (30s)

# Post-regen data verification
uv run python scripts/audit_supabase_tables.py --band wsp --band phish --band goose --band billy --band um
# + custom read-only SELECTs against setlist_predictions / setlist_prediction_songs

# Live site review
webfetch https://jambandnerd.com/predictions?band=wsp
webfetch https://jambandnerd.com/
webfetch https://jambandnerd.com/performance?band=wsp
```

## Validation Status

| Check | Status |
|---|---|
| `black --check` | PASS |
| `ruff check` | PASS |
| `npm run verify:docs` (mkdocs --strict) | PASS |
| Full pytest suite (566 + 33 WSP tests, excluding live markers) | PASS |
| Local `pip-audit` against new lockfile | PASS (`No known vulnerabilities found`) |
| CI Dependency Audit (workflow_dispatch) | PASS (run 28039884840, 30s, success) |
| CI Daily Data Pipeline WSP (workflow_dispatch) | PASS (run 28039885012, all 3 jobs success) |
| Post-regen Supabase: Drums absent from WSP top-50 | PASS |
| Post-regen Supabase: Jam + 4 artist collisions absent | PASS |
| Post-regen Supabase: top_k = 50 preserved (both JSONB + projection) | PASS |
| Post-regen Supabase: `prediction_action = generated` (not reused) | PASS |
| Live site `/predictions?band=wsp` reflects new data (Jun 23 12:17 PM EDT) | PASS |
| Live site `/` homepage smoke | PASS |
| Live site `/performance?band=wsp` ledger renders (50 scored shows) | PASS |

## Pre-existing Observations (not bugs)

- Billy has 100 projection rows for `target_show_key=26640` because two historical runs exist (id=72 current `billy_fast_gbm_v12_gap_scaled_p50` + id=8 stale `billy_fast_gbm_v10_hp_tuned` from May). The site reads by `prediction_run_id`, so display is correct; projection table has stale residue that could be cleaned up.
- `audit_supabase_tables.py` reports `state=failed` for WSP/Phish/Billy/UM with `supported_accuracy_freshness_stale`. Expected between shows — accuracy only refreshes when a show completes. Goose is `ok` because of more recent completed show.
- Eggy remains excluded from daily pipeline per ADR 0001.

## Notable Side Effect: WSP Ranking Shift

Removing Drums/Jam from training (not just from output) reshuffled the entire WSP top-50. Pre-regen top song was Drums (52.9%); post-regen top is Goodpeople (59.4%), and 5 new songs backfilled into the top-50 (The Last Straw, Mercy, Low Spark Of High Heeled Boys, Small Town, Makes Sense To Me). Probabilities rose 5-7pp across the board.

Root cause: LightGBM `rank_xendcg` is sensitive to the composition of each training group. Drums played at 36.2% of WSP shows (191/527) with extreme feature values (`plays_past_50=14`, `gap=4`). It was a feature-space outlier that shaped the model's split decisions and score scale. Removing it changes tree structures, early-stopping iteration, and the absolute score distribution. The "probabilities" (`1/(1+exp(-score))`) are uncalibrated rank scores — their absolute values shift with the training set.

Watch the 2026-06-26 Red Rocks show score to confirm the post-regen model quality is at or above baseline.

## Durable Lessons Added to PLAYBOOK.md

1. A centralized exclusion config is necessary but not sufficient — every predictor family must be verified to apply it. The PhishFastPredictor chain bypassed the existing filter for years because the application contract wasn't enforced or tested.
2. Removing an outlier from a learning-to-rank model's training data shifts the entire ranking distribution, not just the output. Removing a noise entry from output filtering alone would be a near-no-op; removing it from training produces a structurally different model.

## Next Step

- Monitor the next scheduled Daily Data Pipeline (today 19:00 UTC) to confirm the 5-band scheduled run stays green.
- After the 2026-06-26 Red Rocks show completes, score it and compare WSP model accuracy against the pre-regen baseline — if F1@25 regresses meaningfully, consider promoting a new WSP model version rather than silently shipping the exclusion fix.
- (Optional) Clean up the stale Billy projection rows for `target_show_key=26640` (id=8, model_version=`billy_fast_gbm_v10_hp_tuned`).
