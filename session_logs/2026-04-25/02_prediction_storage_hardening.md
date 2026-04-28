# Prediction Storage Hardening

## Goal

- Harden the split live/completed prediction storage rollout before writing live
  rows to the new Supabase tables.

## Constraints

- Do not populate the new live/completed prediction tables in this phase.
- Keep legacy prediction and accuracy tables untouched.
- Preserve Goose as the first population target after hardening.

## Current Supabase State

- The four split-storage tables remain intentionally empty:
  - `next_show_prediction_runs`
  - `next_show_prediction_songs`
  - `completed_show_prediction_runs`
  - `completed_show_accuracy`

## Work Planned

- Add a read-only rollout checker for table readability, empty/populated state,
  schema checks when the schema RPC is available, and per-band/model counts.
- Add dry-run support to live prediction and retained completed-show scoring
  paths.
- Add guardrails before destructive projection replacement and retained-corpus
  pruning.

## Next Step

- Run dry-run Goose payload checks and the empty-state rollout checker before
  any Goose population command.
- For Goose-first rollout, use model-scoped retained-corpus commands so
  Notebook and Deal can be rehearsed, written, and retried independently.
- Expect Deal retained-history scoring to be materially slower than Notebook
  because it uses fresh in-memory training for each historical target.
