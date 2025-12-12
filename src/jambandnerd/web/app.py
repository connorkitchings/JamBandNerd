from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from jambandnerd.db.connection import get_supabase_client
from jambandnerd.web import theme
from jambandnerd.web.components.sidebar import (
    display_sidebar,
    get_initial_selection_from_url,
    sync_query_params,
)
from jambandnerd.web.components.tabs.about import display_about
from jambandnerd.web.components.tabs.explorer import display_historical_explorer
from jambandnerd.web.components.tabs.last_show import display_last_show_setlist
from jambandnerd.web.components.tabs.performance import display_historical_accuracy
from jambandnerd.web.components.tabs.predictions import display_predictions


def _configure_logging() -> None:
    """Configure basic logging to a local .tmp file, creating the directory if needed."""
    root_dir = Path(__file__).resolve().parents[3]
    log_dir = root_dir / ".tmp"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(filename=log_dir / "app.log", level=logging.INFO)


def apply_theme() -> None:
    """Inject CSS variables and shared styles for the app."""
    css_path = Path(__file__).resolve().parent / "style.css"
    try:
        css = css_path.read_text()
    except FileNotFoundError:
        css = ""

    style_vars = "\n".join(
        [
            ":root {",
            f"  --primary-color: {theme.PRIMARY_COLOR};",
            f"  --success-color: {theme.SUCCESS_COLOR};",
            f"  --warning-color: {theme.WARNING_COLOR};",
            f"  --info-color: {theme.INFO_COLOR};",
            f"  --background-color: {theme.BACKGROUND_COLOR};",
            f"  --surface-color: {theme.SURFACE_COLOR};",
            f"  --border-color: {theme.BORDER_COLOR};",
            f"  --text-color: {theme.TEXT_COLOR};",
            f"  --text-muted: {theme.TEXT_MUTED};",
            f"  --white: {theme.WHITE};",
            f"  --black: {theme.BLACK};",
            f"  --gray: {theme.GRAY};",
            "}",
        ]
    )

    st.markdown(f"<style>\n{style_vars}\n{css}\n</style>", unsafe_allow_html=True)


def main() -> None:
    """Main application entry point."""
    _configure_logging()
    st.set_page_config(page_title="JamBandNerd", layout="wide")
    apply_theme()
    st.markdown(
        "<h1 style='text-align: center;'>JamBandNerd</h1>", unsafe_allow_html=True
    )

    defaults = {"band": "goose", "model": "notebook", "k": 50}

    # Initialize session state from URL params on first load only
    if "initialized" not in st.session_state:
        initial_selection = get_initial_selection_from_url(
            default_band=defaults["band"],
            default_model=defaults["model"],
            default_k=defaults["k"],
        )
        st.session_state.current_band = initial_selection["band"]
        st.session_state.current_model = initial_selection["model"]
        st.session_state.current_k = initial_selection["k"]
        st.session_state.initialized = True

    # Use session state as source of truth
    selected_band, selected_model, selected_k = display_sidebar(
        initial_band=st.session_state.current_band,
        initial_model=st.session_state.current_model,
        initial_k=st.session_state.current_k,
    )

    # Update session state if selection changed
    st.session_state.current_band = selected_band
    st.session_state.current_model = selected_model
    st.session_state.current_k = selected_k

    # Sync to URL for sharing (non-blocking)
    sync_query_params(selected_band, selected_model, selected_k)

    supabase_client = get_supabase_client()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Predictions",
            "Last Show Analysis",
            "Historical Explorer",
            "Model Performance",
            "About",
        ]
    )

    with tab1:
        display_predictions(supabase_client, selected_band, selected_model)

    with tab2:
        st.markdown(
            "<h3 style='text-align: center;'>Last Show Setlist</h3>",
            unsafe_allow_html=True,
        )
        display_last_show_setlist(supabase_client, selected_band, selected_model)

    with tab3:
        display_historical_explorer(supabase_client, selected_band, selected_model)

    with tab4:
        display_historical_accuracy(
            supabase_client, selected_band, selected_model, selected_k
        )

    with tab5:
        display_about(selected_model)


if __name__ == "__main__":
    main()
