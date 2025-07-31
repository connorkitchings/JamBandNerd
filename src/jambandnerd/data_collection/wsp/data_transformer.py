import pandas as pd



def transform_songs_for_supabase(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms the raw songs DataFrame for Supabase.

    - Converts date columns to 'MM/DD/YYYY' strings.

    Args:
        df: The raw DataFrame from scrape_wsp_songs.

    Returns:
        A new DataFrame formatted for the 'wsp_songs' table.
    """
    df_copy = df.copy()
    df_copy["first_played"] = df_copy["first_played"].dt.strftime("%m/%d/%Y")
    df_copy["last_played"] = df_copy["last_played"].dt.strftime("%m/%d/%Y")
    return df_copy


def transform_shows_for_supabase(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms the raw shows DataFrame for Supabase.

    - Converts the main date column to a 'MM/DD/YYYY' string.

    Args:
        df: The raw DataFrame from scrape_wsp_shows.

    Returns:
        A new DataFrame formatted for the 'wsp_shows' table.
    """
    df_copy = df.copy()
    df_copy["date"] = df_copy["date"].dt.strftime("%m/%d/%Y")
    return df_copy


def transform_setlists_for_supabase(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms the raw setlists DataFrame for Supabase.

    - Converts 'is_into' from int to boolean.

    Args:
        df: The raw DataFrame from scrape_setlists.

    Returns:
        A new DataFrame formatted for the 'wsp_setlists' table.
    """
    df_copy = df.copy()
    df_copy["is_into"] = df_copy["is_into"].astype(bool)
    return df_copy
