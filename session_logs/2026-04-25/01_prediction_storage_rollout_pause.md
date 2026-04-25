# Prediction Storage Rollout Pause

## Goal

- Pause after manually creating the new Supabase prediction-storage tables and
  document the safe next steps for the parallel-table rollout.

## Constraints

- Do not break the current production site.
- Treat the Supabase work as additive table creation, not destructive migration.
- Keep legacy `predictions`, `prediction_songs`, `historical_prediction_runs`,
  and `accuracy_per_show` available until the new tables are populated,
  validated, and the website cutover is complete.
- Enable RLS on each new table, with public read-only access and service-role
  writes.

## Commands Run

```bash
sed -n '1,240p' .agent/skills/end-session/SKILL.md
sed -n '1,220p' docs/operations/data_recovery_rebuild.md
ls session_logs
find session_logs -maxdepth 2 -type f | tail -20
sed -n '1,180p' session_logs/TEMPLATE.md
sed -n '1,220p' .agent/PLAYBOOK.md
find session_logs/2026-04-24 -maxdepth 1 -type f -print | sort
mkdir -p session_logs/2026-04-25
git diff --check
npm run verify:docs
```

## Files And Artifacts

- Updated `docs/operations/data_recovery_rebuild.md` with the parallel-table
  rollout order and RLS/public-read/service-role-write policy.
- Updated `.agent/PLAYBOOK.md` with a durable lesson for additive Supabase
  storage rewrites.
- Created this session log.

## Validation

- `git diff --check` passed.
- `npm run verify:docs` passed.
- Prior implementation verification in this session had also passed:
  - `npm run verify:python`
  - `npm run verify:web`

## Current Supabase State

- User reported manually completing creation of all four new tables:
  - `next_show_prediction_runs`
  - `next_show_prediction_songs`
  - `completed_show_prediction_runs`
  - `completed_show_accuracy`
- The intended state is that all four new tables exist and are empty, with RLS
  enabled, `anon`/`authenticated` read policies, and `service_role` write
  policies.

## Next Step

- Verify the four new tables exist and are empty, then populate and validate
  Goose only before any website cutover.
