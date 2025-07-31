# Current Context

_This file should be updated at the end of each session or sprint to summarize the current state,
key decisions, and next steps._

- **Active Sprint:** Supabase Data Migration
- **Current Focus:** Complete the migration of all data pipelines from local files to Supabase.
- **Recent Decisions:** Migrated the Phish pipeline to Supabase as a pilot. This new architecture
  will be the template for all other bands.
- **Known Issues:** The high-level orchestration script (`scripts/run_all_predict_todays.py`) uses
  `subprocess` and fails for non-migrated pipelines. It needs to be refactored to use a more robust
  method like `importlib`.
- **Next Steps:** Migrate the Goose, UM, and WSP data and prediction pipelines to Supabase.
