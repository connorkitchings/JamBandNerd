# 2026-04-13 Comprehensive Alignment Audit

## Executive Summary

This audit reviewed JamBandNerd as one operating system: strategy and product docs, contributor guidance, command surfaces, pipeline code, model metadata, website behavior, GitHub Actions workflows, and sampled live Supabase state.

The main conclusion is that the project substance is stronger than the active documentation suggests. The registry-based model platform, dynamic band registry, replay lineage, test surface, and website smoke coverage are all in materially better shape than several active docs imply. The main risk is not missing implementation. The main risk is truth drift between code, docs, metadata, and live operations.

### Immediate priorities

- Unify the product version contract across Python, web, displayed site version, and docs.
- Canonicalize model lifecycle state so CK+ and Deal are described the same way everywhere.
- Resolve the Streamlit status contradiction: either restore a real maintained legacy surface or archive/remove the remaining active references.
- Restore a working docs-build path or stop documenting `mkdocs` commands until the config exists again.
- Treat WSP Notebook freshness as a live operations issue, not a documentation issue.

## Evidence Snapshot

| Check | Result | Evidence |
|---|---|---|
| Branch / worktree | `dev`, clean at audit start | `git branch --show-current`, `git status --short` |
| Python test surface | `251` tests collected | `uv run pytest --collect-only -q` |
| Website smoke inventory | `22` tests listed across desktop/mobile | `npm run test:web:smoke:list` |
| Website smoke execution | `11 passed`, `11 skipped` | `npm run test:web:smoke` |
| Live data access | Successful | `validate_prediction_tables.py`, `validate_accuracy_tables.py`, schema probe, `fetch_active_bands()` |
| Active bands in live registry | `6` active bands | `bands` table via `fetch_active_bands()` |

### Sample live-data findings

- `predictions_notebook` was fresh for Goose and Phish, but stale for WSP in the sampled run.
- `predictions_deal` was fresh for Goose, Phish, and WSP in the sampled run.
- Notebook accuracy was fresh for Goose and Phish, but stale for WSP in the sampled run.
- Deal accuracy was fresh for Goose, Phish, and WSP in the sampled run.
- Live schemas were confirmed for `bands`, `predictions_notebook`, `predictions_deal`, `prediction_songs`, `historical_prediction_runs`, `accuracy_per_show`, `notebook_accuracy`, and `accuracy_deal`.

## Healthy Foundations

- The repo has a meaningful automated verification surface: `251` pytest cases plus website smoke coverage.
- Model orchestration is structured around `src/jambandnerd/models/metadata.py` and `registry.py`, which is the right direction for rollout control and drift reduction.
- Replay lineage is implemented in the data model through `historical_prediction_runs` and linked `accuracy_per_show.prediction_run_id`.
- The website already reads dynamic band metadata from the `bands` table rather than hardcoding a band list in route logic.
- Tracked-file hygiene is reasonably good. Common generated artifacts are ignored rather than committed.

## Canonical Truth Map

| Domain | Canonical Source Of Truth | Supporting Surfaces | Audit Note |
|---|---|---|---|
| Commands and operator workflow | `README.md`, `docs/user/pipeline_usage.md`, root `package.json`, `scripts/README.md` | `.codex/QUICKSTART.md`, onboarding docs | This is mostly the right split, but docs-site commands are currently broken. |
| Architecture and data contract | `docs/contributor/developer_guide/architecture.md`, `docs/reference/specifications/data_strategy.md` | `scripts/common.py`, `transformations/normalization.py`, `transformations/gaps.py`, `run_optimized_pipeline.py` | `data_strategy.md` is closest to the real implementation shape. |
| Model lifecycle and capability flags | `src/jambandnerd/models/metadata.py`, `src/jambandnerd/models/registry.py` | `apps/web/src/lib/config.ts`, model docs | Registry and metadata are authoritative. Website config is presentation metadata only. |
| Live website behavior | `apps/web/src/lib/data.ts`, `apps/web/src/lib/config.ts`, `apps/web/src/lib/data/*.ts` | `docs/operations/website_delivery.md`, smoke tests | Website behavior is ahead of several docs, especially around Deal promotion. |
| Ops workflow and schedules | `.github/workflows/*.yml` | `docs/operations/github_actions.md`, `docs/operations/website_delivery.md` | Workflow count and core CI gates mostly match docs. |
| Active band catalog | live `bands` table | `src/jambandnerd/config/bands.py` fallback helpers, website band reads | Runtime truth is dynamic. Static config is fallback only. |
| Product version | No single source exists today | `pyproject.toml`, `apps/web/package.json`, `src/jambandnerd/__init__.py`, `apps/web/src/lib/site.ts`, docs | This missing source-of-truth is the root cause of version drift. |

