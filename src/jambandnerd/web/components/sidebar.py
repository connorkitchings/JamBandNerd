from __future__ import annotations

from typing import Optional

import streamlit as st

from jambandnerd.web.components.common import clean_song_name_for_display

# This is a temporary solution. In the future, this should be moved to a more centralized location.
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


# Forward the function for backward compatibility if needed, though direct import is preferred
def _clean_song_name_for_display(name: str, band: str) -> str:
    return clean_song_name_for_display(name, band)


def get_initial_selection_from_url(
    default_band: str, default_model: str, default_k: int
) -> dict:
    try:
        qp = dict(st.query_params)
    except Exception:
        qp = st.experimental_get_query_params()
    band_val = (
        qp.get("band", [default_band])[0]
        if isinstance(qp.get("band"), list)
        else qp.get("band", default_band)
    )
    model_val = (
        qp.get("model", [default_model])[0]
        if isinstance(qp.get("model"), list)
        else qp.get("model", default_model)
    )
    try:
        k_raw = (
            qp.get("k", [str(default_k)])[0]
            if isinstance(qp.get("k"), list)
            else qp.get("k", str(default_k))
        )
        k_val = int(k_raw)
    except Exception:
        k_val = default_k
    if band_val not in ACTIVE_BAND_SET:
        band_val = default_band
    return {"band": band_val, "model": model_val, "k": k_val}


def sync_query_params(band: str, model: str, k: int) -> None:
    try:
        st.query_params.update(band=band, model=model, k=str(k))
    except Exception:
        st.experimental_set_query_params(band=band, model=model, k=str(k))


def display_sidebar(
    initial_band: Optional[str] = None,
    initial_model: Optional[str] = None,
    initial_k: Optional[int] = None,
) -> tuple[str, str, int]:
    """Render the sidebar and return selected options."""
    st.sidebar.title("JamBandNerd")

    sorted_bands = sorted(
        ((slug, BAND_CONFIG[slug]) for slug in ACTIVE_BANDS),
        key=lambda item: item[1]["display_name"].lower(),
    )
    band_display_names = [config["display_name"] for _, config in sorted_bands]
    display_to_slug = {config["display_name"]: slug for slug, config in sorted_bands}

    # Only set index on first load, then let widget maintain its own state
    if "band_selector" not in st.session_state:
        # First load: use initial_band to set index
        if initial_band in ACTIVE_BAND_SET:
            initial_band_display = BAND_CONFIG[initial_band]["display_name"]  # type: ignore[index]
        else:
            initial_band_display = band_display_names[0]
        try:
            band_index = band_display_names.index(initial_band_display)
        except ValueError:
            band_index = 0
    else:
        # After first load: don't override widget state, use current widget value
        band_index = band_display_names.index(st.session_state.band_selector)

    selected_band_display = st.sidebar.selectbox(
        "Select a Band", band_display_names, index=band_index, key="band_selector"
    )
    selected_band_slug = display_to_slug[selected_band_display]

    # Same logic for model
    model_display_names = [config["display_name"] for config in MODEL_CONFIG.values()]
    if "model_selector" not in st.session_state:
        if initial_model in MODEL_CONFIG:
            initial_model_display = MODEL_CONFIG[initial_model]["display_name"]  # type: ignore[index]
        else:
            initial_model_display = model_display_names[0]
        try:
            model_index = model_display_names.index(initial_model_display)
        except ValueError:
            model_index = 0
    else:
        model_index = model_display_names.index(st.session_state.model_selector)

    selected_model_display = st.sidebar.radio(
        "Select a Model", model_display_names, index=model_index, key="model_selector"
    )
    selected_model_slug = next(
        slug
        for slug, config in MODEL_CONFIG.items()
        if config["display_name"] == selected_model_display
    )

    # Compact model explanation with tooltip-like hint
    st.sidebar.caption(
        f"{selected_model_display}: {MODEL_CONFIG[selected_model_slug]['explanation']}"
    )

    # Same logic for k
    k_options = [10, 25, 50]
    if "k_selector" not in st.session_state:
        if initial_k in k_options:
            k_index = k_options.index(initial_k)  # type: ignore[arg-type]
        else:
            k_index = 2
    else:
        k_index = k_options.index(st.session_state.k_selector)

    selected_k = st.sidebar.selectbox(
        "K for Accuracy (Top-K)",
        k_options,
        index=k_index,
        help="Number of top-ranked songs considered for the recall metric.",
        key="k_selector",
    )
    st.sidebar.caption(
        "Top-K: Of the songs actually played, the fraction that appear in the Top-K predictions."
    )

    return selected_band_slug, selected_model_slug, selected_k
