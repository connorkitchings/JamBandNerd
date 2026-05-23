# Session Search Workflow

Use this when prior AI sessions may contain commands, decisions, failures, or handoffs needed for the current task.

## Search Order

1. Current active logs in `session_logs/`.
2. Recent relevant archive entries in `docs/logs/` only if active logs do not cover the topic.
3. Tool transcript stores only when the user asks to recover conversation history or local logs are insufficient.

## Local Commands

Prefer scoped searches:

```bash
find session_logs -type f | sort | tail -20
rg -n "search phrase|command|decision" session_logs .agent docs/logs
```

Avoid broad recursive searches from the home directory. If transcript search is needed, first identify candidate files or sessions, then inspect only those.

## Return Format

```text
Found:
- session_logs/YYYY-MM-DD/NN.md - relevant decision or command
Not found:
- What was searched without a match
Next:
- The file or question the current session should use
```

Keep retrieved excerpts short. Link to the file path and summarize the decision rather than pasting long logs.
