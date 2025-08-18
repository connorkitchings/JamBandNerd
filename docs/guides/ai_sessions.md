# AI Session Guides

This document provides standardized prompts for starting and ending an AI-assisted development session.

## Session Start Template

Copy, paste, and fill in the bracketed sections to begin a session. This prompt asks the AI to read
context and confirm readiness.

```markdown
Hello. We are continuing our work on the 'JamBandNerd' project.

To get up to speed, please perform the following steps:

1. Review the Project Foundation:
   - `documents/planning/project_context.md`
   - `documents/planning/PRD.md`
   - `documents/guides/implementation_guide.md`
   - `pyproject.toml`

2. Review the Current Sprint Status:
   - `documents/planning/implementation_schedule.md`

3. Review the Last Session's Handoff:
   - `docs/logs/[YYYY-MM-DD]/[XX].md` (use the most recent log for today)

4. Prepare for Today's Task:
   - **Our focus today is:** [Describe the main goal for the session, referencing
   `implementation_schedule.md`]

Once you have completed this review, please confirm you are ready, and we will begin.
```

## Session End Template

Use this prompt to generate the dev log and update relevant documentation at the end of a session.

```markdown
We are now ending our development session for today. Please generate the dev log using the standard
template structure.

- **Task Completed**: [Short description of the task or goal for the session.]
- **Key Outcomes**:
  - [Outcome 1]
  - [Outcome 2]
- **Blockers Encountered**: [Describe any blockers, or "None".]
- **Session Handoff & Next Steps**: [Describe the immediate next task and any other notes for the
next session.]
- **Updated Documents**:
  - [List any documents that were created or modified.]

After generating the log, please confirm the file path and a list of the documents you updated.
 
 Additionally, as part of closing the session, review and update any affected documentation in `README.md` and the `docs/` folder to reflect changes made during the session.
```
