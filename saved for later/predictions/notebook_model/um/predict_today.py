import os
from datetime import datetime

from data_loader import load_setlist_and_showdata
from model import aggregate_setlist_features
from utils.logger import get_logger, restrict_to_repo_root
from utils.prediction_utils import update_date_updated

logger = get_logger(__name__)

if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    data_folder = os.path.join(root_dir, "data", "UM")
    collected_folder = os.path.join(data_folder, "collected")
    generated_folder = os.path.join(data_folder, "generated")
    setlist_path = os.path.join(collected_folder, "setlistdata.csv")
    venuedata_path = os.path.join(collected_folder, "venuedata.csv")
    songdata_path = os.path.join(collected_folder, "songdata.csv")
    df = load_setlist_and_showdata(setlist_path, venuedata_path, songdata_path)
    today = datetime.now().strftime("%m-%d-%Y")
    agg_df = aggregate_setlist_features(df, today)
    os.makedirs(generated_folder, exist_ok=True)
    agg_df.to_csv(os.path.join(generated_folder, "todaysnotebook.csv"), index=False)
    logger.info(
        f"Saved Notebook predictions to {restrict_to_repo_root(generated_folder)}"
    )

    # Update date_updated.json after successful save
    update_date_updated("UM", "Notebook", datetime.now().isoformat())
