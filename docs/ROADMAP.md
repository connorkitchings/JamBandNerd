# JamBandNerd: Project Roadmap & Next Steps

**Last Updated:** 2026-03-19

## 1. Introduction

JamBandNerd now has a stable pipeline foundation, mature prediction models, and a legacy Streamlit
interface that proves out the product shape. The next major goal is to replace Streamlit with a
full website that becomes the primary public product surface.

This roadmap shifts priorities accordingly:

1. **Documentation Realignment:** Make the repo’s active docs website-first and internally consistent.
2. **Website Foundation:** Add the new website app and core deployment workflow.
3. **Parity Migration:** Rebuild the current user-facing prediction experience on the website.
4. **Cutover and Operations:** Retire Streamlit as the primary surface and harden website operations.

## 2. Prioritization Strategy

The highest priority is to complete **Phase 1: Documentation Realignment**. The repo still contains
many active references that describe Streamlit as the target product, and those need to be fixed
before implementation work can proceed cleanly.

After the docs pass, focus on **Phase 2: Website Foundation** and **Phase 3: Parity Migration**.
The existing pipeline, Supabase schema, and model behavior should stay stable unless the website
build exposes a concrete data-access gap.

---

## Phase 1: Documentation Realignment (Current Priority)

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

## Phase 2: Website Foundation

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

## Phase 3: Parity Migration

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

## Phase 4: Cutover and Operations

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
  1. Add website observability and deployment health checks.
  2. Keep pipeline failure alerting and data freshness monitoring in place.
  3. Revisit public API work only after the website launch creates real external-consumer demand.
- **Priority:** **Medium**.
