"""
UM utility functions for logging, directory management, and time formatting.
"""

import json
import logging
from datetime import datetime
from pathlib import Path


# --- Directory Utilities ---
def get_band_data_dir(band_name: str, subfolder: str = "collected") -> Path:
    """
    Returns the path to the band's data directory for a given subfolder.
    For UM, returns <PROJECT_ROOT>/data/um (ignores subfolder for UM).
    For other bands, returns <PROJECT_ROOT>/data/<band_name>/<subfolder>.
    """
    root = Path(__file__).resolve().parent.parent.parent.parent
    if band_name.lower() == "um":
        return root / "data" / "um"
    return root / "data" / band_name.lower() / subfolder


# --- Logging Utilities ---
def get_logger(name: str, log_file: Path = None, add_console_handler: bool = True):
    """
    Returns a logger with the given name. If log_file is provided, logs to that file.
    Adds a console handler by default. Prevents duplicate handlers.
    Log format: [mm--dd--yyyy hh:mm:ss] LEVEL: message
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m--%d--%Y %H:%M:%S"
    )
    # Only add handlers if none exist (prevents double logging)
    if not logger.handlers:
        if log_file is not None:
            log_file = Path(log_file)
            # Ensure log files are always placed in the top-level @logs directory, not @src/logs
            try:
                src_idx = log_file.parts.index("src")
                # Rebuild the path without 'src' and anything before it
                log_file = Path(
                    *log_file.parts[:src_idx], *log_file.parts[src_idx + 1 :]
                )
            except ValueError:
                pass  # 'src' not in path, leave as is
            log_file.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        if add_console_handler:
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)
    logger.propagate = False
    return logger


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
