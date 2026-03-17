from __future__ import annotations

import streamlit as st

from jambandnerd.web.components.tabs.performance import MODEL_CONFIG

MODEL_SUMMARY = {
    "notebook": {
        "title": "Notebook (frequency-based)",
        "intro": "Simple, transparent baseline that leans on recent popularity while avoiding over-predicting recents.",
        "bullets": [
            "Looks back 1 year of shows and counts plays.",
            "Removes songs played in the last 3 shows.",
            "Breaks ties by how long since last played (current gap).",
        ],
    },
    "ckplus": {
        "title": "CK+ (gap-based)",
        "intro": "Gap-driven model focused on how overdue songs are, balancing consistency and recency.",
        "bullets": [
            "Uses ~5-year gaps between plays for each song.",
            "Ranks by gap ratio/Z-score (how overdue vs. typical).",
            "Down-weights rare or erratic songs; excludes extreme-gap 'retired' songs.",
        ],
    },
}


def display_about(selected_model: str) -> None:
    """Render the About tab with project context and model explainer."""
    st.markdown(
        """
        <div class="jbn-card jbn-hero" style="align-items: flex-start; text-align: left;">
            <div class="jbn-hero__title">About</div>
            <div class="jbn-hero__headline" style="color: var(--text-color);">JamBandNerd</div>
        </div>
        <div class="jbn-card">
            <div class="jbn-hero__title">Overview</div>
            <p>JamBandNerd collects jam band setlists, transforms them in-memory, and serves ranked predictions for multiple bands. Pipelines run daily in GitHub Actions; Supabase stores raw data, predictions, and accuracy; Streamlit powers this UI.</p>
            <ul>
                <li>Collectors per band with fallbacks where needed (e.g., WSP with Playwright).</li>
                <li>Two models: Notebook (frequency-based) and CK+ (gap-based).</li>
                <li>Accuracy tracked per show and aggregated for quick benchmarking.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    model_display = MODEL_CONFIG.get(selected_model, {}).get(
        "display_name", selected_model.title()
    )
    summary = MODEL_SUMMARY.get(
        selected_model,
        {"title": model_display, "intro": "Model summary unavailable.", "bullets": []},
    )
    bullets_html = "".join(f"<li>{b}</li>" for b in summary["bullets"])
    st.markdown(
        f"""
        <div class="jbn-card">
            <div class="jbn-hero__title">How This Model Works</div>
            <div class="jbn-hero__headline">{summary["title"]}</div>
            <p>{summary["intro"]}</p>
            <ul>{bullets_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
