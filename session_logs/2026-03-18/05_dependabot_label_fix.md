# Dependabot Label Fix

## Goal

- Fix the Dependabot configuration after GitHub rejected non-existent label names.

## Constraints

- Resolve the remote validation error without introducing a larger repo-management change.
- Prefer a config-only fix over creating repo labels out of band.

## Commands Run

```bash
nl -ba .github/dependabot.yml | sed -n '1,200p'
uv run --with pyyaml python - <<'PY'
from pathlib import Path
import yaml
with Path('.github/dependabot.yml').open() as f:
    yaml.safe_load(f)
print('OK .github/dependabot.yml')
PY
```

## Files Changed

- `.github/dependabot.yml`: removed invalid `labels` entries that referenced labels not present in the repository.

## Validation Status

- The updated Dependabot YAML parses successfully.
- The fix removes the specific GitHub validation failure about missing labels.

## Next Step

- Commit and push the Dependabot config fix so GitHub revalidates the file on the remote branch.
