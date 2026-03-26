import json

from src.jambandnerd.config.bands import get_active_bands


def get_bands():
    """
    Returns the list of active bands.
    """
    return sorted(get_active_bands())


if __name__ == "__main__":
    bands = get_bands()
    print(json.dumps(bands))
