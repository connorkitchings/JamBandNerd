"""
Goose utility functions for directory management and time formatting.
"""

from datetime import datetime
from pathlib import Path


def get_band_data_dir(band_name: str, subfolder: str = "collected") -> Path:
    """
    Returns the path to the band's data directory for a given subfolder.
    For Goose, returns <PROJECT_ROOT>/data/goose.
    """
    root = Path(__file__).resolve().parent.parent.parent.parent
    if band_name.lower() == "goose":
        return root / "data" / "goose"
    return root / "data" / band_name / subfolder


def get_date_and_time() -> str:
    """
    Returns the current date and time as a formatted string.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_relative_path(path: Path):
    """
    Prints the given path relative to the current working directory.
    """
    print(str(path.relative_to(Path.cwd())))
