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


@dataclass(frozen=True)
class RecentSetlistCompletenessResult:
    band: str
    cutoff: str
    end_date: str
    recent_show_count: int
    missing_show_count: int
    missing_show_ids: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.missing_show_count == 0

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ok"] = self.ok
        payload["missing_show_ids"] = list(self.missing_show_ids)
        return payload


def audit_recent_setlist_completeness(
    band: str,
    *,
    client=None,
    emit_text: bool = True,
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
    if not shows.empty:
        show_ids_raw = [show_id for show_id in shows[id_col].dropna().tolist()]
        show_ids = {str(show_id) for show_id in show_ids_raw}
        setlist_ids = fetch_column_values_for_ids(
            f"{band}_setlists_raw",
            id_column=id_col,
            ids=show_ids_raw,
            client=client,
        )
        missing_show_ids = tuple(sorted(show_ids - setlist_ids))

    result = RecentSetlistCompletenessResult(
        band=band,
        cutoff=cutoff,
        end_date=end_date,
        recent_show_count=0 if shows.empty else len(shows),
        missing_show_count=len(missing_show_ids),
        missing_show_ids=missing_show_ids,
    )

    if emit_text:
        print(
            f"Checking data freshness for {band} from {cutoff} through {end_date} "
            "(completed shows only)"
        )
        if result.recent_show_count <= 0:
            print(f"ℹ️ No recent completed shows found for {band} in the last 7 days")
        elif result.ok:
            print(f"✅ All recent shows have setlist data for {band}")
        else:
            print(
                f"::warning::WARNING: {result.missing_show_count} recent shows missing "
                f"setlist data for {band}"
            )
            print(
                f"WARNING: {result.missing_show_count} recent shows missing setlist data"
            )
            for show_id in result.missing_show_ids[:5]:
                show = shows[shows[id_col].astype(str) == show_id].iloc[0]
                print(f"  - {show.get('show_date', 'Unknown date')} (ID: {show_id})")

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

    except Exception as e:
        print(f"::error::Error checking data freshness: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
