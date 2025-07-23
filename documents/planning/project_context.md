# JamBandNerd Project Context

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

**High-Level Summary:**
JamBandNerd is organized around modular data collection pipelines (one per band), unified logging,
and standardized analytics/prediction modules.

**System Diagram:**

```text
+---------------------------+      +-------------------+      +---------------------+
| Data Collection Pipelines | ---> | Data Storage/Logs | ---> | Analytics/Models    |
| (Phish, Goose, UM, WSP)  |      | (CSV, JSON, Logs) |      | (CK+, Notebook)     |
+--------------------------+      +-------------------+      +---------------------+
```

**Folder Structure:**

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
