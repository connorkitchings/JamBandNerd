# Model Baseline Artifacts

Durable JSON artifacts for the current model-comparison workflow.

The comparison workflow also maintains a local per-show cache under
`docs/reports/model_baselines/cache/` for model-development runs. These cache
artifacts preserve exact historical ranked boards plus per-show metrics so
future candidate-model comparisons can aggregate from cached rows rather than
recompute every show. Canonical experimental reports should now capture the
`replacement_readiness` and `candidate_weak_shows` sections so the artifact can
double as both a baseline snapshot and a next-iteration triage surface.

- `2026-04-07_deal_baseline_goose_last50.json` — Goose-only `last_50` smoke baseline for Deal vs CK+ vs Notebook
- `2026-04-07_shared_model_input_audit.json` — shared historical-input audit used to freeze Deal feature scope before ablations
- `2026-04-07_deal_baseline_all_last50.json` — canonical cross-band `last_50` baseline artifact for Deal vs CK+ vs Notebook once the resumable all-band run completes
- `2026-04-09_deal_readiness_all_last50.json` — current resumable cache-first Deal readiness report; includes `replacement_readiness`, `candidate_weak_shows`, and `cache_summary` and can be resumed with the same `compare_models.py` command
- `ablations/batch1/` — completed Batch 1 Deal ablation outputs generated through `scripts/compare_models.py --deal-overrides ...`; final analyzer outcome: no single-factor config qualified for Batch 2, so the next iteration should be feature engineering rather than combination tuning
