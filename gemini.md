# Gemini CLI Guidance for JamBandNerd

Purpose: Get Gemini (via CLI) productive in under a minute with minimal context load.
Rule #1: Load only the files in the Boot Order first. Everything else is on-demand.

## 30-Second Quick Ref

* **First time?** Read sections 1 & 4 only
* **Running pipeline:** `uv run python scripts/run_optimized_pipeline.py --band [band]`
* **Stuck?** Check section 5 (Triage Matrix)
* **CLI workflow:** Gemini suggests commands → user runs them → Gemini analyzes output

---

## 1) Boot Order (read in this exact order)

1. **pyproject.toml** — skim [project], [tool.*], and scripts.
2. **README.md** — skim Quick Start and Usage.
3. **docs/pipeline_usage.md** — read the canonical run commands.
4. **docs/architecture.md** — skim the diagram/section headers for system map.

**Do not pre-load other docs.** Open these only when needed:

* CI/CD: docs/github_actions.md
* Web UI: docs/streamlit_deploy.md
* Band-specific fallbacks/parsers: docs/tourwrangler_fallback.md
* Roadmaps/decisions: docs/*.md (targeted sections only)

---

## 2) CLI Operating Loop

1. Confirm task & constraints (inputs, band(s), time budget).
2. **Re-confirm** you've loaded Boot Order only (skip the rest).
3. Propose a 3–5 line plan.
4. **Suggest the smallest useful command** (see Cheat-Sheet).
5. Wait for user to run command and paste output.
6. Analyze output, record artifacts (paths, metrics).
7. Decide: done ↔ iterate ↔ escalate.

**Context budget:** keep ≤ ~2k tokens loaded; summarize aggressively; link to sources instead of pasting them.

---

## 3) Guardrails

1. **Single source of truth:** Use README.md and docs/pipeline_usage.md for commands; do not invent.
2. **Config, not hardcode:** Read from centralized config/env; avoid duplicating constants.
3. **Prefer consolidated scripts:** Only drop to band-specific scripts when debugging.
4. **Minimal diffs:** Show compact diffs or bulleted change-sets, not full files.
5. **Repro first:** Any failure report must include exact command(s), directory, and environment.

---

## 4) Minimal Command Cheat-Sheet

**End-to-end (all bands):**

```bash
uv run python scripts/run_optimized_pipeline.py --band all
