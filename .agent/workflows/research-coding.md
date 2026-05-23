# Research + Coding Workflow

Use this when external facts, upstream APIs, dependency behavior, current documentation, or product conventions should inform code or operational changes.

## Scope Tiers

- **Simple**: one factual lookup. Answer inline with a source link.
- **Standard**: two or three independent questions. Gather sources, summarize tradeoffs, then implement only the needed change.
- **Deep**: contested, high-risk, or broad decisions. Split research by angle and preserve findings in `docs/` or `session_logs/` before coding.

Prefer the smallest tier that can answer the decision.

## Research Rules

1. State the decision the research is meant to support.
2. Prefer primary sources: official docs, upstream repos, standards, source code, or observed runtime behavior.
3. Capture source links, dates when relevant, and confidence.
4. Flag gaps instead of smoothing over missing or conflicting evidence.
5. Translate findings into repo-specific action: no change, doc update, code change, test, or follow-up.

## Coding Rules After Research

- Inspect existing local patterns before implementing.
- Keep external assumptions at boundaries: config, adapters, collectors, docs, or tests.
- Add tests for behavior changed because of the research, or document why tests do not apply.
- In the session log, include the source links that materially affected the decision.

## Output Shape

```text
Decision:
Sources:
- URL - relevant fact
Findings:
- What matters for JamBandNerd
Action:
- Code/doc/test change or no-change rationale
Gaps:
- What remains uncertain
```
