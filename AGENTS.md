# AI Agent Guidance for JamBandNerd

Purpose: Get any AI/automation agent productive in under a minute with minimal context load.
Rule #1: Load only the files in the Boot Order first. Everything else is on-demand.

## 30-Second Quick Ref

* **First time?** Read sections 1 & 5 only
* **Running pipeline:** `uv run python scripts/run_optimized_pipeline.py --band [band]`
* **Stuck?** Check section 6 (Triage Matrix)
* **Session Summary template:** docs/ai_sessions.md
* **Permission model:** Agents can read files and suggest commands; user confirms execution

---

## 1) Boot Order (read in this exact order)

1. **pyproject.toml** — skim [project], [tool.*], and scripts.
2. **README.md** — skim Quick Start and Usage.
3. **docs/pipeline_usage.md** — read the canonical run commands.
4. **docs/architecture.md** — skim the diagram/section headers for system map.
5. **docs/ai_sessions.md** — (only if you're an AI session) skim the session template.

**Do not pre-load other docs.** Open these only when needed:

* CI/CD: docs/github_actions.md
* Web UI: docs/streamlit_deploy.md
* Band-specific fallbacks/parsers: docs/tourwrangler_fallback.md
* Roadmaps/decisions: docs/*.md (targeted sections only)

---

## 2) Roles & Handoffs (ultra-short)

### Navigator (front door)

Classify the request → write a 3–7 line plan → route to one specialist. Keep the plan and scope in the summary.

**Scope:** Navigator handles queries answerable from Boot Order docs (e.g., "how do I run the pipeline?", "where's the config?"). Route only when specialized context (code inspection, API changes, metrics analysis) is needed.

### Researcher

Fetch only current, relevant info. Return a tight brief (bullets + links). Avoid long prose.

### DataOps

Env setup, data paths, secrets, Supabase, GitHub Actions diagnostics. Provide minimal repro steps.

### Feature Engineer

Edit/create features, guard against leakage, keep naming consistent. Provide a diff-style summary.

### Modeler

Train/evaluate, run small sweeps, compare against baselines. Return a compact metrics table.

### Web/App

Streamlit & user-facing tweaks. Optimize launch and state handling first.

### Handoff Format

```text
[Agent] → [Next Agent]: Brief context (1 line) + artifact location + open question

Example:
Modeler → Feature Engineer: R² dropped 0.15 after adding venue_capacity.
Check features/venue.py:45-67 for potential leakage.
```

**Handoff rule:** Each agent updates the running Session Summary with: goal, constraints, commands run, artifacts, next step.

**Escalation threshold:** If unsure after 2 attempts or investigation hits a dead end, hand off to appropriate specialist with full context.

---

## 3) Operating Loop (default)

1. Confirm task & constraints (inputs, band(s), time budget).
2. **Re-confirm** you've loaded Boot Order only (skip the rest).
3. Propose a 3–7 line plan (Navigator).
4. Run the smallest useful command (see Cheat-Sheet).
5. Record minimal artifacts (paths, tables, metrics).
6. Decide: done ↔ iterate ↔ escalate (different agent).
7. Update Session Summary (what changed + next action).

**Context budget:** keep ≤ ~2k tokens loaded; summarize aggressively; link to sources instead of pasting them.

---

## 4) Guardrails

* **Single source of truth:** Use README.md and docs/pipeline_usage.md for how to run things; do not invent commands.
* **Config, not hardcode:** Read from centralized config/env; avoid duplicating constants.
* **Prefer consolidated scripts:** Only drop to band-specific or per-stage scripts when debugging.
* **Minimal diffs:** When proposing changes, show a compact diff or a bulleted change-set, not full files.
* **Repro first:** Any failure report must include exact command(s), directory, and environment notes.
* **Data leakage prevention:** All features MUST respect `reference_date` cutoff. Never include data after `reference_date` in training features (see `src/jambandnerd/transformations/gaps.py`).
* **In-memory transforms:** Do not create intermediate Supabase tables. Use `ModelData` container for all transformations.
* **Band-agnostic core:** Keep band-specific logic in collectors only (`src/jambandnerd/data_collection/{band}/`). Transformations and models work across all bands.

---

## 5) Minimal Command Cheat-Sheet

**End-to-end (all bands):**

```bash
uv run python scripts/run_optimized_pipeline.py --band all
```

**Single band quick test:**

```bash
uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy
```

**Debug single stage for one band:**

```bash
uv run python -m jambandnerd.pipeline.stages.feature_engineering --band goose
```

**Web UI (local):**

```bash
streamlit run src/jambandnerd/web/app.py
```

**Available bands:** `billy` | `cosmic` | `eggy` | `goose` | `phish` | `um` | `wsp`

**Speed up dev loops:** Add `--skip-accuracy` to bypass accuracy checks

**Individual operations:**

```bash
# Generate predictions for specific band/model
uv run python scripts/generate_predictions.py --band goose --model notebook

# Run backtest (accuracy evaluation)
uv run python scripts/run_backtest.py --band goose --model notebook --shows 50

# Diagnose data issues
uv run python scripts/diagnose_band_data.py --band goose

# Verify data freshness
uv run python scripts/verify_data_freshness.py --band goose
```

**Testing:**

```bash
pytest tests/                    # Run all tests
pytest tests/test_models.py      # Specific test file
ruff check src/                  # Lint
black src/                       # Format
```

---

## 6) Triage Matrix (when something breaks)

| Issue Type | Route To | First Diagnostic | Common Fix |
|------------|----------|------------------|------------|
| Install/env errors | DataOps | Python 3.12? UV installed? | `uv venv --python=3.12 && uv pip install .` |
| API/schema changes | Researcher → DataOps | Check `base.py` retry logic? | Update collector rate limits/headers |
| Collection failures | DataOps | API keys in .env? | Verify `SUPABASE_URL`, `SUPABASE_KEY`, `PHISH_API_KEY` |
| Prediction errors | Feature Engineer | Raw tables populated? | Run `diagnose_band_data.py --band {band}` |
| Data leakage suspected | Feature Engineer | `reference_date` filtering? | Verify `transformations/gaps.py` date cutoff |
| Metrics regressions | Modeler → Feature Engineer | Recent feature changes? | Run backtest: `run_backtest.py --shows 10` |
| UI/state issues | Web/App | Supabase connection? | Check browser console, `verify_data_freshness.py` |
| Cron/CI/CD failures | DataOps | Secrets configured? | Check `.github/workflows/daily-pipeline.yml` |

---

## 7) Output Format (what each agent must leave behind)

### Required Elements

1. **1–3 bullets:** what changed, where it lives (path/table), and why.
2. **Short code/command block:** exact steps to reproduce.
3. **Tiny artifact table** (if applicable):

```markdown
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| R²     | 0.847  | 0.823 | -0.024 |
| Rows   | 1,243  | 1,243 | —      |
```

1. **Next step:** 1 line (do X / review Y / ship Z).

---

## 8) What NOT to load on startup

* ❌ Entire docs/ folder, decision logs, or full PRDs
* ❌ Long historical discussions, old experiment notebooks, or verbose run logs
* ❌ Historical experiment results or archived metrics
* ❌ Any file not listed in the Boot Order

---

## 9) Common Anti-Patterns (DON'T)

**Process anti-patterns:**
* ❌ Loading all docs upfront "just in case"
* ❌ Writing multi-file solutions without confirming scope
* ❌ Proposing changes without running the current state first
* ❌ Pasting full file contents instead of diffs
* ❌ Inventing commands not documented in pipeline_usage.md
* ❌ Continuing past 2 failed attempts without escalating

**Technical anti-patterns:**
* ❌ Adding features to `transformations/gaps.py` without respecting `reference_date`
* ❌ Creating new intermediate Supabase tables (use in-memory transforms)
* ❌ Hardcoding band names (use `get_all_bands.py` for discovery)
* ❌ Adding band-specific logic to transformation pipeline
* ❌ Skipping backtests after model changes
* ❌ Modifying raw table schemas without updating all band collectors

---

## 10) Quick Architecture Context (load only if modifying core)

**Data Flow:**
```
Band Sources → Collection (API/Scrape) → Raw Storage (Supabase) →
In-Memory Transform → Models (Notebook/CK+) → Predictions (Supabase) → Web UI
```

**Key modules:**
* `src/jambandnerd/data_collection/` - Band-specific collectors inheriting from `BaseCollector`
* `src/jambandnerd/transformations/gaps.py` - `generate_model_data()` produces `ModelData` container
* `src/jambandnerd/models/` - `PredictionModel` base class, `notebook/` and `ckplus/` implementations
* `src/jambandnerd/db/` - Supabase connection (`connection.py`), operations (`operations.py`)
* `scripts/` - Entry points: `run_optimized_pipeline.py`, `generate_predictions.py`, `run_backtest.py`

**Critical patterns:**
* `ModelData` container: `historical_plays`, `master_feature_set`, `reference_date`, `reference_index`
* Raw tables: `{band}_shows_raw`, `{band}_setlists_raw` (standardized schemas)
* Prediction tables: Cross-band unified `predictions`, `backtest_accuracy`
* WSP special: Scrapes everydaycompanion.com with TourWrangler.com fallback

---

## Version

Last updated: 2025-12-01
Maintained by: JamBandNerd core team
