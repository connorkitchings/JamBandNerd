# Dev Log: Notebook v2 Experiment

- **Task Completed**: Tested a new "Notebook 2.0" model against the existing "Notebook" model to see if a "last 100 shows" window performs better than a "last 1 year" window.
- **Key Outcomes**:
  - Created a new `notebookv2` model with a 100-show window.
  - Ran backtests for both `notebook` and `notebookv2` models across all 6 bands for the last 100 shows.
  - The original `notebook` model (1-year window) was found to be superior for 4 of the 6 bands, and tied for another.
  - The `notebookv2` model was only superior for WSP.
  - Based on the results, the `notebookv2` model was not promoted, and all related code and files were removed.
  - Documented the experiment and its results in `docs/reports/2025-12-12_notebookv2_experiment.md`.
- **Blockers Encountered**:
  - Initial attempt to create a new database table for `notebookv2` failed due to lack of database credentials.
  - This was overcome by using the existing `predictions_notebook` table and distinguishing the models by `model_version`.
- **Session Handoff & Next Steps**:
  - The experiment is complete and the codebase has been cleaned up.
  - The next logical step would be to explore other model improvements or work on other items from the project roadmap.
- **Updated Documents**:
  - `docs/reports/2025-12-12_notebookv2_experiment.md` (created)
  - `docs/reports/index.md` (created)
