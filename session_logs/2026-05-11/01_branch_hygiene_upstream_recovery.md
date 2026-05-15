# Branch Hygiene + Upstream Recovery

## Goal

Continue the `feat/wsp-combo-sweep` branch after the May 10 handoff by
preserving shippable readiness fixes and making the current WSP/Billy blockers
explicit.

## Branch Hygiene Decisions

- Keep the Billy baseline documentation correction: `BillyFastBaselinePredictor`
  aliases `BillyFastPredictorV10` with model version
  `billy_fast_gbm_v10_hp_tuned`.
- Keep the UM schema-sync fixes in `scripts/run_um_collection.py` and the UM
  collector/normalizer. The prior session completed forced UM production
  pipeline validation after these changes.
- Keep `PhishFastPlusShowType` as an experiment artifact only. It remains
  reachable through `PHISH_SWEEPS["show_type_sweep"]`, but it is not registered
  as the production Phish model because it regressed the incumbent backtest.
- Keep `prepare_dataframe_for_upsert` dropping extra schema columns before
  PostgREST writes. Validation already reports extra columns as ignored, and
  the prepared dataframe must match the live table contract before upsert.

## Current Blockers

- WSP: Everyday Companion currently has recent show pages without setlist tables
  for May 8 and May 9, 2026.
- Billy: `bmfsdb.com` is returning HTTP 500 during source reachability
  preflight.

## Next Step

Do not run or require a full five-band forced Supabase audit until WSP and
Billy can publish current website-facing rows again. Use focused tests and the
canonical verify commands to harden the partial readiness branch.