## Active Documentation Classification

| Path | Classification | Current State |
|---|---|---|
| `README.md` | Canonical | Mostly aligned, but docs-site guidance is broken and Streamlit wording is too generous relative to current code. |
| `docs/index.md` | Active secondary | Navigation currently elevates stale model/reference pages alongside current docs. |
| `docs/user/getting_started.md` | Active secondary | Acceptable as orientation, but it inherits the broken docs-site path through `README.md`. |
| `docs/user/pipeline_usage.md` | Canonical | Aligned with current pipeline and website-first direction. |
| `docs/user/configuration.md` | Active secondary | Stale on model state; still presents CK+ as a current configurable model path. |
| `docs/contributor/onboarding.md` | Active secondary | Mostly aligned, but still speaks too softly about which docs are canonical vs secondary. |
| `docs/contributor/developer_guide/ai_sessions.md` | Active secondary | Aligned with the active `.agent/` and `session_logs/` workflow. |
| `docs/contributor/developer_guide/architecture.md` | Canonical | Partially stale: still presents Deal as web-hidden and CK+ as retained baseline. |
| `docs/contributor/developer_guide/extending_the_platform.md` | Active secondary | Stale on band-extension workflow; it still instructs hardcoded web config changes for bands. |
| `docs/contributor/model_development.md` | Active secondary | Still useful, but needs a pass after model-lifecycle cleanup. |
| `docs/contributor/model_readiness.md` | Active secondary | Still useful, but should explicitly reference metadata/registry as the rollout truth. |
| `docs/operations/github_actions.md` | Canonical | Mostly aligned with workflow count, schedules, and quality gates. |
| `docs/operations/website_delivery.md` | Canonical | Strongest website operations doc; version section is now stale. |
| `docs/operations/streamlit_deploy.md` | Legacy-but-keep | Only defensible if an actual legacy surface still exists. Current repo state suggests it should be archived or rewritten as historical context. |
| `docs/operations/pipeline_optimization.md` | Legacy-but-keep | Contains stale CK+ references and reads more like historical migration context than active ops guidance. |
| `docs/operations/frontend_strategy.md` | Legacy-but-keep | Historical planning context, not current website truth. |
| `docs/operations/mobile_verification.md` | Active secondary | Compatible with the current smoke and mobile-first story. |
| `docs/operations/main_branch_elevation.md` | Active secondary | Still relevant to the website delivery model. |
| `docs/operations/data_recovery_rebuild.md` | Active secondary | Relevant to recovery workflows. |
| `docs/operations/tourwrangler_fallback.md` | Active secondary | Relevant for WSP collector operations. |
| `docs/overview/implementation_status.md` | Active secondary | Stale on version, CK+/Deal lifecycle, and current product state. |
| `docs/overview/project/prd.md` | Active secondary | Useful product context, but stale on supported bands and feature sequencing details. |
| `docs/overview/project/adr.md` | Legacy-but-keep | Historical decisions remain useful, but it is not the place to learn current architecture. |
| `docs/overview/project/schedule.md` | Legacy-but-keep | Explicitly historical and should stay demoted. |
| `docs/reference/specifications/data_strategy.md` | Canonical | Best current contract doc. |
| `docs/reference/specifications/cli.md` | Active secondary | Mostly aligned. |
| `docs/reference/specifications/technical_overview.md` | Legacy-but-keep | Heavily stale and mixes outdated architecture, old schedules, and pseudocode. |
| `docs/reference/models/deal.md` | Active secondary | Mostly aligned with current code, but the promotion date does not match metadata notes. |
| `docs/reference/models/index.md` | Legacy-but-keep | Stale because it still describes Deal as hidden and CK+ as active. |
| `docs/reference/models/ckplus.md` | Legacy-but-keep | Historical model reference now that CK+ is retired. |
| `docs/reports/index.md` | Active secondary | Good place for reports; keep it as the report registry and add future audits here. |
| `docs/troubleshooting/*` | Legacy-but-keep | Valuable incident history, but should not be surfaced like active architecture or product docs. |
| `docs/logs/**` | Archive-only | Historical archive only. |
| `docs/archive/**` | Archive-only | Historical archive only. |

## Findings

## Critical

### 1. Product version is split across code, website, and docs

**Evidence**

- `pyproject.toml`: `0.2.1`
- `apps/web/package.json`: `0.2.1`
- `src/jambandnerd/__init__.py`: `0.1.0`
- `apps/web/src/lib/site.ts`: `0.1.0`
- `docs/overview/implementation_status.md`: `0.1.0`
- `docs/operations/website_delivery.md`: `0.1.0`

