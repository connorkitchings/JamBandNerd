# JamBandNerd: Project Roadmap & Next Steps

**Last Updated:** 2025-11-30

## 1. Introduction

The JamBandNerd project has successfully evolved from its initial concept into a mature, feature-rich data science platform. With automated data pipelines, two distinct prediction models, and a comprehensive web interface supporting six bands, the core implementation is largely complete.

This document outlines the recommended next steps to guide the project from its current state to a stabilized "v1.0" release and beyond. The plan is organized into four distinct phases:

1.  **Stabilization and v1.0 Release:** Closing out remaining tasks and fixing known issues.
2.  **User Experience & Analytics Enhancements:** Improving the value of the existing web application.
3.  **Strategic Feature Expansion:** Beginning work on next-generation capabilities.
4.  **Ongoing Operations & Maintenance:** Ensuring the long-term health and reliability of the platform.

## 2. Prioritization Strategy

The highest priority is to **complete Phase 1: Stabilization**. This ensures the platform is robust, fully functional as designed, and has a reliable test suite to support future development.

Following stabilization, **Phase 2: User Experience & Analytics** should be prioritized. These enhancements deliver the most significant and immediate value to end-users by making the existing data and models more insightful and interactive.

Phases 3 and 4 represent mid-to-long-term goals that build upon the stable foundation established in the earlier phases.

---

## Phase 1: Stabilization and v1.0 Release (Highest Priority)

### 1.1. Finalize WSP Data Pipeline

-   **Goal:** Complete the Widespread Panic fallback data mechanism by applying the final database schema change.
-   **Pros:**
    -   Completes a core, documented feature.
    -   Improves data integrity and reliability for WSP setlists.
    -   Removes a known "to-do" item from the project backlog.
-   **Cons:**
    -   Requires manual intervention by a user with database access to run the `ALTER TABLE` command.
-   **Implementation:**
    1.  A user with Supabase credentials must execute the following SQL command in the Supabase SQL Editor:
        ```sql
        ALTER TABLE public.wsp_setlists_raw ADD COLUMN IF NOT EXISTS source text;
        ```
    2.  The `scripts/run_wsp_collection.py` script will be executed to backfill the new `source` column for existing data from EverydayCompanion.
    3.  The pipeline will be run again to verify that the promotion logic (where EverydayCompanion data replaces TourWrangler data) works as expected.
-   **Priority:** **High**. This is the last remaining piece of the initial implementation.

### 1.2. Stabilize Test Suite

-   **Goal:** Resolve any environment issues and fix failing tests to ensure a stable, passing test suite.
-   **Pros:**
    -   Guarantees code quality and prevents future regressions.
    -   Increases developer confidence when adding new features or refactoring.
    -   Essential for a mature, maintainable project.
-   **Cons:**
    -   Can be time-consuming if the root cause of test failures is complex.
    -   Does not add a direct user-facing feature.
-   **Implementation:**
    1.  Ensure `pytest` is installed in the `uv` virtual environment.
    2.  Execute the test suite via `uv run pytest`.
    3.  Diagnose and fix each of the failing tests. This may involve correcting test logic, updating mocks, or fixing underlying bugs in the source code.
-   **Priority:** **High**. A reliable test suite is critical before adding new features.

### 1.3. Address Performance Bottlenecks

-   **Goal:** Optimize the Billy Strings data collection pipeline to make it practical for regular execution.
-   **Pros:**
    -   Makes the Billy Strings data pipeline fully operational and reliable.
    -   Improves the overall robustness of the daily automated workflow.
-   **Cons:**
    -   Optimization may involve trial-and-error with scraping logic and is dependent on an external, third-party website.
-   **Implementation:**
    1.  Analyze `src/jambandnerd/data_collection/billy/collector.py` to identify slow operations.
    2.  Increase the default request `timeout` in `src/jambandnerd/data_collection/config.py` for the `'billy'` collector.
    3.  Potentially implement a simple file-based cache for show pages during backfills to prevent re-scraping on transient errors.
-   **Priority:** **Medium**. Important for full-band support but can be addressed after the core platform is stabilized.

### 1.4. Documentation Cleanup

