import os
import sys
from dataclasses import asdict, dataclass

import pandas as pd

# Add src to path if running from repo root
repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, "src"))

try:
    from jambandnerd.config import BAND_ID_COLUMNS
    from jambandnerd.config.bands import (
        get_excluded_prediction_show_dates,
        get_excluded_prediction_show_ids,
    )
    from jambandnerd.db.connection import get_supabase_client
except Exception as e:
    print(f"::error::Failed to import pipeline modules: {e}")
    raise SystemExit(1) from e

from scripts.common import (
    completed_show_window,
    fetch_column_values_for_ids,
    fetch_table_rows,
)

_completed_show_window = completed_show_window


def _first_nonempty_str(
    row: pd.Series | dict[str, object], keys: tuple[str, ...]
) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value):
            text = str(value).strip()
            if text:
                return text
    return None


def _build_missing_show_meta(
    row: pd.Series | dict[str, object],
    *,
    id_col: str,
) -> dict[str, str | None]:
    return {
        "show_id": _first_nonempty_str(row, (id_col, "show_id")),
        "show_date": _first_nonempty_str(row, ("show_date", "showdate")),
        "venue_name": _first_nonempty_str(row, ("venue_name", "venue")),
        "city": _first_nonempty_str(row, ("city", "venue_city")),
        "state": _first_nonempty_str(row, ("state", "venue_state", "region")),
        "country": _first_nonempty_str(row, ("country", "venue_country")),
    }


@dataclass(frozen=True)
class RecentSetlistCompletenessResult:
    band: str
    cutoff: str
    end_date: str
    recent_show_count: int
    missing_show_count: int
    missing_show_ids: tuple[str, ...]
    partial_show_count: int = 0
    partial_show_ids: tuple[str, ...] = ()
    min_unique_songs: int = 3
    missing_shows: tuple[dict[str, str | None], ...] = ()

    @property
    def ok(self) -> bool:
        return self.missing_show_count == 0 and self.partial_show_count == 0

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ok"] = self.ok
        payload["missing_show_ids"] = list(self.missing_show_ids)
        payload["partial_show_ids"] = list(self.partial_show_ids)
        payload["missing_shows"] = [dict(item) for item in self.missing_shows]
        return payload


def _fetch_setlist_ids_for_shows(
    client,
    table_name: str,
    id_column: str,
    show_ids: set[str],
) -> set[str]:
    return fetch_column_values_for_ids(
        table_name,
        id_column=id_column,
        ids=list(show_ids),
        client=client,
    )


def _fetch_song_counts_per_show(
    client,
    table_name: str,
    id_column: str,
    show_ids: set[str],
) -> dict[str, int]:
    """Return unique song count per show_id for shows in the setlists table."""
    if not show_ids:
        return {}
    rows = fetch_table_rows(
        table_name,
        filters=[("in", id_column, list(show_ids))],
        client=client,
    )
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    if "song_name" not in df.columns or id_column not in df.columns:
        return {}
    counts = (
        df.dropna(subset=[id_column, "song_name"])
        .assign(show_id=lambda d: d[id_column].astype(str))
        .groupby("show_id")["song_name"]
        .nunique()
    )
    return counts.to_dict()