**Impact**

- Release communication is unreliable.
- Contributors cannot tell which version is current.
- The website can display a version that does not match the package and docs.

**Source-of-truth recommendation**

- Define one canonical product version owner.
- Sync Python package version, web package version, displayed site version, and docs to it.
- Add a CI check that fails on version drift.

### 2. Model lifecycle state is inconsistent across code, docs, and website messaging

**Evidence**

- `src/jambandnerd/models/metadata.py`: CK+ retired, Deal enabled for pipeline and web, Deal note says promoted `2026-04-11`.
- `apps/web/src/lib/config.ts`: Notebook and Deal promoted, CK+ hidden.
- `docs/contributor/developer_guide/architecture.md`: Deal still web-hidden, CK+ retained as baseline.
- `docs/overview/implementation_status.md`: CK+ still production, Deal still experimental/gated.
- `docs/reference/models/index.md`: Deal still hidden until approved.
- `docs/reference/models/deal.md`: says Deal promoted on `2026-04-10`.

**Impact**

- Product and ops docs disagree with the running website.
- Contributors can make the wrong rollout assumption.
- Model-readiness work cannot reliably reference a single lifecycle state.

**Source-of-truth recommendation**

- Treat `ModelMetadata` and `registry.py` as the only backend truth.
- Treat web config as display metadata only.
- Rewrite model docs and architecture/status docs from registry state.

### 3. Streamlit is documented as a retained legacy surface, but the code surface is absent

**Evidence**

- `src/jambandnerd/web` does not exist.
- `src/jambandnerd/__init__.py` still advertises `web` capabilities and exports `web` in `__all__`.
- `README.md`, `docs/overview/project/prd.md`, `docs/reference/specifications/technical_overview.md`, and `docs/operations/streamlit_deploy.md` still describe a retained internal Streamlit surface.

**Impact**

- Contributors are told there is an internal UI path that does not actually exist in the current repo.
- Package metadata is misleading.
- Legacy docs remain harder to archive because the project has not clearly declared the surface dead.

**Source-of-truth recommendation**

Make an explicit binary decision. Either restore and test a real legacy surface, or archive/remove active Streamlit references and clean up Python package metadata accordingly.

### 4. The documented docs-build workflow is broken

**Evidence**

- `README.md` instructs users to run `mkdocs serve`.
- `pyproject.toml` still includes a `docs` extra with `mkdocs`.
- No `mkdocs.yml` or `mkdocs.yaml` exists in the repo root.
- Historical session logs reference `mkdocs.yaml`, confirming this was once present and is now missing.

**Impact**

- The documentation system cannot be rebuilt from the documented workflow.
- This is a broken operator path in a canonical entrypoint.
- Any future docs cleanup lacks a reliable validation command.

**Source-of-truth recommendation**

- Either restore the MkDocs config and make the docs build pass again.
- Or remove `mkdocs` guidance from canonical docs until the build path is restored.

## Medium

### 5. The live operations surface shows WSP Notebook freshness drift

**Evidence**

- `validate_prediction_tables.py` reported WSP Notebook predictions as stale in the sampled run.
- `validate_accuracy_tables.py` reported WSP Notebook per-show and aggregate accuracy as stale in the sampled run.
- WSP Deal predictions and accuracy were fresh in the same sample.

**Impact**

- Live model parity is inconsistent by band/model.
- Website or downstream consumers may see mixed freshness expectations depending on model.
- Ops documentation currently explains degraded-mode collection handling, but not this model-specific freshness divergence.

**Source-of-truth recommendation**

- Investigate whether WSP Notebook is intentionally deprecated in practice, operationally skipped, or failing silently.
- Reflect the actual policy in workflows, validation messaging, and docs.

### 6. Navigation still elevates stale reference pages as if they were active truth

**Evidence**

- `docs/index.md` links `technical_overview.md`, `reference/models/index.md`, and `reference/models/ckplus.md` as normal active references.
- Those pages are materially behind current registry and website behavior.

**Impact**

- New contributors can land on outdated guidance before they reach the canonical docs.
- The repo already has a good truth hierarchy, but navigation does not enforce it.

**Source-of-truth recommendation**

- Make `docs/index.md` reflect the canonical vs historical split.
- Demote stale pages to legacy sections or archive-only navigation.

### 7. Extension and contributor docs still encode outdated implementation patterns

**Evidence**