-   **Goal:** Update all project documentation to accurately reflect the "v1.0 complete" status.
-   **Pros:**
    -   Improves clarity and reduces confusion for new contributors.
    -   Formally closes out the initial development phase.
-   **Cons:**
    -   No direct functional impact on the application.
-   **Implementation:**
    1.  Review `docs/overview/implementation_status.md` and related documents.
    2.  Use the `replace` tool to update status from "99% Complete" to "v1.0 Complete", remove contradictory statements, and archive the "Partially Implemented" sections that are now complete.
-   **Priority:** **Low**. This should be done as the final step of Phase 1.

---

## Phase 2: User Experience & Analytics Enhancements (Next Priority)

### 2.1. Add Prediction Insights

-   **Goal:** Make the prediction models more transparent by showing *why* a song was predicted.
-   **Pros:**
    -   Dramatically increases the value and "stickiness" of the web UI for users.
    -   Helps users understand the difference between the two prediction models.
-   **Cons:**
    -   Requires careful UI design to avoid clutter.
-   **Implementation:**
    1.  Modify the `display_predictions` function in `src/jambandnerd/web/components/tabs/predictions.py`.
    2.  For each row in the predictions table, add a new column with a tooltip or an info icon (`ℹ️`).
    3.  When a user hovers over the icon, display the key features that led to the prediction (e.g., "Plays in Last Year: 12", "Current Gap: 15", "Gap Ratio: 2.1").
-   **Priority:** **High (within Phase 2).** This is the most impactful UX improvement.

### 2.2. Implement Historical Prediction Explorer

-   **Goal:** Allow users to look up a past show and see what the predictions would have been on that date.
-   **Pros:**
    -   Creates a major new, engaging feature for the application.
    -   Provides a powerful tool for manually auditing model performance.
-   **Cons:**
    -   Requires new UI components and data-fetching logic, increasing complexity.
-   **Implementation:**
    1.  Create a new "Explorer" tab in `src/jambandnerd/web/app.py`.
    2.  Add a band selector and a date input to the tab.
    3.  When a user selects a date, fetch both the actual setlist for that date and the predictions that were (or would have been) generated for it using `fetch_predictions_for_date`.
    4.  Display the predictions and the actual setlist side-by-side, highlighting the "hits".
-   **Priority:** **Medium (within Phase 2).**

---

## Phase 3: Strategic Feature Expansion (Mid-Term)

### 3.1. Develop a Public API

-   **Goal:** Expose prediction data through a public, read-only REST API.
-   **Pros:**
    -   Unlocks significant potential for community integrations (e.g., mobile widgets, third-party sites).
    -   Positions JamBandNerd as a data platform, not just a website.
-   **Cons:**
    -   Adds a new service to deploy, monitor, and secure.
    -   Requires careful API design and documentation.
-   **Implementation:**
    1.  Scaffold a new API application using a modern Python framework like **FastAPI**.
    2.  Create a file, e.g., `api/main.py`, that reuses `src/jambandnerd/db/connection.py` to connect to Supabase.
    3.  Define a `GET /predictions/{band}/{model}` endpoint that fetches the latest predictions and returns them as a JSON response.
-   **Priority:** **Mid-Term Goal.** This is a significant new capability that can be started after Phase 2 enhancements are delivered.

---

## Phase 4: Ongoing Operations & Maintenance (Continuous)

### 4.1. Implement Monitoring & Alerting

-   **Goal:** Proactively detect pipeline failures and data quality issues.
-   **Pros:**
    -   Improves system reliability and maintains user trust.
    -   Reduces the time to detect and resolve production issues.
-   **Cons:**
    -   Requires configuration of external services or webhooks.
-   **Implementation:**
    1.  Modify the `.github/workflows/daily-pipeline.yml` workflow.
    2.  Add a new final step that runs only on failure (`if: failure()`).
    3.  This step will use a pre-existing GitHub Action (or a simple `curl` command) to send a formatted message to a webhook URL stored in GitHub Secrets.
-   **Priority:** **High (Post-Stabilization).** This is a key operational improvement that should be implemented once v1.0 is stable.