def audit_recent_setlist_completeness(
    band: str,
    *,
    client=None,
    emit_text: bool = True,
    min_unique_songs: int = 3,
) -> RecentSetlistCompletenessResult:
    cutoff, end_date = completed_show_window()
    id_col = BAND_ID_COLUMNS.get(band, "show_id")
    client = client or get_supabase_client()

    shows_data = fetch_table_rows(
        f"{band}_shows_raw",
        filters=[("gte", "show_date", cutoff), ("lte", "show_date", end_date)],
        client=client,
    )
    shows = pd.DataFrame(shows_data) if shows_data else pd.DataFrame()

    missing_show_ids: tuple[str, ...] = ()
    partial_show_ids: tuple[str, ...] = ()
    missing_shows: tuple[dict[str, str | None], ...] = ()
    song_counts: dict[str, int] = {}
    setlist_table = f"{band}_setlists_raw"

    if not shows.empty and id_col in shows.columns:
        excluded_ids = get_excluded_prediction_show_ids(band)
        excluded_dates = get_excluded_prediction_show_dates(band)
        if excluded_ids:
            shows = shows[
                ~shows[id_col].astype(str).str.strip().isin(excluded_ids)
            ].copy()
        if excluded_dates and "show_date" in shows.columns:
            shows = shows[
                ~shows["show_date"].astype(str).str.strip().isin(excluded_dates)
            ].copy()

    if not shows.empty and id_col in shows.columns:
        show_ids_raw = [show_id for show_id in shows[id_col].dropna().tolist()]
        show_ids = {str(show_id) for show_id in show_ids_raw}

        present_ids = _fetch_setlist_ids_for_shows(
            client,
            setlist_table,
            id_col,
            show_ids,
        )
        present_to_check = present_ids
        song_counts = _fetch_song_counts_per_show(
            client,
            setlist_table,
            id_col,
            present_to_check,
        )

        complete_ids = {
            sid for sid in present_ids if song_counts.get(sid, 0) >= min_unique_songs
        }
        covered_dates: set[str] = set()
        if "show_date" in shows.columns and complete_ids:
            covered_dates = {
                str(row.get("show_date")).strip()
                for _, row in shows.iterrows()
                if str(row.get(id_col)) in complete_ids and row.get("show_date")
            }

        uncovered_ids = {
            str(row.get(id_col))
            for _, row in shows.iterrows()
            if row.get(id_col) is not None
            and str(row.get("show_date") or "").strip() not in covered_dates
        }

        missing = (show_ids - present_ids) & uncovered_ids
        missing_show_ids = tuple(sorted(missing))

        below_threshold = {
            sid
            for sid in (present_ids & uncovered_ids)
            if song_counts.get(sid, 0) < min_unique_songs
        }
        partial_show_ids = tuple(sorted(below_threshold))

        incomplete_ids = missing | below_threshold
        if incomplete_ids:
            incomplete_rows = [
                _build_missing_show_meta(row, id_col=id_col)
                for _, row in shows.iterrows()
                if str(row.get(id_col)) in incomplete_ids
            ]
            incomplete_rows.sort(
                key=lambda item: (
                    item.get("show_date") or "",
                    item.get("show_id") or "",
                )
            )
            missing_shows = tuple(incomplete_rows)

    result = RecentSetlistCompletenessResult(
        band=band,
        cutoff=cutoff,
        end_date=end_date,
        recent_show_count=0 if shows.empty else len(shows),
        missing_show_count=len(missing_show_ids),
        missing_show_ids=missing_show_ids,
        partial_show_count=len(partial_show_ids),
        partial_show_ids=partial_show_ids,
        min_unique_songs=min_unique_songs,
        missing_shows=missing_shows,
    )

    if emit_text:
        print(
            f"Checking data freshness for {band} from {cutoff} through {end_date} "
            "(completed shows only)"
        )
        if result.recent_show_count <= 0:
            print(f"ℹ️ No recent completed shows found for {band} in the last 7 days")
        elif result.ok:
            print(f"✅ All recent shows have complete setlist data for {band}")
        else:
            if result.missing_show_count > 0:
                print(
                    f"::warning::WARNING: {result.missing_show_count} recent shows missing "
                    f"setlist data for {band}"
                )
                for show_id in result.missing_show_ids[:5]:
                    show = shows[shows[id_col].astype(str) == show_id].iloc[0]
                    print(
                        f"  - {show.get('show_date', 'Unknown date')} (ID: {show_id})"
                    )
            if result.partial_show_count > 0:
                print(
                    f"::warning::WARNING: {result.partial_show_count} recent shows have "
                    f"partial setlist data (<{result.min_unique_songs} unique songs) for {band}"
                )
                for show_id in result.partial_show_ids[:5]:
                    nc = song_counts.get(show_id, 0)
                    show = shows[shows[id_col].astype(str) == show_id].iloc[0]
                    print(
                        f"  - {show.get('show_date', 'Unknown date')} (ID: {show_id}) "
                        f"— only {nc} unique song(s)"
                    )

    return result


def main():
    band = os.environ.get("BAND")
    if not band:
        print("::error::BAND environment variable not set")
        sys.exit(1)

    try:
        result = audit_recent_setlist_completeness(
            band,
            client=get_supabase_client(),
            emit_text=True,
        )
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"missing_data={'false' if result.ok else 'true'}\n")
                f.write(f"missing_count={result.missing_show_count}\n")
                f.write(
                    f"partial_data={'true' if result.partial_show_count > 0 else 'false'}\n"
                )
                f.write(f"partial_count={result.partial_show_count}\n")

    except Exception as e:
        print(f"::error::Error checking data freshness: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
