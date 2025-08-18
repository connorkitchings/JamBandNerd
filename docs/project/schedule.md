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

Progress Update (2025-08-17)

- [x] Implement Goose raw data collection and load to Supabase (`goose_songs_raw`, `goose_shows_raw`, `goose_setlists_raw`).
- [x] Update `docs/schemas/goose_api.md` to match actual API response wrapper and types.
- [x] Resolve uniqueness and schema issues (introduce `api_song_id`, drop `song_length_seconds`).
- [ ] FIRST NEXT SESSION: Review elgoose API query parameters to ensure we only collect band=Goose data (exclude non-Goose entries like Vasudo).
- [ ] Add nightly automation (GitHub Actions) to run Goose collection.
- [ ] Begin transformation layer for standardized Goose tables.

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
