import json
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(project_root, "src"))

from jambandnerd.config.bands import get_daily_pipeline_bands


def get_bands():
    """Return the repo-authoritative daily pipeline band list."""
    return list(get_daily_pipeline_bands())


if __name__ == "__main__":
    bands = get_bands()
    print(json.dumps(bands))
