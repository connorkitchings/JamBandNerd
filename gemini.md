# Gemini CLI Guidance for JamBandNerd

Purpose: Get Gemini (via CLI) productive in under a minute with minimal context load.
Rule #1: Load only the files in the Boot Order first. Everything else is on-demand.

## 30-Second Quick Ref

* **First time?** Read sections 1 & 4 only
* **Running pipeline:** `uv run python scripts/run_optimized_pipeline.py --band [band]`
* **Available bands:** `billy` | `cosmic` | `eggy` | `goose` | `phish` | `um` | `wsp`
* **Stuck?** Check section 6 (Triage Matrix)
* **CLI workflow:** Gemini suggests commands → user runs them → Gemini analyzes output
* **Critical concept:** All features must respect `reference_date` cutoff for data leakage prevention

---

## 1) Boot Order (read in this exact order)

1. **pyproject.toml** — skim [project], [tool.*], and scripts.
2. **README.md** — skim Quick Start and Usage.
3. **docs/pipeline_usage.md** — read the canonical run commands (if exists).
4. **docs/architecture.md** — skim the diagram/section headers for system map (if exists).

**Do not pre-load other docs.** Open these only when needed:

* CI/CD: docs/github_actions.md
* Web UI: docs/streamlit_deploy.md
* Band-specific fallbacks/parsers: docs/tourwrangler_fallback.md
* Roadmaps/decisions: docs/*.md (targeted sections only)

**If docs don't exist:** Fall back to README.md + this file + on-demand code inspection.

---

## 2) CLI Operating Loop

1. **Confirm task & constraints** (inputs, band(s), time budget).
2. **Re-confirm** you've loaded Boot Order only (skip the rest).
3. **Propose a 3–5 line plan.**
4. **Suggest the smallest useful command** (see Cheat-Sheet below).
5. **Wait for user to run command and paste output.**
6. **Analyze output**, record artifacts (paths, metrics).
7. **Decide:** done ↔ iterate ↔ suggest next command.

**Context budget:** keep ≤ ~2k tokens loaded; summarize aggressively; link to sources instead of pasting them.

**CLI-specific notes:**
- Never execute commands yourself—always suggest and wait for user
- Provide exact command syntax with all required flags
- After user pastes output, extract key info (errors, metrics, paths)
- If output is verbose, ask user to filter with `grep`, `head`, or `tail`

---

## 3) Guardrails

1. **Single source of truth:** Use README.md for commands; do not invent.
2. **Config, not hardcode:** Read from centralized config/env; avoid duplicating constants.
3. **Prefer consolidated scripts:** Only drop to band-specific scripts when debugging.
4. **Minimal diffs:** Show compact diffs or bulleted change-sets, not full files.
5. **Repro first:** Any failure report must include exact command(s), directory, and environment.
6. **Data leakage prevention:** All features MUST respect `reference_date` cutoff (see `transformations/gaps.py`).
7. **In-memory transforms:** Do not create intermediate Supabase tables. Use `ModelData` container.
8. **Band-agnostic core:** Keep band-specific logic in collectors only.

---

## 4) Minimal Command Cheat-Sheet

**End-to-end (all bands):**

```bash
uv run python scripts/run_optimized_pipeline.py --band all
```

**Single band quick test:**

```bash
uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy
```

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

**Web UI (local):**

```bash
uv run streamlit run src/jambandnerd/web/app.py
```

**Testing:**

```bash
pytest tests/                    # Run all tests
pytest tests/test_models.py      # Specific test file
ruff check src/                  # Lint
black src/                       # Format
```

**Environment setup:**

```bash
uv venv --python=3.12
source .venv/bin/activate
uv pip install .
uv pip install -e ".[dev]"       # For development
```

**Speed up dev loops:** Add `--skip-accuracy` to bypass accuracy checks

---

## 5) CLI Interaction Pattern Examples

**Example 1: User reports prediction error**

```
Gemini: Let's diagnose this. Please run:
  uv run python scripts/diagnose_band_data.py --band goose

User: [pastes output showing "No shows found in goose_shows_raw"]

Gemini: The raw table is empty. Let's collect data first:
  uv run python scripts/run_goose_collection.py

User: [pastes successful collection output]

Gemini: Good. Now generate predictions:
  uv run python scripts/generate_predictions.py --band goose --model notebook
```

**Example 2: User wants to add new feature**

```
Gemini: Before modifying, let's run current baseline:
  uv run python scripts/run_backtest.py --band goose --model notebook --shows 10

User: [pastes metrics: Top-10 accuracy: 0.42]

Gemini: Baseline recorded. Now suggest your feature change. After implementation:
  1. Run the same backtest command
  2. Compare metrics
  3. Verify transformations/gaps.py respects reference_date
```

---

## 6) Triage Matrix (when something breaks)

| Issue Type | First Diagnostic | Suggested Command |
|------------|------------------|-------------------|
| Install/env errors | Python 3.12? UV installed? | `uv venv --python=3.12 && uv pip install .` |
| Collection failures | API keys in .env? | `cat .env \| grep -E 'SUPABASE\|PHISH'` (user runs) |
| Prediction errors | Raw tables populated? | `uv run python scripts/diagnose_band_data.py --band {band}` |
| Data leakage suspected | reference_date filtering? | Inspect `transformations/gaps.py`, check date filters |
| Accuracy regressions | Recent feature changes? | `uv run python scripts/run_backtest.py --band {band} --shows 10` |
| Web UI issues | Supabase connection? | `uv run python scripts/verify_data_freshness.py --band {band}` |
| GitHub Actions failures | Secrets configured? | Ask user to check GitHub repo Settings → Secrets |

---

## 7) Output Format (what Gemini should provide)

### After each command analysis:

1. **Status:** Success / Partial / Failed
2. **Key findings:** 1–3 bullets of what the output reveals
3. **Extracted artifacts:** Paths, table names, metrics (if applicable)
4. **Next command:** Specific command to run next, or declare done

**Example output:**

```
Status: Success
Key findings:
  - goose_shows_raw contains 487 shows
  - Latest show: 2024-11-15
  - All required columns present

Artifacts:
  - Table: goose_shows_raw (487 rows)
  - Latest date: 2024-11-15

Next command:
  uv run python scripts/generate_predictions.py --band goose --model notebook
```

---

## 8) What NOT to load on startup

* ❌ Entire docs/ folder, decision logs, or full PRDs
* ❌ Long historical discussions, old experiment notebooks, or verbose run logs
* ❌ Historical experiment results or archived metrics
* ❌ Any file not listed in the Boot Order

---

## 9) Common Anti-Patterns (DON'T)

**Process anti-patterns:**
* ❌ Trying to execute commands (always suggest, never execute)
* ❌ Loading all docs upfront "just in case"
* ❌ Proposing changes without running the current state first
* ❌ Pasting full file contents instead of diffs
* ❌ Inventing commands not documented in README.md

**Technical anti-patterns:**
* ❌ Adding features to `transformations/gaps.py` without respecting `reference_date`
* ❌ Creating new intermediate Supabase tables (use in-memory transforms)
* ❌ Hardcoding band names (use `get_all_bands.py` for discovery)
* ❌ Adding band-specific logic to transformation pipeline
* ❌ Skipping backtests after model changes
* ❌ Modifying raw table schemas without updating all band collectors

---

## 10) Quick Architecture Context (load only if needed)

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

**Environment variables required:**
* `SUPABASE_URL` - Supabase project URL
* `SUPABASE_KEY` - Supabase service key
* `PHISH_API_KEY` - Optional, only for Phish data collection

---

## Version

Last updated: 2025-12-01
Maintained by: JamBandNerd core team
