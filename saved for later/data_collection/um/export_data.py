"""
Module for exporting data collected from Umphrey's McGee.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from .utils import get_date_and_time, get_logger

# --- Constants ---
BAND_NAME = "UM"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_COLLECTED_DIR = PROJECT_ROOT / "data" / BAND_NAME / "collected"
LOG_FILE_PATH = PROJECT_ROOT / "logs" / BAND_NAME / "um_pipeline.log"
SONG_DATA_FILENAME = "songdata.csv"
VENUE_DATA_FILENAME = "venuedata.csv"
SETLIST_DATA_FILENAME = "setlistdata.csv"
SHOW_DATA_FILENAME = "showdata.csv"
LAST_UPDATED_FILENAME = "last_updated.json"
NEXT_SHOW_FILENAME = "next_show.json"

logger = get_logger(__name__, log_file=LOG_FILE_PATH, add_console_handler=False)


def save_um_data(
    song_data: pd.DataFrame,
    venue_data: pd.DataFrame,
    setlist_data: pd.DataFrame,
    data_dir: Path | None = None,
) -> None:
    """
    Save the provided DataFrames as CSV files in the output directory.

    Args:
        song_data (pd.DataFrame): The song data to save.
        venue_data (pd.DataFrame): The venue data to save.
        setlist_data (pd.DataFrame): The setlist data to save.
        data_dir (Path | None): Directory where the output CSVs will be saved.
        Defaults to DATA_COLLECTED_DIR.
    """
    data_dir = Path(data_dir) if data_dir is not None else Path(DATA_COLLECTED_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    if "Last Played" in venue_data.columns:
        venue_data["Last Played"] = pd.to_datetime(
            venue_data["Last Played"], errors="coerce"
        ).dt.date
        venue_data_sorted = venue_data.sort_values("Last Played")
        next_show = venue_data_sorted[venue_data_sorted["Last Played"] >= today].head(1)
    else:
        next_show = None
    next_show_path = data_dir / NEXT_SHOW_FILENAME
    if next_show is not None and not next_show.empty:
        next_show_record = next_show.iloc[0].to_dict()
        for k, v in next_show_record.items():
            if hasattr(v, "isoformat"):
                next_show_record[k] = v.isoformat()
        with open(next_show_path, "w", encoding="utf-8") as f:
            json.dump({"next_show": next_show_record}, f, indent=2)
    else:
        if next_show_path.exists():
            next_show_path.unlink()
    song_data.to_csv(data_dir / SONG_DATA_FILENAME, index=False)
    venue_data.to_csv(data_dir / VENUE_DATA_FILENAME, index=False)
    setlist_data.to_csv(data_dir / SETLIST_DATA_FILENAME, index=False)


def save_query_data(data_dir: Path | None = None) -> None:
    """
    Save the last updated time as a JSON file in the output directory.

    Args:
        data_dir (Path | None): Directory where the output JSON will be saved.
        Defaults to DATA_COLLECTED_DIR.
    """
    data_dir = Path(data_dir) if data_dir is not None else Path(DATA_COLLECTED_DIR)
    update_time = get_date_and_time()
    last_updated_path = data_dir / LAST_UPDATED_FILENAME
    with open(last_updated_path, "w", encoding="utf-8") as f:
        json.dump({"last_updated": update_time}, f)
