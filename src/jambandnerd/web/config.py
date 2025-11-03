from __future__ import annotations

BAND_CONFIG = {
    "eggy": {
        "display_name": "Eggy",
        "shows_table": "eggy_shows_raw",
    },
    "billy": {
        "display_name": "Billy Strings",
        "shows_table": "billy_shows_raw",
    },
    "goose": {
        "display_name": "Goose",
        "shows_table": "goose_shows_raw",
    },
    "phish": {
        "display_name": "Phish",
        "shows_table": "phish_shows_raw",
    },
    "wsp": {
        "display_name": "Widespread Panic",
        "shows_table": "wsp_shows_raw",
    },
    "um": {
        "display_name": "Umphrey's McGee",
        "shows_table": "um_shows_raw",
    },
}

ACTIVE_BANDS = list(BAND_CONFIG.keys())
ACTIVE_BAND_SET = set(ACTIVE_BANDS)

MODEL_CONFIG = {
    "notebook": {
        "display_name": "Notebook",
        "explanation": "Focuses on songs most frequently played in the last year, excluding those played in the last three shows. It surfaces in-rotation songs and provides last played date and current gap context.",
        "columns": {
            "rank": "Rank",
            "song_name": "Song",
            "plays_past_year": "Plays in Last Year",
            "LTP": "Last Played",
            "current_gap": "Current Gap",
        },
    },
    "ckplus": {
        "display_name": "CK+",
        "explanation": "Gap-based statistical predictor that ranks songs by how overdue they are, using historical show-to-show gaps, recency, and reliability scaling. It emphasizes songs likely to return given typical gaps.",
        "columns": {
            "rank": "Rank",
            "song_name": "Song",
            "LTP": "Last Played",
            "current_gap": "Current Gap",
            "avg_gap": "Avg Gap",
            "gap_ratio": "Gap Ratio",
            "gap_z_score": "Gap Z-Score",
            "ckplus_score": "CK+ Score",
        },
    },
}

WSP_ARTIST_MARKERS = {
    "david bromberg band",
    "new riders of the purple sage",
    "j.j. cale",
    "the doors",
}
