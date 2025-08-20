Implementation Schedule

Instructions: This document is the tactical plan for the project. Use it to plan sprints,
track tasks, and manage risks. It answers the questions "Who, when, and on what?"

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
- [ ] Add nightly automation (GitHub Actions) to run collection, predictions, and accuracy summary.

Action Items for Next Sprint

- Begin Sprint 3 tasks.

---

### Sprint 3: Refactoring & CK+ Model

**Sprint Goal**: Refactor the database schema to use unified prediction tables, implement
robust data validation, and add the new `ckplus` model for Goose.

**Dates**: 2025-08-20 to 2025-08-28

**Planned Tasks**:

- [ ] **Refactor to Unified Tables**:
  - [ ] Modify `scripts/generate_goose_predictions.py` to write to a unified `predictions_notebook`
        table, adding a `band` column.
  - [ ] Update `scripts/save_notebook_accuracy.py` to write to a unified `notebook_accuracy` table.
  - [ ] Adjust `src/jambandnerd/web/app.py` to read from the unified table and filter by band.
  - [ ] Update `ADR-003` to reflect the decision to use unified tables.
- [ ] **Implement Database Validation**:
  - [ ] Implement schema validation logic in `src/jambandnerd/db/validation.py`.
  - [ ] Add a utility to `src/jambandnerd/db/operations.py` to fetch table schemas from Supabase.
  - [ ] Integrate validation checks into the data collection and prediction scripts before writing
        to the database.
- [ ] **Implement CK+ Model**:
  - [ ] Create the core `ckplus` model logic in `src/jambandnerd/models/ckplus/`.
  - [ ] Develop the necessary data transformations for the `ckplus` model's gap-based features.
  - [ ] Create new scripts (`generate_goose_ckplus_predictions.py`, etc.) to run the model and
        store its predictions and accuracy in the unified tables (`predictions_ckplus`, `accuracy_ckplus`).

### Risk Management

| Risk | Probability | Impact | Mitigation Strategy | Owner |
| :--- | :--- | :--- | :--- | :--- |
| Third-party API changes | Medium | High | Implement fallback,<br>monitor changelog | @dev |
| Data model/schema drift | Low | Medium | Add schema validation pre-export;<br>keep schema docs up to date | @dev |
| Model Implementation Complexity | Medium | High | Start with a simple version of the CK+ model and iterate | @dev |

### Sprint Retrospective

*To be filled out at the end of the sprint.*

**What Went Well**
TBD

**What Didn't Go Well**
TBD

**Action Items for Next Sprint**
TBD
