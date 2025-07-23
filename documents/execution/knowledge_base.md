# JamBandNerd Knowledge Base

> **Tooling Note:** JamBandNerd recommends [uv](https://github.com/astral-sh/uv) as the Python
package manager for all environment setup. Use Python 3.12.x for best compatibility (especially
for lxml). Install all dependencies with `uv pip install .` (from `pyproject.toml`).

A structured, flexible workflow for taking an idea from concept to delivery, designed for efficient
and context-aware collaboration between a developer and an AI assistant, with a focus on jam band
data pipelines, analytics, and predictive modeling.

## Core Philosophy

JamBandNerd's workflow is designed to maximize transparency, reproducibility, and rapid iteration.

The following principles guide all work:

* **Documentation-first:** All major decisions and steps are documented.
* **Automated, reproducible environments:** Use `uv` and `pyproject.toml` for all dependencies.
* **Separation of concerns:** Data collection, processing, modeling, and publishing are modular.
* **Continuous validation:** Testing and linting are integrated into the workflow.

## Documentation Ecosystem

The JamBandNerd Documentation System is built on a set of specialized Markdown documents designed
to separate concerns and maintain clarity.

### Strategic & Planning Documents

#### prd.md

The "What" & "Why": Defines JamBandNerd project goals, user personas, core features (band pipelines,
analytics, prediction models), scope, and success metrics. The single source of truth for the
project's vision.

* At project inception.
* During planning phases.
* When a feature's purpose is in question.

#### project_context.md

The "Foundation": A static reference for JamBandNerd's technical landscape. Contains setup,
architecture, tech stack, and coding standards (Python, orchestration scripts, logging, etc.).

* When onboarding.
* When architectural questions arise.
* For environment setup.

#### dev_log_template.md

Purpose

When to Use

dev_log_template.md

The "Session History": A chronological log of JamBandNerd development sessions. Captures what was
done (e.g., pipeline runs, model improvements), decisions made, and a handoff for the next session.

* At the beginning and end of every coding session. This is the most frequently updated document.

#### knowledge_base.md

"Institutional Memory": A curated collection of reusable patterns, solutions (e.g., data normalization,
unified logging), and valuable AI prompts discovered during the JamBandNerd project.

* When a reusable solution is created. When a particularly effective AI prompt is found.

#### quality_gates.md

"The Standard": A checklist and dashboard for ensuring quality, from code style and test coverage to
security validation, tailored for JamBandNerd's Python pipelines and analytics.

## Cross-Document Linkage System

To connect these documents into a cohesive whole, JamBandNerd uses a standardized reference system.

[PRD-decision:YYYY-MM-DD]: Links to a specific decision in the prd.md.
[IMPL-task:ID]: Links to a task in the implementation_schedule.md.
[LOG:YYYY-MM-DD]: Links to a specific dev_log.md entry.
[KB:PatternName]: Links to a pattern in the knowledge_base.md.
[QG:CheckpointName]: Links to a checkpoint in the quality_gates.md.

## The Phased Workflow

JamBandNerd follows a phased workflow for efficient, context-aware development:

### Phase 0: Idea Validation & Scope Check

* Feasibility Audit: Is the idea viable, exciting, and achievable within a reasonable timeframe?
* AI Stress Test: Prompt the AI to identify potential failures, hard parts, and simpler alternatives.
* Go/No-Go: Create the initial prd.md with a clear, one-sentence goal.

### Phase 1: High-Level Planning & Setup

* Flesh out prd.md: Define user stories, features, and success metrics.
* Establish project_context.md: Define the initial tech stack, architecture, and standards.
* Set up Version Control: Initialize git repository with branch and commit message conventions.

### Phase 2: Iterative Development & User Testing

* Session Kickoff: Review the "Session Handoff" from the last dev_log_template.md entry.
* Action: Provide the AI with the relevant documents for the day's task.
* Development Cycle: Generate code and tests with AI assistance, review and validate output, run
  code against quality_gates.md checklists.
* User Testing: Integrate feedback loops as needed.
* Session End: Update the dev_log_template.md with a new entry, update knowledge_base.md with new
  patterns.

### Phase 3: MVP Delivery & Maintenance

* Final Review: Ensure all core features from the prd.md are complete and tested.
* Deployment: Deploy the MVP.
* Retrospective: Review the dev_log_template.md and project_context.md to analyze the development
  process.

## Automation & Tooling

JamBandNerd uses automation scripts (e.g., orchestration CLI, cross-link validation) to streamline
development and documentation.
