"""
WSP Show Scraping Module
Scrapes show data from everydaycompanion.com and processes into DataFrame.
"""

import re
from datetime import date

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from .utils import get_logger

logger = get_logger(__name__, add_console_handler=True)


def scrape_wsp_shows(
    base_url: str = "http://www.everydaycompanion.com/",
    start_year: int = 1985,
    years: list = None,
) -> "pd.DataFrame":
    """
    Scrape and return show data for all years (except those in years) from everydaycompanion.com.

    Args:
        base_url (str): Base URL for Everyday Companion. Defaults to BASE_URL from config.
        start_year (int): First year to scrape. Defaults to 1985.
        years (list): Years to skip. Defaults to SKIP_YEARS from config.
    Returns:
        pd.DataFrame: DataFrame of show dates and venues.
    """
    if years is None:
        years = [2004]
    today = date.today()
    this_year = today.year
    tour_list = [x for x in range(start_year, this_year + 1) if x not in years]
    tour_df_list = []
    for yr in tour_list:
        yr_str = str(yr)[-2:]
        year_link = f"{base_url}asp/tour{yr_str}.asp"
        try:
            response = requests.get(year_link)
            soup = BeautifulSoup(response.content, "html.parser")
            p_tag = soup.find("p")
            if p_tag is None:
                logger.warning("No <p> tag found for year %s.", yr)
                continue
            tour_string = p_tag.get_text()
        except AttributeError as e:
            logger.warning(
                "No data on Everyday Companion for %s: %s", yr, e, exc_info=True
            )
            continue
        except Exception as e:
            logger.error(
                "Unexpected error fetching/parsing year %s: %s", yr, e, exc_info=True
            )
            continue
        tour_string = re.sub(r"\?\?", "00", tour_string)
        # Split the string into individual dates
        venues = [
            venue.strip()
            for venue in re.split(r"\d{2}/\d{2}/\d{2}", tour_string)
            if venue.strip()
        ]
        dates = re.findall(r"\d{2}/\d{2}/\d{2}", tour_string)

        tour_data = pd.DataFrame({"date": dates, "venue": venues})

        # If tour_data is empty, skip this year
        if tour_data.empty:
            logger.warning("No show data extracted for year %s, skipping.", yr)
            continue
        tour_data["link_date"] = tour_data["date"].apply(
            lambda x: str(x[6:]) + str(x[0:2]) + str(x[3:5])
        )
        for index, value in tour_data["link_date"].items():
            if value[0] in ["8", "9"]:
                tour_data.at[index, "link_date"] = "19" + value
            if value[0] in ["0", "1", "2"]:
                tour_data.at[index, "link_date"] = "20" + value
        tour_data["date_count"] = tour_data.groupby("link_date").cumcount() + 1
        tour_data["assigned_letter"] = tour_data["date_count"].apply(
            lambda x: chr(ord("a") + x - 1)
        )
        tour_data["link"] = (
            base_url
            + "setlists/"
            + tour_data["link_date"]
            + tour_data["assigned_letter"]
            + ".asp"
        )
        tour_data["running_count"] = tour_data.groupby(["date", "venue"]).cumcount() + 1
        tour_data = tour_data.drop(columns=["date_count", "assigned_letter"])

        # Extract year, month, day from link
        tour_data[["year", "month", "day"]] = tour_data["link"].str.extract(
            r"(\d{4})(\d{2})(\d{2})"
        )
        tour_data["date_ec"] = tour_data["date"]
        tour_data["date"] = pd.to_datetime(
            tour_data["date"], format="%m/%d/%y", errors="coerce"
        ).fillna(pd.NaT)
        # Standardize to four-digit year string for consistency
        tour_data["date"] = tour_data["date"].dt.strftime("%m/%d/%Y")
        tour_data["weekday"] = pd.to_datetime(
            tour_data["date"], errors="coerce"
        ).dt.strftime("%A")
        try:
            tour_data[["venue_name", "city", "state"]] = tour_data["venue"].str.rsplit(
                ", ", n=2, expand=True
            )
            # If split fails to create all columns, fill missing with None
            if set(["venue_name", "city", "state"]) - set(tour_data.columns):
                tour_data = tour_data.reindex(
                    columns=[*tour_data.columns, "venue_name", "city", "state"]
                )
        except Exception as e:
            logger.error(
                "[%s] Venue split error: %s. Data: %s",
                yr,
                e,
                tour_data["venue"].head(2).tolist(),
            )
            continue
        tour_data.rename(
            columns={"venue": "venue_full", "venue_name": "venue"}, inplace=True
        )
        tour_data["venue_full"] = tour_data["venue_full"].str.upper()
        tour_data.drop(columns=["running_count"], inplace=True)
        tour_data["show_index_withinyear"] = tour_data.index + 1
        tour_df_list.append(tour_data)
    if not tour_df_list:
        logger.error("No tour data was collected for any year.")
        return pd.DataFrame()
    combined_tour_data = pd.concat(tour_df_list, ignore_index=True)
    combined_tour_data["show_index_overall"] = combined_tour_data.index + 1
    combined_tour_data["date_ec"] = combined_tour_data["date"].astype(str)
    combined_tour_data["date_ec"] = combined_tour_data.apply(
        lambda row: f"??/{row['day']}/{row['year'][-2:]}"
        if row["month"] == "00"
        else row["date_ec"],
        axis=1,
    )
    combined_tour_data["date_ec"] = combined_tour_data.apply(
        lambda row: f"{row['month']}/??/{row['year'][-2:]}"
        if row["day"] == "00"
        else row["date_ec"],
        axis=1,
    )
    combined_tour_data["date_ec"] = combined_tour_data.apply(
        lambda row: f"??/??/{row['year'][-2:]}"
        if ((row["month"] == "00") & (row["day"] == "00"))
        else row["date_ec"],
        axis=1,
    )
    combined_tour_data.sort_values(by=["show_index_overall", "venue"]).reset_index(
        drop=True, inplace=True
    )
    mask = (combined_tour_data["venue"] != combined_tour_data["venue"].shift(1)) | (
        combined_tour_data["show_index_overall"]
        != combined_tour_data["show_index_overall"].shift(1) + 1
    )
    combined_tour_data["run_index"] = mask.cumsum()
    combined_tour_data = combined_tour_data[
        [
            "date",
            "year",
            "month",
            "day",
            "weekday",
            "date_ec",
            "venue",
            "city",
            "state",
            "show_index_overall",
            "show_index_withinyear",
            "run_index",
            "venue_full",
            "link",
        ]
    ]
    venue_conditions = [
        (combined_tour_data["venue"] == "ADAMS CENTER")
        & (combined_tour_data["state"] == "MT"),
        (combined_tour_data["venue"] == "AUDITORIUM THEATRE")
        & (combined_tour_data["city"] == "CHICAGO"),
        (combined_tour_data["venue"] == "BAYFRONT ARENA")
        & (combined_tour_data["state"] == "FL"),
        (combined_tour_data["venue"] == "FLEET PAVILION")
        & (combined_tour_data["city"] == "BOSTON"),
        (combined_tour_data["venue"] == "CAESAR'S TAHOE SHOWROOM")
        & (combined_tour_data["state"] == "NV"),
    ]
    venue_replacements = [
        "ADAMS FIELDHOUSE, UNIVERSITY OF MONTANA",
        "AUDITORIUM THEATER, ROOSEVELT UNIVERSITY",
        "BAYFRONT AUDITORIUM",
        "CAESAR'S TAHOE",
        "CAESAR'S TAHOE",
    ]
    city_conditions = [
        (combined_tour_data["venue"] == "23 EAST CABARET")
        & (combined_tour_data["state"] == "PA"),
        (combined_tour_data["venue"] == "CAESAR'S TAHOE"),
        (combined_tour_data["venue"] == "CYNTHIA WOODS MITCHELL PAVILLION"),
        (combined_tour_data["city"].isin(["N. LITTLE ROCK", "NORTH LITTLE ROCK"])),
        (combined_tour_data["city"] == "MT. CRESTED BUTTE"),
        (combined_tour_data["city"] == "SNOWMASS VILLAGE"),
        (combined_tour_data["city"] == "ELON COLLEGE"),
        (combined_tour_data["city"] == "N. MYRTLE BEACH"),
    ]
    city_replacements = [
        "PHILADELPHIA",
        "LAKE TAHOE",
        "THE WOODLANDS",
        "LITTLE ROCK",
        "CRESTED BUTTE",
        "SNOWMASS",
        "ELON",
        "MYRTLE BEACH",
    ]
    combined_tour_data["venue"] = np.select(
        venue_conditions, venue_replacements, default=combined_tour_data["venue"]
    )
    combined_tour_data["city"] = np.select(
        city_conditions, city_replacements, default=combined_tour_data["city"]
    )
    combined_tour_data["date"] = pd.to_datetime(
        combined_tour_data["date"], format="%m/%d/%Y", errors="coerce"
    )
    return combined_tour_data
