# JamBandNerd Onboarding Guide

Welcome to the JamBandNerd project! This guide provides everything you need to get your development environment set up and start contributing.

## 1. Environment Setup

**Prerequisites:**

*   Python 3.12.x (recommended for `lxml` compatibility)
*   [uv](https://github.com/astral-sh/uv) (a fast Python package installer)

**Setup Instructions:**

```bash
# 1. Clone the repository
git clone https://github.com/connorkitchings/JamBandNerd.git
cd JamBandNerd

# 2. Create a virtual environment using uv
uv venv --python=3.12

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Install all project dependencies with uv
uv pip install .

# 5. Set up your environment variables
# Copy the example .env file
cp .env.example .env

# Edit the .env file with your credentials for Supabase and any APIs
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_key
# PHISH_API_KEY=your_phish_net_key
```

Your environment is now ready.

## 2. AI Session Kickoff

To ensure continuity and context for all contributors (human and AI), always start a session by gathering the latest context. This ensures you are aligned with the project's current state.

**Kickoff Prompt Template:**

Copy, paste, and fill in the bracketed information to bring an AI assistant up to speed quickly.

```
Hello. We are continuing our work on the 'JamBandNerd' project.

To get up to speed, please perform the following steps:

1.  **Review the Project Foundation:**
    *   `documents/planning/project_context.md`: To understand the architecture and tech stack.
    *   `documents/planning/PRD.md`: To understand the project goals and features.
    *   `pyproject.toml`: To understand the project dependencies and configuration.

2.  **Review the Current Sprint Status:**
    *   `documents/planning/implementation_schedule.md`: To see the current sprint goal and all open tasks.

3.  **Review the Last Session's Handoff:**
    *   `documents/execution/dev_logs/[YYYY-MM-DD].md`: Please review the most recent dev log entry to understand exactly where we left off. Pay close attention to the 'Session Handoff' section.

4.  **Prepare for Today's Task:**
    *   **Our focus today is:** [Describe the main goal for the session, referencing the implementation_schedule.md]

Once you have completed this review, please confirm you are ready, and we will begin.
```
