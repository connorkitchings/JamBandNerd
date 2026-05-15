# ADR 0001 — Single Model Per Band

**Status**: Accepted  
**Date**: 2026-04-25  
**Branch**: `feat/single-model-per-band`

---

## Context

JamBandNerd currently runs two promoted prediction models (Notebook and Deal)
for every supported band. Each model produces an independent ranked song list
and the website surfaces both via a model-picker UI, a Compare page
(head-to-head boards), and a Replay page (historical side-by-side review).

Three problems drove this decision:

1. **User-facing complexity**: The model-picker forces users to choose between
   predictions they have no basis to evaluate. Fans want a single answer —
   what songs are likely tonight? — not a comparison of two model outputs.

2. **Mediocre shared accuracy**: Both existing models make the same broad
   assumptions. Neither was designed with a specific band's repertoire
   structure, setlist patterns, or data density in mind. Per-band design
   can capture those differences directly.

3. **Per-band specialization**: Bands differ meaningfully — Phish's set
   structure and ~1000-song catalogue, Eggy's smaller and tighter rotation,
   Goose's cover-heavy shows. A shared model architecture applies average
   assumptions to all bands and gets none of them fully right.

---

## Decision

**One purpose-built prediction model per band.**

- Each band has exactly one promoted prediction model in the registry.
- During Phase B, each model is evaluated for promotion primarily on
  **F1@25** because fixed-board precision@25 is capped by actual setlist size.
  Precision@25 remains the user-facing board accuracy metric and must not
  materially regress.
- Legacy p@10/r@50 and weighted precision metrics are tracked alongside during
  the metric transition.
- Per-band predictor classes are allowed under
  `src/jambandnerd/models/{band}/`. Different bands may use different model
  architectures if their data characteristics warrant it.
- The shared infrastructure — `ModelData` feature container, `PredictionModel`
  ABC, training/eval harness, storage contract, CI scaffolding — remains
  band-agnostic.
- The pipeline, storage, and frontend all drop the `model_slug` dimension.
  `model_version` is retained so per-band model iteration can still signal
  freshness and trigger cache invalidation.

**Sequencing:**

- Phase A: Reshape infrastructure end-to-end. All bands use a shared baseline
  predictor class (Deal-style logistic regression) as v1. This proves the new
  architecture without requiring six new models simultaneously.
- Phase B: Iterate per band. Goose first. For each band, evaluate whether the
  baseline v1 is sufficient or whether a bespoke v2 warrants new architecture.
  Gate promotion on F1@25 improvement with p@25 non-regression, while legacy
  p@10/r@50 checks remain active over the required backtest window.

**Parallel operation during development:**

- Legacy tables (`predictions`, `prediction_songs`, `historical_prediction_runs`,
  `accuracy_per_show`, and the four split tables) stay populated on `main`/`dev`
  and continue serving the live site.
- This branch builds new Supabase tables alongside them. No legacy data is
  migrated, rewritten, or removed during Phase A.
- Site cutover to new tables happens as a separate step after Phase A is
  validated end-to-end.

---

## Consequences

### Architecture rules (updated from prior rule set)

The former "rule #3 — band-agnostic core" is **reframed**, not repealed:

- **Band-agnostic**: `ModelData` feature container, `PredictionModel` ABC,
  training/eval harness (backtest loop, precision@K computation), storage
  helpers, and CI orchestration.
- **Band-specific (allowed)**: predictor class implementations under
  `src/jambandnerd/models/{band}/`. Per-band feature modules (à la
  `models/deal/features.py` today). Per-band hyperparameters in
  `config/models.py`.

Without this containment, per-band code will drift into six separate codebases
over time. The rule is: *shared infra, band-specific modeling code*.

### Registry

`_PREDICTOR_CLASSES` and `MODEL_METADATA` in `registry.py` are reshaped from
a flat model-slug key to a band-slug key. `build_predictor(band, **kwargs)` is
the only factory. Helper selectors (`list_pipeline_models`,
`list_web_models`, etc.) are replaced with `list_active_bands()`.

### Storage

Four new tables replace the current split tables:

| New table | Purpose |
|-----------|---------|
| `setlist_predictions` | Active next-show forecasts, one row per band per upcoming show |
| `setlist_prediction_songs` | Per-song projection of `setlist_predictions` |
| `setlist_results` | Completed-show runs with actuals (replaces `completed_show_prediction_runs`) |
| `setlist_accuracy` | Per-show precision metrics, keyed `(band, model_version, target_show_key)` |

All tables drop `model_slug`. `model_version` is retained as the versioning
and freshness signal.

Legacy tables remain read-only on `main`/`dev` until:
- New tables have been populated and validated for all bands.
- The website has been cutover and stable for ≥30 days.
- Per-band models have demonstrated improvement over legacy baselines.

### Frontend

Pages removed: `/compare`, `/replay`.  
Components removed: model picker, model-toggle UI, `ModelAgreeIcon`.  
`MODEL_CONFIG`, `ACTIVE_MODELS`, `ModelSlug` type, `normalizeModel` helper
are deleted from `apps/web/src/lib/config.ts`.  
`apps/web/src/lib/data/replay.ts` is deleted.

Every Supabase query in `apps/web/src/lib/data/*.ts` drops
`.eq("model_slug", ...)` filters. Queries become band-only.

### Legacy predictor classes

CK+, Notebook, and Deal predictor classes are moved to
`src/jambandnerd/models/legacy/` after Phase A completes. They remain
importable for `scripts/compare_to_legacy_baselines.py` until per-band models
have met the promotion gate for all bands.

### Metric edge case

Bands with small active repertoires (Eggy) may have fewer than 50 songs in
active rotation. A per-band `top_n` config in `config/models.py` (e.g.,
`min(50, 0.5 * active_repertoire)`) prevents precision@25 from being a
trivially saturated metric for those bands.

---

## Alternatives Considered

**Keep multi-model, change UX only**: Hide the model picker and surface only
the better-performing model per band. Fast, low-risk, no modeling work. Rejected
because it doesn't address the underlying accuracy problem and keeps dead weight
in the codebase.

**Learned ensemble (stacker)**: Blend CK+/Notebook/Deal scores per band via a
logistic combiner. Gets some per-band optimization without discarding existing
models. Rejected because it layers complexity on top of models that are
mediocre, rather than redesigning for the precision objective.

**Band-agnostic shared model, per-band hyperparameters only**: One model class,
per-band config. Preserves rule #3 fully. Rejected because bands differ enough
in setlist structure, repertoire size, and data density that architecture
differences may be warranted — and that judgment should be made per band, not
precluded in advance.
