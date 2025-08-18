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
- [x] Implement notebook model transformation (reference show date, last-year window, last-3 exclusion, current_gap).
- [x] Generate and persist top-50 predictions to `goose_notebook_predictions` (unique on band+reference_date+model_version).
- [x] Add metadata logging: `collection_runs`, `predicted_at` timestamps.
- [x] Historical backtesting script and summary table `notebook_accuracy` (last 50 shows).
- [ ] Add nightly automation (GitHub Actions) to run collection, predictions, and accuracy summary.

Risk Management
Risk

Probability

Impact

Mitigation Strategy

Owner

Third-party API changes

Medium

High

Implement fallback, monitor changelog

@dev

Data model/schema drift

Medium

Medium

Add schema validation pre-export; keep schema docs up to date

@dev

Scope creep (adding bands early)

High

Medium

Enforce Goose-first; defer others until verification

@dev

Sprint Retrospective
To be filled out at the end of the sprint.

What Went Well
TBD

What Didn't Go Well
TBD

Action Items for Next Sprint
TBD
