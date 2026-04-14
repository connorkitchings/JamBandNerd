# Architectural Decision Record (ADR)

This document records key architectural decisions made during the development of JamBandNerd.

---

## ADR-001: Adopt Supabase for All Data Storage

- **Date**: 2025-07-23
- **Status**: Adopted
- **Context**: The original system relied on local CSV and JSON files for data storage. This was not
  scalable, made data sharing difficult, and prevented the development of a cloud-based web interface.
- **Decision**: All data pipelines (collection, transformation, prediction) will use a central
  Supabase (PostgreSQL) database as the single source of truth. Local file storage is deprecated.
- **Consequences**:
  - All data collection scripts were refactored to export data directly to Supabase tables.
  - Prediction models were updated to load data from Supabase and save predictions back to it.
  - Enables a clear path for a web application to display real-time data.

---

## ADR-002: Refactor to Band-Agnostic Prediction Models

- **Date**: 2025-07-24
- **Status**: Adopted
- **Context**: Initial prediction models had band-specific logic, leading to significant code
  duplication (e.g., separate CK+ models for Phish and Goose). This made maintenance and
  improvements difficult.
- **Decision**: Refactor the prediction logic into a band-agnostic architecture. Create a clear
  separation between band-specific data preparation and the core, reusable model logic.
- **Consequences**:
  - Created a central `src/jambandnerd/models/` directory for shared model code (`ckplus_model.py`,
    `notebook_model.py`).
  - Band-specific prediction pipelines now focus only on loading and transforming data before
    passing it to the common model.
  - Reduced code duplication by ~80% and simplified adding new models or tuning existing ones.

---

### ADR-003: Use Unified Database Tables for Predictions and Accuracy

- **Date**: 2025-07-31
- **Status**: Adopted, amended 2026-04-14
- **Context**: As more bands and models were added, the initial approach of creating separate
  prediction and accuracy tables per band and model (e.g., `goose_predictions_notebook`,
  `phish_accuracy_ckplus`) became cumbersome for cross-band analysis and UI development.
- **Decision**: Consolidate predictions and accuracy metrics into unified tables, identified by a
  model slug (e.g., `notebook`, `deal`). A `band` column distinguishes the data
  for each band.
  - Canonical run-level predictions: `predictions`
  - Derived song-level projection: `prediction_songs`
  - Canonical per-show evaluation: `accuracy_per_show`
  - Historical scored lineage: `historical_prediction_runs`
- **Consequences**:
  - Simplifies queries for the web interface and replay tooling.
  - All prediction and accuracy pipeline scripts must filter explicitly by `band`,
    `model_slug`, and `model_version` where appropriate.
  - Legacy per-model prediction and aggregate-accuracy tables become migration
    history rather than active storage surfaces.

---

### ADR-004: Implement Database-Driven Incremental Updates for Scraping

- **Date**: 2025-07-24
- **Status**: Adopted
- **Context**: The Widespread Panic data collection, which relies on web scraping, was inefficiently
  re-scraping all 3,000+ shows on every run.
- **Decision**: Implement a database-driven update strategy. The pipeline now queries the Supabase
  database to find the most recent show date and only scrapes for shows after that date.
- **Consequences**:
  - Drastically reduced the runtime of the WSP data collection pipeline for daily updates
    (from minutes to seconds).
  - Makes the pipeline more resilient and less resource-intensive.
  - This pattern can be applied to any future scraping-based data collectors.
