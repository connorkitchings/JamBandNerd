# Delegation Workflow

Use this when the task benefits from parallel specialist work, fresh-context review, or a handoff between agent roles. Keep delegation scoped; do not split a single atomic change across multiple owners.

## When To Delegate

- Non-trivial implementation touching separable files or concerns.
- Research with independent angles such as source behavior, API docs, operational risk, or product precedent.
- Review after meaningful code changes, especially shared pipeline, model, storage, or website behavior.
- Test design for changed public behavior or regression fixes.

Do not delegate typo fixes, single-line mechanical edits, or tasks where each step depends on the previous output.

## Brief Format

Every delegated packet must be self-contained:

```text
[Owner] -> [Specialist]: atomic objective.
Files allowed: path/to/file.py, path/to/test.py
Do not touch: path/owned/by/other/work.py
Context: relevant constraints, interfaces, and repo rules.
Questions:
- What must be true for this to be correct?
- What existing pattern should this follow?
- What verification should run?
Output: concise findings, changed files, commands run, open questions.
```

## File Ownership

- Assign explicit file ownership before parallel implementation.
- Avoid overlapping edits unless one owner is review-only.
- If an interface is not stable enough to parallelize, sequence the work and hand off with the packet format in `.agent/AGENTS.md`.

## Synthesis

- Organize results by risk or theme, not by who produced them.
- Surface disagreements explicitly.
- Verify merged work locally before presenting it as complete.
