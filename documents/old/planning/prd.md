Product Requirements Document (PRD)
Instructions: This document is the single source of truth for what we are building and why.
It should be updated as the project evolves, especially the DECISION LOG.

PROJECT
JamBandNerd

GOAL
A modular data science platform for collecting, processing, and predicting jam band setlists.
JamBandNerd enables robust, parallelized data pipelines and predictive analytics for major jam
bands, supporting research and fan engagement.

For architecture, tech stack, and setup details, see project_context.md.

> 📚 For a high-level entry point and links to all documentation, see [README.md](../../README.md).

USERS & USER STORIES
Primary Persona
Name: Jamie Fan

Role: Jam band enthusiast & data explorer

Pain Points: Wants to analyze setlists, discover trends, and predict future shows but lacks easy
access to clean, up-to-date data.

Goals: Explore band histories, run predictions, and share insights with the community.

Core User Stories

- As a jam band fan, I want to view historical setlists and song statistics so that I can better
  understand band trends.
- As a data scientist, I want to access standardized, clean data for all bands so that I can build
  and test predictive models.
- As a developer, I want to run all pipelines easily and see unified logs so that I can maintain
  and extend the platform.

FEATURES & SCOPE
Must-Have (MVP)

- Automated data collection pipelines for Phish, Goose, Umphrey's McGee (UM), and
  Widespread Panic (WSP)
- Unified, timestamped logging for all pipelines
- Standardized data outputs for analytics and ML
- Prediction models for setlist generation (CK+, Notebook)
- Orchestration scripts for parallel pipeline execution

See [Scope Appendix](./scope_appendix.md) for Post-MVP features and Out of Scope items.

RISKS & ASSUMPTIONS
Key Assumptions

- Band APIs or source websites may change or rate-limit access (Mitigation: monitor and implement fallbacks)
- Data quality varies by band/source (Mitigation: validation scripts, manual review)
- Prediction accuracy depends on data completeness and model tuning

Technical Risks
Risk

Probability

Impact

Mitigation

Third-party API failure

Medium

High

Implement fallback; see [IMPL-task:ID]

Database performance

Low

Medium

Optimize queries during development

SYSTEM & SECURITY
System Diagram

```text
+--------------------------+      +-------------------+      +---------------------+
| Data Collection Pipelines | ---> | Data Storage/Logs | ---> | Analytics/Models    |
| (Phish, Goose, UM, WSP)  |      | (CSV, JSON, Logs) |      | (CK+, Notebook)     |
+--------------------------+      +-------------------+      +---------------------+
```

Security & Privacy
PII Handling: No personal user data collected; all data is public setlist and show info

Enforcement: All features handling data must adhere to the [QG:SecurityReview] checklist in quality_gates.md.

LOGS & HISTORY
Decision Log
Date

Decision

Rationale

Reversible?

2025-07-01

Standardized all pipeline outputs to CSV in `data/<band>/collected/`

Ensures compatibility with analytics tools and ML workflows

Yes

2025-07-15

Use React for frontend

Team familiarity, large ecosystem

Yes

2025-07-16

Use PostgreSQL for DB

ACID compliance and JSONB support needed

Difficult

Version History
Version

Date

Summary of Changes

Author

v0.1

2025-07-01

Initial draft for JamBandNerd

@connorkitchings

v1.0

2025-07-21

Finalized requirements for MVP launch

@connorkitchings
