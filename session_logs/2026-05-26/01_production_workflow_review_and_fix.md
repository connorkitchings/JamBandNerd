# Session Log: Production Workflow Review, Audit Fix, and Freshness Hardening

Date: 2026-05-26
Branch: `dev`

## Goal

Review the publishing of the most recent branch to production (PR #148) and ensure daily/weekly GitHub Actions workflows are healthy. Fix discovered issues. Enhance setlist completeness testing.

## Constraints

- Never work directly on `main` (use feature branches or `dev`)
- Preserve anti-leakage `reference_date` rules
- Band-agnostic core stays band-agnostic

## Commands Run

```bash
uv lock
uv run pytest tests/test_verify_data_freshness.py -v
uv run ruff check scripts/verify_data_freshness.py tests/ tests/pipeline/
uv run black --check scripts/verify_data_freshness.py tests/ tests/pipeline/
gh run list --workflow="Daily Data Pipeline" --limit 5
gh run list --workflow="Weekly Correction Sweep" --limit 10
gh run list --workflow="Dependency Audit" --limit 5
gh workflow run weekly-correction-sweep.yml -f band=all
gh workflow run daily-pipeline.yml -f band=goose
gh workflow run backfill-predictions.yml -f band=goose -f dry_run=false
```

## Files Changed

- `pyproject.toml` — Added `idna>=3.15` and `urllib3>=2.7.0` to fix dependency audit CVEs
- `uv.lock` — idna 3.10→3.16, urllib3 2.6.3→2.7.0
- `scripts/verify_data_freshness.py` — Added partial setlist detection (<3 unique songs threshold) matching the evaluation layer's `list_completed_shows()` contract. New `partial_data`/`partial_count` outputs for CI.
- `tests/test_verify_data_freshness.py` — New: 18 unit tests covering dataclass properties, song counting, and end-to-end audit function (missing, partial, boundary cases, custom thresholds)
- `tests/pipeline/test_live_band_smoke.py` — New `test_live_setlist_completeness`: per-band live smoke test querying Supabase for ≥3 unique songs per recent show
- `.github/workflows/backfill-predictions.yml` — Fixed: added `--replay-window 50` to validation step (merged to `main` via PR #149)

## Artifacts

- PR #149: `fix(ci): pass --replay-window 50 to backfill validation` (merged to `main`)
- Weekly correction sweep dry-run: all 6 bands passed (May 19 `ModuleNotFoundError` resolved by PR #148)
- Daily pipeline for Goose: generated May 27 prediction, all validations clean
- Backfill sync for Goose: 50 shows in both `setlist_results` and `setlist_accuracy`, all validated

## Issues Discovered & Resolved

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Dependency audit failing weekly | Stale `idna==3.10`, `urllib3==2.6.3` with known CVEs | Added lower bounds in `pyproject.toml`, lockfile updated |
| Weekly correction sweep failing all 6 bands | `correction_detector.py` missing from `main` (only on `dev`) | Already fixed by PR #148 merge on May 23; confirmed passing today |
| Backfill validation failing with "50/100 retained eligible rows" | `validate_accuracy_tables.py --replay-window` defaulted to 100, but corpus is 50 | Added `--replay-window 50` to backfill workflow (PR #149) |
| `verify_data_freshness.py` blind spot | Only checked binary setlist presence (any rows), but evaluation requires >2 unique songs | Added `partial_show_count`/`partial_show_ids` with configurable `min_unique_songs` threshold |
| May 22-23 Goose predictions appeared stale | Only one active prediction retained per band/model_version; old predictions deleted on supersession | Intentional design — accuracy data is the permanent record. Explained in audit. |

## Goose Predictions Analysis

| Show | Venue | Songs | p10 | p25 | r25 | Model |
|------|-------|-------|-----|-----|-----|-------|
| May 22 | Electric Brixton | 11 | 30% | 16% | 36.4% | `goose_fast_rank_v1` |
| May 23 | Electric Brixton | 11 | 30% | 24% | 54.5% | `goose_fast_rank_v1_candidate_relaxed_special_nbtop10` |
| May 25 | La Madeleine | 7 | 20% | 20% | 71.4% | `goose_fast_rank_v1_candidate_relaxed_special_nbtop10` |

May 23 prediction was generated fresh on May 23 at 19:27 UTC using May 22's setlist as input. The prediction storage model (`upsert_setlist_prediction_run`) keeps only one active prediction per band/model_version, deleting previous ones on supersession. The accuracy/per-show tables are the permanent evaluation record.

## Verification

- `uv run pytest tests/test_verify_data_freshness.py` — 18/18 passed
- `uv run ruff check` — all passed
- `uv run black --check` — all clean
- Dependency audit: 0 vulnerabilities
- Weekly sweep: all 6 bands passed
- Daily pipeline: Goose passed, prediction for May 27 generated
- Backfill sync: 50 rows in both tables, validated

## Next Step

Open PR from `dev` to `main` with the dependency audit fix, verify_data_freshness hardening, and new tests.
