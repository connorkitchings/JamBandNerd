# JamBandNerd: Project Roadmap & Next Steps

**Last Updated:** 2026-03-19

## 1. Introduction

JamBandNerd now has a stable pipeline foundation, mature prediction models, and a legacy Streamlit
interface that proved out the product shape. A working website now exists in `apps/web`, and the
current goal is to make it the unambiguous primary product surface before final Streamlit removal.

This roadmap shifts priorities accordingly:

1. **Website Parity:** Keep improving the current website routes and shared shell.
2. **Soft Cutover Prep:** Make the website the default path in docs, onboarding, and workflow messaging.
3. **Deployment Hardening:** Add the production website deployment workflow and verification path.
4. **Final Legacy Removal:** Retire Streamlit from the repo once deployment and confidence are in place.

## 2. Prioritization Strategy

Phases 1 through 3 are now substantially complete in the repo. The highest priority is **Phase 4:
Cutover and Operations**, starting with a soft cutover that makes the website the default surface
everywhere users and contributors look first.

---

## Phase 1: Documentation Realignment (Completed)

### 1.1. Canonical Docs Update

- **Goal:** Rewrite active docs so they describe JamBandNerd as a website-first product.
- **Implementation:**
  1. Update the canonical entrypoints: `README.md`, `docs/user/pipeline_usage.md`, and `docs/contributor/developer_guide/architecture.md`.
  2. Update product/planning docs: `docs/overview/project/prd.md`, `docs/ROADMAP.md`, and `docs/overview/implementation_status.md`.
  3. Update contributor and user guidance to describe Streamlit as a legacy transition surface rather than the destination architecture.
- **Priority:** **Highest**.

### 1.2. Navigation and Operations Cleanup

- **Goal:** Ensure navigation points to current website-first guidance.
- **Implementation:**
  1. Add a website delivery strategy doc for the new target architecture.
  2. Reclassify Streamlit deployment docs as legacy/internal transition guidance.
  3. Run stale-reference searches across active docs and update broken navigation.
- **Priority:** **Highest**.

---

## Phase 2: Website Foundation (Completed)

### 2.1. Monorepo Frontend Setup

- **Goal:** Add a production website app to this repository.
- **Implementation:**
  1. Scaffold a monorepo website application using Next.js.
  2. Standardize environment-variable handling for Supabase access.
  3. Set up local development, build, and preview deploy workflows.
- **Priority:** **High**.

### 2.2. Deployment Baseline

- **Goal:** Establish a production-ready website deployment path.
- **Implementation:**
  1. Target Vercel for hosting and preview deployments.
  2. Define the required runtime secrets and deployment environments.
  3. Add CI checks appropriate for the website app.
- **Priority:** **High**.

---

## Phase 3: Parity Migration (Largely Complete)

### 3.1. Rebuild the Current Product Surface

- **Goal:** Reach full parity with the current Streamlit experience before cutover.
- **Required website views:**
  - Current predictions
  - Model comparison
  - Historical explorer
  - Accuracy/performance views
  - Last-show details
  - About/explanatory content
- **Implementation Notes:**
  - Use server-side reads from Supabase in v1.
  - Do not require a separate public API for initial launch.
  - Reuse existing prediction and accuracy tables rather than redesigning storage first.
- **Priority:** **High**.

### 3.2. Preserve Data/Model Stability

- **Goal:** Avoid unnecessary backend churn during the frontend migration.
- **Implementation:**
  1. Keep `scripts/run_optimized_pipeline.py` as the canonical end-to-end entrypoint.
  2. Keep prediction schemas and backtest workflows stable unless the website build proves a real mismatch.
  3. Only touch legacy Streamlit code when needed to validate behavior during migration.
- **Priority:** **High**.

---

## Phase 4: Cutover and Operations (Current Priority)

### 4.1. Website Cutover

- **Goal:** Make the website the primary public surface and demote Streamlit to legacy status.
- **Implementation:**
  1. Validate parity against the existing Streamlit feature set.
  2. Update docs and contributor guidance to point new feature work at the website app only.
3. Remove Streamlit deployment from the primary operations path.
- **Priority:** **Medium**.

### 4.2. Ongoing Operations

- **Goal:** Operate the website and pipeline as a coherent production system.
- **Implementation:**
  1. Wire the website to Vercel’s native GitHub integration with `apps/web` as the root directory.
  2. Keep website verification checks in GitHub Actions (`lint`, `build`, smoke-suite listing).
  3. Keep pipeline failure alerting and data freshness monitoring in place.
  4. Revisit public API work only after the website launch creates real external-consumer demand.
- **Priority:** **Medium**.
