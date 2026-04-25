# Extending the Platform

This guide explains how to add new bands and models to the JamBandNerd project.

## How to Add a New Band

Adding a new band requires changes in collection, normalization compatibility,
orchestration, and the live band registry the website reads from.

Before implementing, read the canonical
[Data Strategy](../../reference/specifications/data_strategy.md). A new band is
not complete unless it can participate in the shared show-centric prediction
flow.

### 1. Data Collection

To add a new band, you need to create a new data collector and integrate it into the pipeline.

1. **Create raw tables**: add at least `{band}_shows_raw`, `{band}_setlists_raw`,
   and `{band}_songs_raw`. Add supporting tables only if the source requires
   them.
2. **Create a collector**: add a collector under
   `src/jambandnerd/data_collection/<band_name>/`.
3. **Create a collection entrypoint**: add `scripts/run_<band>_collection.py`.
4. **Preserve the normalized contract**: shared code must be able to derive
   `show_id`, `show_date`, `song_name`, and deterministic show ordering.
5. **Update repo band support**: add the band to the repo-authoritative
   workflow/config surface in `src/jambandnerd/config/bands.py`.
6. **Register runtime metadata in Supabase**: add a row to the live `bands`
   table with the slug, display name, raw shows table, and ID column. The
   website reads bands dynamically from this registry.
7. **Wire orchestration**: update current runners and automation paths that
   consume the repo-supported band list.
8. **Validate predictions**: confirm `generate_predictions.py` and
   `run_backtest.py` work for the new band.
9. **Verify the website path**: ensure the new band appears through the
   dynamic website data layer without adding a hardcoded frontend band list.

## How to Add a New Model

Adding a new model follows a similar pattern.

### 1. Model Implementation

1. **Create a new model**: add the model under `src/jambandnerd/models/<model_name>/`.
2. **Consume `ModelData`**: reuse the shared normalized transform boundary rather
   than introducing a separate raw-data path.
3. **Update consolidated scripts**: wire the model into:
   - `scripts/generate_live_predictions.py`
   - `scripts/run_backtest.py`
   - `scripts/run_optimized_pipeline.py`
4. **Create storage**: write live next-show rows to
   `next_show_prediction_runs`/`next_show_prediction_songs`, and write retained
   completed-show rows to `completed_show_prediction_runs` plus
   `completed_show_accuracy`.
5. **Document versioning**: define the `model_version` contract for the new
   model.

### 2. Presentation Layer

The public surface is the website app in `apps/web`. Model presentation metadata
still lives in `apps/web/src/lib/config.ts`, but backend lifecycle and
capability flags come from `src/jambandnerd/models/metadata.py`.

```ts
MODEL_CONFIG = {
  notebook: {
    displayName: "Notebook",
    explanation: "Existing notebook model explanation.",
  },
  new_model: {
    displayName: "New Model",
    explanation: "A brief explanation of how the new model works.",
  },
} as const;
```
