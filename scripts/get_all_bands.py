import json
import os
import re


def get_bands():
    """
    Scans the 'scripts' directory for 'run_*_collection.py' files
    and returns a list of band names.
    """
    bands = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in os.listdir(script_dir):
        match = re.match(r"run_(.*)_collection\.py", filename)
        if match:
            bands.append(match.group(1))
    return sorted(bands)


if __name__ == "__main__":
    bands = get_bands()
    print(json.dumps(bands))
