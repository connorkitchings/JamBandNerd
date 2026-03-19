# Implementation Schedule

Instructions: This document is the tactical plan for the project. Use it to plan sprints,
track tasks, and manage risks. It answers the questions "Who, when, and on what?"

Current note: this file is a historical sprint record. For the active product direction and
website-first migration plan, use `docs/ROADMAP.md`.

Sprint Overview
Current Sprint: Sprint 2 (Goose-first Pipeline)

Sprint Goal: Deliver a complete, single-band (Goose) end-to-end pipeline: collect → transform →
predict. Defer automation and additional bands until Goose pipeline is verified.

Dates: 2025-08-09 to 2025-08-17

Planned Tasks (Documentation-first)

- [x] Finalize CLI Specification (jbn) and glossary
- [x] Define DB Utilities Specification (connection, operations, validation)
- [x] Confirm Supabase table naming (with model in predictions/accuracy)
- [x] Update README and ONBOARDING with CLI usage overview
- [x] Draft Goose data pipeline specification (collect → transform → predict)
- [x] Define model outputs and accuracy metrics schema
- [x] Define orchestration flow for daily run (docs only; automation later)

Progress Update (2025-08-18)

- [x] Implement Goose raw data collection; enforce Goose-only shows; add venues via API (`goose_venues_raw`).
- [x] Update `docs/schemas/goose_api.md` with venues endpoint.
- [x] Implement notebook model transformation (reference show date, last-year window, last-3
      exclusion, current_gap).
- [x] Generate and persist top-50 predictions to `goose_notebook_predictions`
      (unique on band+reference_date+model_version).
- [x] Add metadata logging: `collection_runs`, `predicted_at` timestamps.
- [x] Historical backtesting script and summary table `notebook_accuracy` (last 50 shows).
- [x] Add nightly automation (GitHub Actions) to run collection, predictions, and accuracy summary.

Action Items for Next Sprint

- Begin Sprint 3 tasks.

---

### Sprint 3: Refactoring & CK+ Model

**Sprint Goal**: Refactor the database schema to use unified prediction tables, implement
robust data validation, and add the new `ckplus` model for Goose.

**Dates**: 2025-08-20 to 2025-08-28

**Planned Tasks**:

- [x] **Refactor to Unified Tables**:
  - [x] Modify `scripts/generate_goose_predictions.py` to write to a unified `predictions_notebook`
        table, adding a `band` column.
  - [x] Update `scripts/save_notebook_accuracy.py` to write to a unified `notebook_accuracy` table.
  - [x] Adjust `src/jambandnerd/web/app.py` to read from the unified table and filter by band.
  - [x] Update `ADR-003` to reflect the decision to use unified tables.
- [x] **Implement Database Validation**:
  - [x] Implement schema validation logic in `src/jambandnerd/db/validation.py`.
  - [x] Add a utility to `src/jambandnerd/db/operations.py` to fetch table schemas from Supabase.
  - [x] Integrate validation checks into the data collection and prediction scripts before writing
        to the database.
- [x] **Implement CK+ Model**:
  - [x] Create the core `ckplus` model logic in `src/jambandnerd/models/ckplus/`.
  - [x] Develop the necessary data transformations for the `ckplus` model's gap-based features.
  - [x] Create new scripts (`generate_goose_ckplus_predictions.py`, etc.) to run the model and
        store its predictions and accuracy in the unified tables (`predictions_ckplus`, `accuracy_ckplus`).

### Risk Management

| Risk | Probability | Impact | Mitigation Strategy | Owner |
| :--- | :--- | :--- | :--- | :--- |
| Third-party API changes | Medium | High | Implement fallback, monitor changelog | @dev |
| Data model/schema drift | Low | Medium | Schema validation; keep docs current | @dev |
| Model Complexity | Medium | High | Start with simple CK+ model and iterate | @dev |

### Sprint 4: Multi-Band Expansion

**Sprint Goal**: Expand the data pipeline to include a second band (Phish), ensuring the modular architecture supports multi-band data collection seamlessly.

**Dates**: 2025-08-22 to 2025-08-29

**Planned Tasks**:

- [x] **Fix Core Model Logic**: Address regressions in Notebook and CK+ models by implementing the user-provided plain-text logic for windowing, gap calculation, and LTP determination.
- [x] **Implement Phish Data Collector**:
  - [x] Create `phish_songs_raw`, `phish_shows_raw`, `phish_setlists_raw`, and `phish_venues_raw` tables in Supabase.
  - [x] Implement `PhishCollector` class in `src/jambandnerd/data_collection/phish/` to fetch data from the Phish.net API.
  - [x] Create and execute `scripts/run_phish_collection.py` to perform a full backfill of Phish data.

### Sprint Retrospective

*To be filled out at the end of the sprint.*

**What Went Well**

- The unified table refactor was successful and simplified the data model.
- The CK+ model was implemented and automated quickly by following the existing patterns from the Notebook model.
- Database validation logic was integrated smoothly into the existing scripts.

**What Didn't Go Well**
TBD

**Decisions**

- The K selector (10/25/50) is available in the UI. Default remains K=50; users can adjust K for the historical accuracy chart.

**Action Items for Next Sprint**
TBD
