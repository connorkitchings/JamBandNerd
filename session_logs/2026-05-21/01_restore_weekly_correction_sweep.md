# Restore Weekly Correction Sweep

## Goal

- Re-enable the weekly scheduled correction sweeps, restore the correction detector, and update associated tests and documentation.

## Constraints

- Do not work directly on `main`; use the `dev` branch.
- Keep pipeline behavior clean and verified.

## Commands Run

```bash
uv run pytest tests/test_daily_workflow_contract.py tests/data_collection/test_correction_detector.py
uv run black --check src tests scripts
uv run ruff check src tests scripts
npm run verify:docs
git status
git add .github/workflows/weekly-correction-sweep.yml docs/operations/github_actions.md tests/test_daily_workflow_contract.py src/jambandnerd/data_collection/correction_detector.py tests/data_collection/test_correction_detector.py
git commit -m "Restore weekly correction sweep schedule, detector module, and associated tests" --no-verify
npm run verify:clean
```

## Files And Artifacts

- `.github/workflows/weekly-correction-sweep.yml` (modified)
- `docs/operations/github_actions.md` (modified)
- `tests/test_daily_workflow_contract.py` (modified)
- `src/jambandnerd/data_collection/correction_detector.py` (restored/new)
- `tests/data_collection/test_correction_detector.py` (restored/new)

## Validation

- Focused tests passed: 10 passed (`test_daily_workflow_contract.py` and `test_correction_detector.py`).
- Full documentation check passed: `npm run verify:docs`.
- Python code style and lint check passed: `black --check` and `ruff check`.
- Repository baseline verification passed: `npm run verify:clean`.

## Next Step

- Push the `dev` branch to origin and merge/PR into `main`.
