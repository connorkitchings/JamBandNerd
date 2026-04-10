# Model Baseline Artifacts

Durable JSON artifacts for the current model-comparison workflow.

- `2026-04-07_deal_baseline_goose_last50.json` — Goose-only `last_50` smoke baseline for Deal vs CK+ vs Notebook
- `2026-04-07_shared_model_input_audit.json` — shared historical-input audit used to freeze Deal feature scope before ablations
- `2026-04-07_deal_baseline_all_last50.json` — canonical cross-band `last_50` baseline artifact for Deal vs CK+ vs Notebook once the resumable all-band run completes
- `ablations/batch1/` — completed Batch 1 Deal ablation outputs generated through `scripts/compare_models.py --deal-overrides ...`; final analyzer outcome: no single-factor config qualified for Batch 2, so the next iteration should be feature engineering rather than combination tuning
