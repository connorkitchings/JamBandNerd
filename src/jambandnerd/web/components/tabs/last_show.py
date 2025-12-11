from __future__ import annotations

import re
from typing import Any, Dict

import pandas as pd
import streamlit as st
from supabase import Client

from jambandnerd.config import BAND_ID_COLUMNS
from jambandnerd.web.data import (
    fetch_last_collection_time,
    fetch_last_show_setlist,
    fetch_predictions,
    fetch_predictions_for_date,
)

# Temporary in-file configuration until centralized
MODEL_DISPLAY = {"notebook": "Notebook", "ckplus": "CK+"}

WSP_ARTIST_MARKERS = {
    "david bromberg band",
    "new riders of the purple sage",
    "j.j. cale",
    "the doors",
}


def _clean_song_name_for_display(name: str, band: str) -> str:
    """Normalize song names for display/highlighting, stripping unwanted artist credits."""
    if not isinstance(name, str):
        return ""
    cleaned = name.rstrip(">").rstrip("*").strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if band == "wsp":
        if lowered in WSP_ARTIST_MARKERS:
            return ""
        for marker in WSP_ARTIST_MARKERS:
            pattern = re.compile(rf"\s*,\s*{re.escape(marker)}\s*$", re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
    cleaned = cleaned.strip()
    return cleaned


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_last_show_data(_client: Client, band: str, model: str) -> dict[str, Any]:
    """Fetch all necessary data for the last show analysis from Supabase."""
    setlist_df, show_details = fetch_last_show_setlist(_client, band)

    if setlist_df.empty or show_details is None:
        return {"setlist": pd.DataFrame(), "show_details": None}

    show_date = show_details.get("show_date")

    predictions_df = pd.DataFrame()
    if show_date:
        predictions_df = fetch_predictions_for_date(
            _client, band, model, str(pd.to_datetime(show_date).date())
        )
    if predictions_df.empty:
        latest_df, _, _ = fetch_predictions(_client, band, model)
        predictions_df = latest_df

    collection_time = fetch_last_collection_time(_client, band)
    _, _, prediction_meta = fetch_predictions(_client, band, model)
    predicted_at_raw = prediction_meta.get("predicted_at")

    return {
        "setlist": setlist_df,
        "show_details": show_details,
        "predictions": predictions_df,
        "collection_time": collection_time,
        "predicted_at": predicted_at_raw,
        "show_date": show_date,
    }


def _format_show_header(show_details: dict[str, Any]) -> str:
    """Compose a concise show header (date • venue • city)."""
    show_date = show_details.get("show_date")
    formatted_date = (
        pd.to_datetime(show_date).strftime("%m/%d/%Y") if show_date else "Unknown Date"
    )

    venue = (
        show_details.get("venue_name")
        or show_details.get("venue")
        or show_details.get("venuename")
        or "Unknown Venue"
    )
    city = show_details.get("venue_city") or show_details.get("city") or ""
    state = show_details.get("venue_state") or show_details.get("state") or ""

    header_parts = [formatted_date, venue]
    if city and state:
        header_parts.append(f"{city}, {state}")
    elif city:
        header_parts.append(city)
    elif state:
        header_parts.append(state)

    return " • ".join([part for part in header_parts if part])


def _build_prediction_lookup(predictions_df: pd.DataFrame, band: str) -> dict[str, int]:
    """Map song name (normalized) to rank for quick lookup."""
    lookup: Dict[str, int] = {}
    if predictions_df.empty or "song_name" not in predictions_df.columns:
        return lookup

    use_rank_col = "rank" in predictions_df.columns
    for idx, row in predictions_df.iterrows():
        normalized = _clean_song_name_for_display(str(row["song_name"]), band).lower()
        if not normalized:
            continue
        rank = int(row["rank"]) if use_rank_col and pd.notna(row["rank"]) else (idx + 1)
        lookup[normalized] = rank
    return lookup


def _compute_summary(
    setlist_df: pd.DataFrame,
    prediction_ranks: dict[str, int],
    prediction_gaps: dict[str, float],
    prior_song_history: set[str],
    band: str,
) -> dict[str, Any]:
    """Compute hit metrics and bustouts/debuts with band-specific gap thresholds."""
    bustout_thresholds = {"phish": 50, "um": 50, "wsp": 50}
    threshold = bustout_thresholds.get(band, 25)
    total_songs = 0
    total_predicted = 0
    top10_hits = 0
    top25_hits = 0
    top50_hits = 0
    bustouts: list[str] = []
    debuts: list[str] = []
    seen = set()

    unique_song_names = setlist_df["song_name"].dropna()
    for song_name in unique_song_names:
        cleaned = _clean_song_name_for_display(song_name, band)
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        total_songs += 1
        lookup_key = cleaned.lower()

        if lookup_key in prediction_ranks:
            total_predicted += 1
            rank = prediction_ranks[lookup_key]
            if rank <= 10:
                top10_hits += 1
            if rank <= 25:
                top25_hits += 1
            if rank <= 50:
                top50_hits += 1

        gap = prediction_gaps.get(lookup_key)
        if lookup_key not in prior_song_history:
            debuts.append(cleaned)
        elif (
            gap is not None and gap >= threshold and lookup_key not in prediction_ranks
        ):
            bustouts.append(cleaned)

    result = {
        "total_songs": total_songs,
        "predicted": total_predicted,
        "top10": top10_hits,
        "top25": top25_hits,
        "top50": top50_hits,
        "bustouts": sorted(set(bustouts)),
        "bustout_threshold": threshold,
        "debuts": sorted(set(debuts)),
    }

    return result


def _render_hero(
    header: str, model_display: str, predicted_at_str: str, collection_time: str
) -> None:
    """Render the top hero card for last show context."""
    st.markdown(
        f"""
        <div class="jbn-card jbn-hero">
            <div class="jbn-hero__title">Last Show</div>
            <div class="jbn-hero__headline">{header}</div>
            <div class="jbn-hero__meta">
                <span class="jbn-pill jbn-pill--primary">Model: {model_display}</span>
                <span class="jbn-pill jbn-pill--muted">Predicted: {predicted_at_str}</span>
                <span class="jbn-pill">Collected: {collection_time}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_cards(stats: dict[str, Any]) -> None:
    """Show quick-hit metrics for the last show."""
    items = [
        ("Songs Predicted", f"{stats['predicted']}/{stats['total_songs']}"),
        ("Top-10 Hits", f"{stats['top10']}"),
        ("Top-25 Hits", f"{stats['top25']}"),
        ("Top-50 Hits", f"{stats['top50']}"),
    ]
    if stats.get("bustouts"):
        items.append(
            (
                f"Bustouts ({stats['bustout_threshold']}+ shows)",
                f"{len(stats['bustouts'])}",
            )
        )
    if stats.get("debuts"):
        items.append(("Debuts", f"{len(stats['debuts'])}"))

    cards_html = "".join(
        f"<div class='jbn-metric'><div class='jbn-metric__label'>{label}</div><div class='jbn-metric__value'>{value}</div></div>"
        for label, value in items
    )
    container_html = (
        f"<div class='jbn-card'><div class='jbn-grid-3'>{cards_html}</div></div>"
    )
    st.markdown(container_html, unsafe_allow_html=True)


def _render_setlist(
    setlist_df: pd.DataFrame,
    prediction_ranks: dict[str, int],
    prediction_gaps: dict[str, float],
    band: str,
    debuts: set[str],
    bustouts: set[str],
) -> None:
    """Render the setlist grouped by set with prediction badges."""
    if "set_number" not in setlist_df.columns:
        st.warning("Setlist missing 'set_number' column.")
        return

    pos_col = "song_position" if "song_position" in setlist_df.columns else "position"
    if all(col in setlist_df.columns for col in ["set_number", pos_col]):
        setlist_df = setlist_df.drop_duplicates(
            subset=["set_number", pos_col], keep="first"
        )

    sets = setlist_df.groupby("set_number", dropna=True)

    def _set_order_key(v: Any) -> int:
        s = str(v).strip().upper()
        if s in {"E", "ENCORE", "99"}:
            return 99
        if s in {"0", "SOUNDCHECK"}:
            return 0
        try:
            return int(float(s))
        except Exception:
            return 50

    set_numbers = sorted(sets.groups.keys(), key=_set_order_key)
    main_sections = []
    encore_sections = []
    for set_num in set_numbers:
        set_data = sets.get_group(set_num).sort_values(pos_col)
        set_num_str = str(set_num).upper()
        if set_num_str in {"E", "ENCORE", "99"}:
            set_header = "Encore"
        elif set_num_str == "0":
            set_header = "Soundcheck"
        else:
            set_header = f"Set {set_num}"

        songs_html = []
        seen_in_set = set()
        for _, song_row in set_data.iterrows():
            song_name_clean = _clean_song_name_for_display(song_row["song_name"], band)
            if not song_name_clean:
                continue
            key = song_name_clean.lower()
            if key in seen_in_set:
                continue
            seen_in_set.add(key)
            rank = prediction_ranks.get(song_name_clean.lower())
            badges = []
            if key in debuts:
                badges.append('<span class="badge-debut">Debut</span>')
            gap_val = prediction_gaps.get(key)
            if gap_val is not None and key in bustouts and key not in prediction_ranks:
                badges.append('<span class="badge-bustout">Bustout</span>')
            if rank is not None:
                if rank <= 10:
                    badges.append(f'<span class="badge-top10">Top 10 • #{rank}</span>')
                elif rank <= 25:
                    badges.append(f'<span class="badge-top25">Top 25 • #{rank}</span>')
                elif rank <= 50:
                    badges.append(f'<span class="badge-top50">Top 50 • #{rank}</span>')
            badge_html = " " + " ".join(badges) if badges else ""
            songs_html.append(
                f"<div class='jbn-set__song'><span>{song_name_clean}</span>{badge_html}</div>"
            )

        section_html = f"<div class='jbn-set'><div class='jbn-set__title'>{set_header}</div><div class='jbn-set__songs'>{''.join(songs_html) if songs_html else '<em>No songs found</em>'}</div></div>"
        if set_header == "Encore":
            encore_sections.append(section_html)
        else:
            main_sections.append(section_html)

    inner_sections: list[str] = []
    if main_sections:
        inner_sections.append(
            f"<div class='jbn-setlist-row'>{''.join(main_sections)}</div>"
        )
    if encore_sections:
        inner_sections.append(
            f"<div class='jbn-setlist-row jbn-encore'>{''.join(encore_sections)}</div>"
        )

    if inner_sections:
        st.markdown(
            f"<div class='jbn-card jbn-setlist'>{''.join(inner_sections)}</div>",
            unsafe_allow_html=True,
        )


def _chunked(iterable, size: int):
    """Yield successive chunks from iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


@st.cache_data(ttl=3600)  # Cache for 1 hour
def _get_prior_song_history(
    _client: Client, band: str, show_date: str | None
) -> set[str]:
    """Fetch songs played before the given show date for debut detection."""
    if not show_date:
        return set()

    # Normalize to date-only format to avoid timestamp comparison issues
    try:
        show_date_normalized = str(pd.to_datetime(show_date).date())
    except Exception:
        show_date_normalized = show_date

    id_col = BAND_ID_COLUMNS.get(band, "show_id")
    shows_table = f"{band}_shows_raw"
    setlists_table = f"{band}_setlists_raw"

    prior_ids: set[str] = set()
    page = 0
    page_size = 1000
    while True:
        try:
            resp = (
                _client.table(shows_table)
                .select(f"{id_col}, show_date")
                .lt("show_date", show_date_normalized)
                .range(page * page_size, page * page_size + page_size - 1)
                .execute()
            )
        except Exception:
            break
        data = resp.data or []
        for row in data:
            sid = row.get(id_col)
            if sid is not None:
                prior_ids.add(str(sid))
        if len(data) < page_size:
            break
        page += 1

    if not prior_ids:
        return set()

    songs: set[str] = set()

    # Try using the id_col as the setlist foreign key; fall back to show_id if missing
    setlist_id_cols = [id_col, "show_id"] if id_col != "show_id" else ["show_id"]
    for setlist_id_col in setlist_id_cols:
        try:
            for chunk in _chunked(list(prior_ids), 500):
                resp = (
                    _client.table(setlists_table)
                    .select(f"song_name, {setlist_id_col}")
                    .in_(setlist_id_col, chunk)
                    .execute()
                )
                for row in resp.data or []:
                    sid = row.get(setlist_id_col)
                    if sid is None or str(sid) not in prior_ids:
                        continue
                    cleaned = _clean_song_name_for_display(row.get("song_name"), band)
                    if cleaned:
                        songs.add(cleaned.lower())
            if songs:
                break
        except Exception:
            continue

    return songs


def display_last_show_setlist(client: Client, band: str, model: str) -> None:
    """Display the last show's setlist with prediction highlights and metrics."""
    with st.spinner("Loading last show setlist..."):
        data = get_last_show_data(client, band, model)

    setlist_df = data["setlist"]
    show_details = data["show_details"]

    if setlist_df.empty or show_details is None:
        st.warning("No recent setlist data available.")
        return

    header_text = _format_show_header(show_details)
    predictions_df = data["predictions"]
    predictions_df = predictions_df.copy()
    if not predictions_df.empty and "current_gap" in predictions_df.columns:
        try:
            predictions_df = predictions_df[predictions_df["current_gap"] > 3]
        except Exception:
            pass
    if "rank" in predictions_df.columns:
        predictions_df = predictions_df.reset_index(drop=True)
        predictions_df["rank"] = predictions_df.index + 1

    prediction_ranks = _build_prediction_lookup(predictions_df, band)

    # Build gap lookup from ORIGINAL predictions (before filtering) for bustout detection
    # We need ALL gaps, not just those with gap > 3, to detect bustouts correctly
    original_predictions = data["predictions"]
    prediction_gaps = {}
    if not original_predictions.empty and "current_gap" in original_predictions.columns:
        for _, row in original_predictions.iterrows():
            name = _clean_song_name_for_display(
                str(row.get("song_name", "")), band
            ).lower()
            if not name:
                continue
            gap_val = row.get("current_gap")
            try:
                gap = float(gap_val)
            except Exception:
                continue
            prediction_gaps[name] = gap

    prior_history = _get_prior_song_history(client, band, data.get("show_date"))
    stats = _compute_summary(
        setlist_df, prediction_ranks, prediction_gaps, prior_history, band
    )

    predicted_at_raw = data.get("predicted_at")
    predicted_at = (
        pd.to_datetime(predicted_at_raw).floor("min") if predicted_at_raw else None
    )
    predicted_at_str = (
        predicted_at.strftime("%Y-%m-%d %H:%M") if predicted_at else "unknown"
    )
    collection_time = data.get("collection_time")
    collection_str = (
        pd.to_datetime(collection_time).strftime("%Y-%m-%d %H:%M")
        if collection_time
        else "unknown"
    )
    model_display = MODEL_DISPLAY.get(model, model.title())

    _render_hero(header_text, model_display, predicted_at_str, collection_str)
    _render_summary_cards(stats)
    _render_setlist(
        setlist_df,
        prediction_ranks,
        prediction_gaps,
        band,
        debuts={name.lower() for name in stats["debuts"]},
        bustouts={name.lower() for name in stats["bustouts"]},
    )
