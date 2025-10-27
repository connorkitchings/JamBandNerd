# Transformations and Feature Engineering

This document describes the data transformation and feature engineering pipeline, which is a critical component of the JamBandNerd project. The primary script for this process is `src/jambandnerd/transformations/gaps.py`, which is responsible for converting raw show and setlist data into a format that can be used by the prediction models.

## Overview

The transformation pipeline is designed to be band-agnostic and is used by all models in the project. It takes raw data from the Supabase database, performs a series of transformations, and generates a rich set of features that are then passed to the prediction models.

The key design principles of the transformation pipeline are:

- **No Data Leakage**: The pipeline strictly adheres to a `reference_date` cutoff, ensuring that no data from the future is used to generate features for a given prediction.
- **In-Memory Processing**: All transformations are performed in-memory using pandas DataFrames, which is efficient and avoids the need for intermediate database tables.
- **Centralized Logic**: The feature engineering logic is centralized in the `gaps.py` module, ensuring that all models use a consistent set of features.

## The `ModelData` Container

The output of the transformation pipeline is a `ModelData` dataclass object, which serves as a container for all the data required by the prediction models. It has the following attributes:

- `historical_plays`: A DataFrame of all historical plays before the `reference_date`.
- `master_feature_set`: A DataFrame of song features aggregated over their entire history.
- `reference_date`: The specific date for which predictions are being generated.
- `reference_index`: The chronological index of the reference show.
- `recently_played_songs`: A list of songs played in the 3 shows immediately preceding the `reference_date`.
- `diagnostics`: A dictionary of metadata about the transformation process.

## Feature Engineering Process

The `generate_model_data` function in `gaps.py` orchestrates the feature engineering process. Here is a step-by-step breakdown of the logic:

1. **Data Normalization**: The function first normalizes the column names of the input DataFrames to ensure consistency between different data sources (e.g., mapping `showdate` to `show_date`).

2. **Historical Data Filtering**: It filters the shows and setlists to include only data that occurred *before* the `reference_date`. This is the crucial step that prevents data leakage.

3. **Show Indexing**: It computes a stable, chronological `show_index` for all historical shows. This index is used for calculating gaps between song performances.

4. **Play-by-Play Data**: It creates a `historical_plays` DataFrame that contains a record for every song played in every historical show, along with its `show_index` and `show_date`.

5. **Master Feature Set**: It then calculates a `master_feature_set` DataFrame, which contains the following features for each song:
    - `times_played`: The total number of times the song has been played in the historical data.
    - `last_played_index`: The `show_index` of the last time the song was played.
    - `last_played_date`: The date of the last time the song was played.
    - `avg_gap`: The average number of shows between plays of the song.
    - `std_gap`: The standard deviation of the gaps between plays.

6. **Recently Played Songs**: It identifies all songs that were played in the last three completed shows before the `reference_date`.

This rich set of features is then passed to the prediction models, which use them to generate their predictions.
