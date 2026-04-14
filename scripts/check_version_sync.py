"""Validate that core product version surfaces stay in sync."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
WEB_PACKAGE_PATH = REPO_ROOT / "apps" / "web" / "package.json"
PYTHON_INIT_PATH = REPO_ROOT / "src" / "jambandnerd" / "__init__.py"
SITE_TS_PATH = REPO_ROOT / "apps" / "web" / "src" / "lib" / "site.ts"


def load_version_surfaces() -> dict[str, str]:
    with PYPROJECT_PATH.open("rb") as handle:
        pyproject = tomllib.load(handle)

    with WEB_PACKAGE_PATH.open() as handle:
        web_package = json.load(handle)

    python_init = PYTHON_INIT_PATH.read_text()
    site_ts = SITE_TS_PATH.read_text()

    python_match = re.search(r'__version__ = "([^"]+)"', python_init)
    site_match = re.search(r'SITE_VERSION = "([^"]+)"', site_ts)

    if python_match is None:
        raise RuntimeError(f"Could not find __version__ in {PYTHON_INIT_PATH}")
    if site_match is None:
        raise RuntimeError(f"Could not find SITE_VERSION in {SITE_TS_PATH}")

    return {
        "pyproject": pyproject["project"]["version"],
        "web_package": web_package["version"],
        "python_package": python_match.group(1),
        "site_version": site_match.group(1),
    }


def main() -> None:
    versions = load_version_surfaces()
    unique_versions = sorted(set(versions.values()))
    if len(unique_versions) != 1:
        details = ", ".join(f"{key}={value}" for key, value in versions.items())
        raise SystemExit(f"Version surfaces are out of sync: {details}")

    version = unique_versions[0]
    print(f"Version surfaces in sync: {version}")


if __name__ == "__main__":
    main()
