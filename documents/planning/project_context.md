# # JamBandNerd Project Context

---

**Onboarding/AI Session Context:**
To ensure continuity and context for all contributors (human and AI), always start a session by
reviewing this document, the latest dev_log, and the current plan. At the end of each session,
update the dev_log and plan with any key changes, blockers, or decisions. This ensures seamless
handoff and rapid onboarding for future sessions
---

_This is a living document defining JamBandNerd’s technical foundation. Update as the architecture
or technology stack evolves._

## 1. Overview

**Project Goal:**
A modular Python-based platform for collecting, processing, and predicting jam band setlists,
with robust orchestration and analytics.

**Repository:**
[JamBandNerd GitHub](https://github.com/connorkitchings/JamBandNerd)

## 2. Architecture

### High-Level Summary

JamBandNerd is organized around modular data collection pipelines (one per band), unified logging,
and standardized analytics/prediction modules.

### System Diagram

```text
+---------------------------+      +-------------------+      +---------------------+
| Data Collection Pipelines | ---> | Data Storage/Logs | ---> | Analytics/Models    |
| (Phish, Goose, UM, WSP)  |      | (CSV, JSON, Logs) |      | (CK+, Notebook)     |
+--------------------------+      +-------------------+      +---------------------+
```

### Folder Structure

```text
JamBandNerd/
├── data/                  # Canonical output data (collected, processed, predictions)
├── logs/                  # All band and pipeline logs
├── scripts/               # Orchestration and runner scripts
├── src/
│   └── jambandnerd/
│       ├── data_collection/
│       │   ├── phish/
│       │   ├── goose/
│       │   ├── um/
│       │   └── wsp/
│       └── predictions/
│           ├── ckplus_model/
│           └── notebook_model/
├── requirements.txt
├── README.md
└── ...
```

## 3. Technology Stack

| Category     | Technology         | Version   | Notes                              |
| ------------|------------------- |---------- |------------------------------------|
| Core        | Python             | 3.9+      | Data pipelines, orchestration      |
| Data        | pandas, requests   | latest    | Data processing, web/API access    |
| Logging     | logging            | stdlib    | Unified, timestamped logs          |
| ML/Analysis | numpy, scikit-learn| latest    | Prediction models                  |
| CLI         | Typer              | latest    | Unified CLI for orchestration      |
| Testing     | pytest             | latest    | Unit/integration tests             |

## 4. Setup & Environment

**Prerequisites:**

- Python 3.12.x (recommended for lxml compatibility)
- [uv](https://github.com/astral-sh/uv) (recommended; install with `pip install uv` if not present)

**Setup Instructions:**

```bash
git clone https://github.com/connorkitchings/JamBandNerd.git
cd JamBandNerd
uv venv --python=3.12
source .venv/bin/activate
# (If needed) Install pip:
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
.venv/bin/python get-pip.py
rm get-pip.py
# Install UV if not present:
.venv/bin/python -m pip install uv
# Install all dependencies:
.venv/bin/uv pip install .
# If using Phish pipeline, set up .env with PHISH_API_KEY
```

**lxml and Python Version Compatibility:**

- lxml is pinned to 4.9.3, which is not compatible with Python 3.13+.

- Use Python 3.12.x for a smooth setup.

**Troubleshooting:**

- If you see pip errors, run the pip install step above.

- If you see lxml build errors, check your Python version.

- For additional help, see README.md or open an issue.

**Running Pipelines:**

---

**End of Session:**
If you have completed significant work, summarize key actions, blockers, and decisions in the
dev_log and update the plan as needed. Always link relevant artifacts and cross-reference PRD,
knowledge_base, and quality_gates as appropriate for traceability
---

```bash
python3 scripts/run_all_pipelines.py
```

**Logs:**

- All logs are stored in `logs/` with `[MM-DD-YYYY HH:MM:SS] LEVEL: message` format.

## 5. Standards & Practices

**Version Control:**

- Feature branches for all work (e.g., `feature/add-goose-pipeline`)
- Conventional Commits for messages

**Coding Standards:**

- Python: formatted with black, linted with ruff
- All code must include type hints and docstrings (see [project rules](../_current_context.md))

**Testing Strategy:**

- Unit and integration tests with pytest
- All new features must include corresponding tests
- Code coverage should not decrease (see [QG:PreMerge] in `quality_gates.md`)

**Documentation:**

- All modules and scripts must have docstrings and usage examples
- Cross-document links (e.g., `[PRD-feat:A]`) should be maintained

---

_Update this document whenever the tech stack, architecture, or standards change._

## 6. Session Kickoff Prompt

This is a template prompt to start a new AI session. Copy, paste, and fill in the bracketed
information to bring the AI up to speed quickly.

Hello. We are continuing our work on the 'JamBandNerd' project. Your role is my AI co-pilot, and we
will be following the Vibe Coding System.

To get up to speed, please perform the following steps:

1. **Review the Project Foundation:**
    - `documents/planning/project_context.md`: To understand the architecture and tech stack.
    - `documents/planning/prd.md`: To understand the project goals and features.
    - `pyproject.toml`: To understand the project dependencies and configuration.

2. **Review the Current Sprint Status:**
    - `documents/planning/implementation_schedule.md`: To see the current sprint goal and all open tasks.

3. **Review the Last Session's Handoff:**
    - `documents/execution/dev_logs/[YYYY-MM-DD].md`: Please review the most recent dev log entry to
      understand exactly where we left off. Pay close attention to the 'Session Handoff' section.
    - If you cannot find a dev log for today, check all dev logs for today's date with session
      numbers ('_01', '_02', '_03', etc.) to find the latest handoff.

4. **Prepare for Today's Task:**
    - **Our focus today is:** Review `documents/planning/implementation_schedule.md` to see the
      current sprint goal and all open tasks.

Once you have completed this review, please confirm you are ready, and we will begin.

## 7. Session Wrap-up Prompt

This is a template prompt to end a development session cleanly. Copy, paste, and fill in the
bracketed information.

We are now ending our development session for today. To ensure we maintain our project context and
prepare for a smooth handoff, please perform the following wrap-up tasks:

1. **Summarize Session Accomplishments:**
    - **Task Completed:** `[IMPL-task:ID] - [Brief description of the task]`
    - **Key Outcomes:** `[List the 1-3 main achievements of the session, e.g., 'Successfully
     connected to the phish.net API v5: The primary data source for all Phish-related information,
     including shows, setlists, songs, and venues.']`

2. **Identify Blockers and Learnings:**
    - **Blockers Encountered:** `[Describe any issues that are preventing progress, e.g., 'The API
     is rate-limiting our requests.']`
    - **New Learnings/Patterns:** `[Mention any new solutions or patterns discovered that should be
     added to the knowledge_base.md, e.g., 'Found a more efficient way to parse JSON responses.']`

3. **Define Next Steps:**
    - **Immediate Next Task:** `[What is the very next thing to do? e.g., 'Refactor the API client
     to handle rate-limiting.']`

4. **Generate the Dev Log:**
    - Based on the information above, please generate a complete dev log entry for today, `[YYYY-MM-DD]`.
    - Use the template from `documents/execution/dev_log_template.md`.
    - **Important:** Check if a dev log already exists for today's date in the
    `/documents/execution/dev_logs/` directory. If it does, create the new log with sequential numbering:
      - First log of the day: `[YYYY-MM-DD].md`
      - Second log of the day: `[YYYY-MM-DD]_02.md`
      - Third log of the day: `[YYYY-MM-DD]_03.md`
      - And so on...
    - Create this log as a new file inside the `/documents/execution/dev_logs/` directory with the
      appropriate filename based on existing logs for that date.

After you have generated the dev log, I will review it, make any final edits, and commit it to our repository.
