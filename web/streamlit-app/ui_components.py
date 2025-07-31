"""UI components for Jam Band Nerd app."""

import streamlit as st


def display_method_explanation(file_label: str) -> None:
    """
    Display an explanation of the selected prediction method.

    Args:
        file_label: String indicating prediction method ("CK+" or "Notebook")
    """
    method_explanations = {
        "CK+": (
            """
<div style='font-size:0.95em; color:#fff; margin-bottom:10px;'>
<b>CK+ Method:</b> This method uses a machine learning model trained on historical setlists and song transitions to predict the most likely songs for the next show. It incorporates recency, rarity, and show-to-show transitions to generate a ranked list and highlight songs with a high probability of being played tonight.
</div>
            """
        ),
        "Notebook": (
            """
<div style='font-size:0.95em; color:#fff; margin-bottom:10px;'>
<b>Notebook Method:</b> Inspired by Phish.net's "Trey's Notebook," this method predicts setlists by focusing on songs played most frequently in the last year, while excluding songs played in the last three shows. It identifies songs that are in rotation but not overplayed, ranking them by recent play frequency and providing stats like last played date and average gap.
</div>
            """
        ),
    }

    st.sidebar.markdown(method_explanations.get(file_label, ""), unsafe_allow_html=True)


def display_disclaimer() -> None:
    """Display a disclaimer for the user."""
    disclaimer = "<div style='font-size:0.9em; color:#888; margin-top:12px; text-align:center;'>Predictions are based on the latest data available in the JamBandNerd database.</div>"
    st.markdown(disclaimer, unsafe_allow_html=True)
