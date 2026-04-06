import json
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(project_root, "src"))

from jambandnerd.config.bands import get_active_bands


def get_bands():
    """
    Returns the list of active bands.
    """
    return sorted(get_active_bands())


if __name__ == "__main__":
    bands = get_bands()
    print(json.dumps(bands))