- `docs/contributor/developer_guide/extending_the_platform.md` says new bands should be added to `apps/web/src/lib/config.ts`.
- Current website band discovery is dynamic through the live `bands` table and `fetch_active_bands()`.
- `tests/TESTING.md` is materially behind the current test organization and verification surface.

**Impact**

- Contributors could follow the wrong extension path.
- New work could reintroduce hardcoded band logic or underuse the current test surface.

**Source-of-truth recommendation**

- Rewrite extension docs around the live band registry, collector entrypoints, and consolidated scripts.
- Refresh testing docs to reflect current suites and website smoke workflows.

### 8. Some support tooling is stale enough to be misleading

**Evidence**

- `scripts/admin/get_schemas.py` fails from the repo root because it imports `src.jambandnerd...` after adding the wrong path.
- `src/jambandnerd/__init__.py` still documents a nonexistent web module and an outdated model list.

**Impact**

- Low-trust tooling raises the maintenance cost of reviews and incident response.
- Metadata drift makes the package surface look less reliable than the underlying code really is.

**Source-of-truth recommendation**

- Fix or retire stale admin helpers.
- Keep package metadata aligned with the actual module tree.

## Low

### 9. Templates and durable reporting surfaces are thinner than the repo now needs

**Evidence**

- `session_logs/TEMPLATE.md` is intentionally minimal, but it does not encourage evidence capture, source-of-truth references, or clear follow-on ownership.
- ADRs and reports are useful, but there is no explicit audit template for repo-wide reviews like this one.

**Impact**

- Reviews and cleanups are more likely to be one-off threads than reusable artifacts.
- Documentation quality depends too much on whoever writes the note.

**Source-of-truth recommendation**

- Add one stronger audit/report template and slightly enrich the session-log template with evidence and validation expectations.

## Prioritized Roadmap

## Near Term

### 1. Canonicalize truth surfaces

- Choose one product version and sync these surfaces:
- `pyproject.toml`
- `apps/web/package.json`
- `src/jambandnerd/__init__.py`
- `apps/web/src/lib/site.ts`
- version references in active docs
- Rewrite active model-state docs from `ModelMetadata`, starting with:
- `docs/contributor/developer_guide/architecture.md`
- `docs/overview/implementation_status.md`
- `docs/reference/models/index.md`
- `docs/reference/models/deal.md`
- `docs/user/configuration.md`
- Make a hard decision on Streamlit and clean active references accordingly.
- Restore a working docs-build config or remove canonical `mkdocs` guidance until it exists.

### 2. Fix broken or misleading operator paths

- Fix `scripts/admin/get_schemas.py` or archive it.
- Refresh `tests/TESTING.md`.
- Tighten `docs/index.md` so it stops elevating stale references.

### 3. Address live WSP Notebook drift

- Confirm whether Notebook for WSP is intentionally stale, implicitly deprecated, or operationally broken.
- Align validation, workflow behavior, and docs to the answer.

## Medium Term

### 4. Introduce stronger documentation ownership and template rules

- Define a compact docs ownership map with four states:
- canonical docs
- active secondary docs
- legacy-but-keep docs
- archive-only docs
- Add a reusable audit/report template.
- Expand `session_logs/TEMPLATE.md` to require:
- evidence summary
- validation results
- explicit next step or owner

### 5. Add CI checks for drift-prone interfaces

- Version-sync check across Python, web, and displayed site version.
- Docs smoke check for whichever docs-build path becomes canonical.
- Optional stale-reference grep for retired surfaces like Streamlit and CK+ in active-doc paths.

## Longer Term

### 6. Reduce compatibility shims and duplicated truth

- Move more website model presentation from hand-maintained config toward shared registry-backed metadata.
- Continue reducing fallback/static config responsibilities where the live registry already owns truth.
- Formalize a recurring live-data health review across band/model freshness, not just table presence.

## Suggested First Implementation Pass

This is the highest-leverage follow-on change set after the audit:

- Sync version contract across package, site, and docs.
- Update active model-state docs to match registry metadata.
- Archive or delete active Streamlit references unless the legacy surface is restored.
- Restore a real docs-build config and wire it into validation.
- Fix `scripts/admin/get_schemas.py`.
- Refresh `docs/index.md`, `extending_the_platform.md`, and `tests/TESTING.md`.

## Acceptance Criteria For Follow-On Cleanup

- One product version appears everywhere active.
- Active docs describe Deal and CK+ the same way as model metadata and the live website.
- No active doc claims there is a maintained Streamlit surface unless one actually exists in the repo.
- The documented docs-build command works from a clean checkout.
- WSP Notebook freshness is either green or explicitly documented as deprecated/degraded.
- `docs/index.md` routes contributors toward current truth before historical context.
