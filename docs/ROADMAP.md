# JamBandNerd: Project Roadmap & Next Steps

**Last Updated:** 2026-05-23

## 1. Introduction

JamBandNerd v1.0.1 shipped to production on 2026-05-23 at
[jambandnerd.com](https://jambandnerd.com). The platform has a stable pipeline
foundation, per-band prediction models (ADR 0001 complete), and a live website
as the sole public product surface. The Streamlit app is retired.

This roadmap documents completed phases and the current post-v1 focus:

1. **Website Operations:** Keep the website routes and shared shell production-ready.
2. **Deployment Hardening:** Maintain the production website deployment workflow and verification path.
3. **Future Expansion:** Model Phase B refinement, potential new bands, and API exploration only after the website creates real external-consumer demand.

## 2. Prioritization Strategy

Phases 1 through 4 are now complete. v1.0.1 is live in production.

---

## Phase 1: Documentation Realignment (Completed)

### 1.1. Canonical Docs Update

- **Goal:** Rewrite active docs so they describe JamBandNerd as a website-first product.
- **Implementation:**
  1. Update the canonical entrypoints: `README.md`, `docs/user/pipeline_usage.md`, and `docs/contributor/developer_guide/architecture.md`.
  2. Update product/planning docs: `docs/overview/project/prd.md`, `docs/ROADMAP.md`, and `docs/overview/implementation_status.md`.
  3. Update contributor and user guidance to reflect the website-first product direction.
- **Priority:** **Highest**.

### 1.2. Navigation and Operations Cleanup

- **Goal:** Ensure navigation points to current website-first guidance.
- **Implementation:**
  1. Add a website delivery strategy doc for the new target architecture.
  2. Retire legacy deployment docs and archive them.
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

## Phase 3: Parity Migration (Completed)

### 3.1. Website Parity

- **Goal:** Replace the Streamlit experience with the website.
- **Completed website views:**
  - Current predictions
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
- **Priority:** **High**.

---

## Phase 4: Cutover and Operations (Complete)

### 4.1. Website Operations

- **Goal:** Operate the website and pipeline as a coherent production system.
- **Completed:**
  1. Website wired to Vercel's native GitHub integration with `apps/web` as root directory.
  2. GitHub Actions CI gates (`Repo Quality`, `Website Quality`, `Hosted Website Smoke`) active.
  3. Daily pipeline running at 3 PM ET with per-band health reporting.
  4. v1.0.1 shipped to production at `jambandnerd.com` on 2026-05-23.
  5. Branch structure simplified to `main` (production) + `dev` (integration).

---

## Phase 5: Post-v1 Iteration (Active)

### 5.1. Model Phase B Refinement

- **Goal:** Improve per-band model accuracy beyond the v1 baselines.
- **Constraints:**
  - Do not resume broad feature or hyperparameter sweeps for the current LightGBM family.
  - Only open experiment: Phish cleanup ablation (see `docs/contributor/model_development.md`).
  - WSP and Billy on hold pending upstream data gaps.
- **Priority:** **Medium**.

### 5.2. Product Polish

- **Goal:** Address UX and code quality items identified in the v1 punch list.
- **Reference:** `docs/archive/v1_punch_list.md` — key open items include loading/error boundaries, accessibility fixes, and component deduplication.
- **Priority:** **Low** (no blocking user-facing issues).

### 5.3. New Band Onboarding

- **Goal:** Expand coverage beyond the current five active bands.
- **Next candidate:** Eggy (collector exists; excluded from single-model rollout due to Cloudflare bypass complexity).
- **Priority:** **Low**.

### 5.4. Public API

- **Goal:** Expose prediction and accuracy data via a public API.
- **Trigger:** Only after the website creates real external-consumer demand.
- **Priority:** **Future / Not started**.
