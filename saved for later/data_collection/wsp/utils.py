"""
WSP utility functions for logging, directory management, and time formatting.
"""

import json
import logging
from datetime import datetime
from pathlib import Path


# --- Directory Utilities ---
def get_band_data_dir(band_name: str, subfolder: str = "collected") -> Path:
    """
    Returns the path to the band's data directory for a given subfolder.
    For WSP, returns <PROJECT_ROOT>/data/wsp (ignores subfolder for WSP).
    For other bands, returns <PROJECT_ROOT>/data/<band_name>/<subfolder>.
    """
    root = Path(__file__).resolve().parent.parent.parent.parent
    if band_name.lower() == "wsp":
        return root / "data" / "wsp"
    return root / "data" / band_name.lower() / subfolder


# --- Time Utilities ---
def get_date_and_time() -> str:
    """
    Returns the current date and time as a formatted string.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- Last Update Utility ---
def get_last_update_time(
    data_dir: Path = None, last_updated_filename: str = "last_updated.json"
) -> str | None:
    """
    Returns the last update time from last_updated.json in the given directory,
    or None if not found.
    Args:
        data_dir (Path): Directory containing last_updated.json.
        last_updated_filename (str): Filename for last update JSON.
    Returns:
        str | None: Last update time as string, or None if not found.
    """
    if data_dir is None:
        # Default to UM's collected data dir
        data_dir = get_band_data_dir("UM", "collected")
    last_updated_path = Path(data_dir) / last_updated_filename
    if last_updated_path.exists():
        with open(last_updated_path, encoding="utf-8") as f:
            meta = json.load(f)
            return meta.get("last_updated")
    return None
