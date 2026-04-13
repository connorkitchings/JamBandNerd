# Architecture Overview

This document provides the high-level system view. For the canonical ingestion,
storage, sequencing, and prediction contract, use the
[Data Strategy](../../reference/specifications/data_strategy.md) document.

## Overview

JamBandNerd is a show-centric data platform for jam band setlist collection,
normalization, prediction, and evaluation. The public product target is a
website-first experience backed by Supabase and the consolidated Python
pipeline.

## System Flow

```mermaid
graph TD
    A[External APIs and Websites]
    B[Band Collectors]
    C[Supabase Raw Tables]
    D[Shared Normalization]
    E[ModelData]
    F[Notebook and Deal Models]
    G[Predictions and Accuracy Tables]
    H[Website]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
```

## Layers

### Collection

- Band-specific collectors handle source quirks and write to raw tables.
- The standard raw families are `{band}_shows_raw`, `{band}_setlists_raw`, and
  `{band}_songs_raw`.
- Supporting tables such as venues or upcoming shows are allowed when the
  source requires them.
- WSP remains a special-case collector because CI reliability can require
  browser automation.

### Normalization and Transformations

- Shared code does not model directly from source-specific raw payloads.
- The normalization boundary in `scripts/common.py` and
  `src/jambandnerd/transformations/gaps.py` aligns bands onto a shared contract.
- Historical ordering is deterministic: `show_date` first, then a stable
  secondary key.
- All downstream feature generation remains in memory; no intermediate
  transformed Supabase tables are allowed.

### Models and Evaluation

- `ModelData` is the canonical handoff from transforms into models.
- Notebook and Deal are the promoted website-facing models. CK+ is retired and
  retained only as a historical baseline because legacy prediction and accuracy
  rows still exist in storage.
- All three registered models rely on the same ordered historical show sequence and
  the same `reference_date` anti-leakage rule.
- `accuracy_per_show` is the granular evaluation source; aggregate accuracy
  tables are derived summaries.

### Delivery

- The website in `apps/web` is the current public surface.
- Supabase remains the shared storage and read layer for predictions and
  accuracy data.
- `apps/web/src/lib/data.ts` remains the compatibility import surface while domain ownership is split across `apps/web/src/lib/data/{bands,predictions,accuracy,replay,shows,venues}.ts`.
- Route files should compose server-side results rather than reimplement query logic.
- Client components are reserved for interactive islands, navigation hooks, and live subscriptions.

Current website routes:
- `/` - Homepage with band overview and upcoming shows
- `/predictions` - Live predictions with model comparison and show outlook
- `/performance` - Historical accuracy charts with K-value selection
- `/compare` - Model board comparison against actual setlists
- `/replay` - Canonical historical prediction replay with both model boards and
  the actual setlist for one completed show
- `/explorer` - Compatibility redirect to `/replay`
- `/last-show` - Most recent completed show details
- `/about`, `/contact`, `/data-use` - Public informational pages

Key shared components:
- `page-hero`, `site-header`, `site-footer`, `dashboard-side-nav`
- `prediction-hero`, `song-board`, `recall-chart`, `accuracy-table`
- `show-outlook-popover`, `live-tracker`, `model-agreement`

### Orchestration

- `scripts/run_optimized_pipeline.py` is the canonical end-to-end local runner.
- GitHub Actions executes the daily pipeline in production-like automation.
- Pull requests targeting `main` should clear `Repo Quality` and `Verify Website` before merge.
- Band metadata (slug, display name, raw table names, ID column) is managed in the
  `bands` Supabase table as the single write point. The website reads it dynamically;
  adding a new band requires only inserting a row into `bands` and creating a collector.
- Supported bands: Goose, Phish, Eggy, Billy Strings, Widespread Panic, Umphrey's McGee

### Model Platform

The backend model platform is registry-based. The canonical model source of
truth is `src/jambandnerd/models/registry.py`, which defines predictor class,
table/version mapping, serializer, and orchestration capability flags.

Three models are registered:

| Model | Slug | Status | Prediction Table |
|-------|------|--------|-----------------|
| Notebook | `notebook` | Web promoted | `predictions_notebook` |
| CK+ | `ckplus` | Retired baseline | `predictions_ckplus` |
| Deal | `deal` | Web promoted | `predictions_deal` |

New prediction models are added through the registry workflow (see
`docs/contributor/model_development.md`):
1. Add a model package that consumes the shared `ModelData` contract
2. Add a model-specific serializer module
3. Add one `ModelDefinition` entry in the registry
4. Optionally add frontend presentation metadata in website config

All models write to `prediction_songs` via `replace_prediction_projection()`, making
them automatically available to the website's analytics and explorer routes.

## Non-Negotiable Rules

- Shared prediction code must remain band-agnostic.
- Collector-specific logic belongs in the collector and config layers.
- `reference_date` must gate all transforms and backtests.
- New data architecture work must preserve the two-stage contract:
  source-faithful raw storage, shared normalized modeling inputs.
- Band metadata lives in the `bands` Supabase table — the website reads it
  dynamically. Do not hardcode band lists in frontend code.
- Backend model registration lives in `models/registry.py`; frontend
  `MODEL_CONFIG` is product presentation metadata only.
