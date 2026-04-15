"""Fantasy Goose integration helpers and browser automation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from playwright.async_api import Browser, Page, async_playwright

from jambandnerd.db.operations import fetch_prediction_songs_for_date

logger = logging.getLogger(__name__)

FANTASY_GOOSE_BASE_URL = "https://www.fantasygoose.com"
ENTRY_CREATE_URL = f"{FANTASY_GOOSE_BASE_URL}/entry/create"
LOGIN_URL = f"{FANTASY_GOOSE_BASE_URL}/login"
MY_PICKS_URL = f"{FANTASY_GOOSE_BASE_URL}/entry/mypicks"
EASTERN_TZ = ZoneInfo("America/New_York")
FANTASY_GOOSE_VERIFICATION_RETRIES = 3
FANTASY_GOOSE_VERIFICATION_DELAY_MS = 2000
DEFAULT_ALIAS_MAP: dict[str, str] = {}


@dataclass(frozen=True)
class FantasyGooseSong:
    """One Fantasy Goose song option."""

    id: str
    name: str


@dataclass(frozen=True)
class FantasyGooseShow:
    """One show option exposed by Fantasy Goose."""

    show_id: str
    label: str
    show_date: date
    cutoff_at: datetime | None = None


@dataclass(frozen=True)
class SongMatch:
    """A resolved JamBandNerd prediction mapped to a Fantasy Goose song."""

    rank: int
    prediction_name: str
    fantasy_goose_song_id: str
    fantasy_goose_song_name: str


@dataclass
class FantasyGooseRunResult:
    """Machine-readable run result for workflow logging and summaries."""

    status: str
    message: str
    target_show: FantasyGooseShow | None = None
    picks: list[SongMatch] = field(default_factory=list)
    missing_predictions: list[str] = field(default_factory=list)

    def as_outputs(self) -> dict[str, str]:
        return {
            "status": self.status,
            "message": self.message,
            "target_show_date": (
                self.target_show.show_date.isoformat() if self.target_show else ""
            ),
            "target_show_label": self.target_show.label if self.target_show else "",
            "picks_json": json.dumps(
                [
                    {
                        "rank": item.rank,
                        "prediction_name": item.prediction_name,
                        "fantasy_goose_song_id": item.fantasy_goose_song_id,
                        "fantasy_goose_song_name": item.fantasy_goose_song_name,
                    }
                    for item in self.picks
                ]
            ),
            "missing_predictions_json": json.dumps(self.missing_predictions),
        }


def normalize_song_name(name: str) -> str:
    """Normalize song names for stable cross-system matching."""
    normalized = name.strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_text(value: str) -> str:
    """Normalize arbitrary page text for loose duplicate-entry checks."""
    return re.sub(r"\s+", " ", value).strip().lower()


def parse_fantasy_goose_show(payload: Mapping[str, Any]) -> FantasyGooseShow:
    """Parse one raw show payload from the entry page into a typed show."""
    label = str(payload.get("label") or payload.get("text") or "").strip()
    show_id = str(payload.get("show_id") or payload.get("value") or "").strip()
    if not label or not show_id:
        raise ValueError("Fantasy Goose show payload missing label or show_id")

    date_prefix = label.split(" - ", 1)[0]
    show_date = datetime.strptime(date_prefix, "%m/%d/%Y").date()

    cutoff_raw = payload.get("cutoff_at") or payload.get("cutoff")
    cutoff_at: datetime | None = None
    if cutoff_raw:
        parsed_cutoff = datetime.strptime(str(cutoff_raw), "%Y-%m-%d %H:%M:%S")
        cutoff_at = parsed_cutoff.replace(tzinfo=EASTERN_TZ)

    return FantasyGooseShow(
        show_id=show_id,
        label=label,
        show_date=show_date,
        cutoff_at=cutoff_at,
    )


def select_target_show(
    shows: Sequence[FantasyGooseShow],
    *,
    target_date: date,
    now_et: datetime,
) -> FantasyGooseRunResult:
    """Pick the eligible show for a target date or return a no-op result."""
    same_day = [show for show in shows if show.show_date == target_date]
    if not same_day:
        return FantasyGooseRunResult(
            status="no_show_tonight",
            message=f"No Fantasy Goose show found for {target_date.isoformat()}.",
        )

    open_shows = [
        show for show in same_day if show.cutoff_at is None or show.cutoff_at > now_et
    ]
    if not open_shows:
        latest = min(
            same_day,
            key=lambda show: show.cutoff_at or datetime.max.replace(tzinfo=EASTERN_TZ),
        )
        return FantasyGooseRunResult(
            status="cutoff_passed",
            message=f"Fantasy Goose cutoff already passed for {latest.label}.",
            target_show=latest,
        )

    target_show = min(
        open_shows,
        key=lambda show: show.cutoff_at or datetime.max.replace(tzinfo=EASTERN_TZ),
    )
    return FantasyGooseRunResult(
        status="ready",
        message=f"Ready to play Fantasy Goose for {target_show.label}.",
        target_show=target_show,
    )


def build_song_index(
    songs: Sequence[FantasyGooseSong],
    alias_map: Mapping[str, str] | None = None,
) -> dict[str, FantasyGooseSong]:
    """Build a unique normalized song index, excluding ambiguous duplicates."""
    alias_map = alias_map or DEFAULT_ALIAS_MAP
    buckets: dict[str, list[FantasyGooseSong]] = {}

    for song in songs:
        buckets.setdefault(normalize_song_name(song.name), []).append(song)

    index: dict[str, FantasyGooseSong] = {}
    for key, matches in buckets.items():
        if len(matches) == 1:
            index[key] = matches[0]

    for source_name, target_name in alias_map.items():
        target_key = normalize_song_name(target_name)
        if target_key in index:
            index[normalize_song_name(source_name)] = index[target_key]

    return index


def match_predictions_to_fg_songs(
    predictions: Sequence[Mapping[str, Any]],
    fg_songs: Sequence[FantasyGooseSong],
    *,
    alias_map: Mapping[str, str] | None = None,
    limit: int = 8,
) -> tuple[list[SongMatch], list[str]]:
    """Map top-ranked JamBandNerd predictions onto Fantasy Goose song ids."""
    alias_map = alias_map or DEFAULT_ALIAS_MAP
    song_index = build_song_index(fg_songs, alias_map=alias_map)
    matches: list[SongMatch] = []
    missing: list[str] = []

    for row in list(predictions)[:limit]:
        prediction_name = str(row.get("song_name") or "").strip()
        rank = int(row.get("rank") or len(matches) + 1)
        normalized = normalize_song_name(prediction_name)
        normalized = normalize_song_name(alias_map.get(normalized, normalized))
        song = song_index.get(normalized)
        if not song:
            missing.append(prediction_name)
            continue
        matches.append(
            SongMatch(
                rank=rank,
                prediction_name=prediction_name,
                fantasy_goose_song_id=song.id,
                fantasy_goose_song_name=song.name,
            )
        )

    return matches, missing


def has_existing_entry(mypicks_text: str, show: FantasyGooseShow) -> bool:
    """Best-effort duplicate-entry check against the user's My Picks page."""
    haystack = normalize_text(mypicks_text)
    label_match = normalize_text(show.label) in haystack
    date_match = normalize_text(show.label.split(" - ", 1)[0]) in haystack
    venue_match = False
    if " - " in show.label:
        venue_match = normalize_text(show.label.split(" - ", 1)[1]) in haystack
    return label_match or (date_match and venue_match)


def fetch_goose_notebook_predictions(
    *,
    reference_date: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Fetch Goose notebook predictions for an exact show date."""
    return fetch_prediction_songs_for_date(
        band="goose",
        model_slug="notebook",
        reference_date=reference_date,
        limit=limit,
    )


def append_github_output(result: FantasyGooseRunResult) -> None:
    """Write stable outputs when running inside GitHub Actions."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        return

    output_path = Path(github_output)
    with output_path.open("a", encoding="utf-8") as handle:
        for key, value in result.as_outputs().items():
            safe_value = str(value).replace("\n", " ").strip()
            handle.write(f"{key}={safe_value}\n")


def format_console_summary(result: FantasyGooseRunResult) -> str:
    """Return a compact human-readable summary for logs and workflow summaries."""
    lines = [f"Fantasy Goose status: {result.status}", result.message]
    if result.target_show:
        lines.append(f"Target show: {result.target_show.label}")
    if result.picks:
        lines.append("Picks:")
        lines.extend(
            f"  {item.rank}. {item.prediction_name} -> {item.fantasy_goose_song_name}"
            for item in result.picks
        )
    if result.missing_predictions:
        lines.append("Missing song mappings: " + ", ".join(result.missing_predictions))
    return "\n".join(lines)


async def login_to_fantasy_goose(page: Page, *, email: str, password: str) -> None:
    """Authenticate a browser page into Fantasy Goose."""
    await page.goto(ENTRY_CREATE_URL, wait_until="domcontentloaded")
    if "/login" not in page.url:
        return

    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await page.get_by_role("textbox", name="Email").fill(email)
    await page.get_by_role("textbox", name="Password").fill(password)
    await page.get_by_role("button", name="Log in").click()
    await page.wait_for_load_state("networkidle")
    if "/login" in page.url:
        raise RuntimeError("Fantasy Goose login did not complete successfully.")


async def fetch_entry_context(
    page: Page,
) -> tuple[list[FantasyGooseShow], list[FantasyGooseSong]]:
    """Read show options and song catalog from the authenticated entry page."""
    await page.goto(ENTRY_CREATE_URL, wait_until="networkidle")
    if "/login" in page.url:
        raise RuntimeError("Fantasy Goose session lost before reading entry page.")

    raw_context = await page.evaluate("""
        () => {
          const select = document.getElementById('show_id');
          const root = document.querySelector('[x-data^="entryForm("]');
          const alpineData = window.Alpine && root ? Alpine.$data(root) : null;
          return {
            shows: select
              ? Array.from(select.options)
                  .filter((option) => option.value)
                  .map((option) => ({
                    value: option.value,
                    label: option.text,
                    cutoff: option.getAttribute('data-cutoff'),
                  }))
              : [],
            songs: alpineData
              ? alpineData.songs.map((song) => ({
                  id: String(song.id),
                  name: String(song.name),
                }))
              : [],
          };
        }
        """)

    shows = [parse_fantasy_goose_show(item) for item in raw_context.get("shows", [])]
    songs = [
        FantasyGooseSong(id=str(item["id"]), name=str(item["name"]))
        for item in raw_context.get("songs", [])
    ]
    return shows, songs


async def fetch_my_picks_text(page: Page) -> str:
    """Fetch the user's My Picks page as plain text."""
    try:
        await page.goto(MY_PICKS_URL, wait_until="domcontentloaded")
    except Exception:
        await page.wait_for_timeout(1000)
        await page.goto(MY_PICKS_URL, wait_until="domcontentloaded")
    return await page.locator("body").inner_text()


def has_entry_for_date(mypicks_text: str, target_date: date) -> bool:
    """Return true when My Picks already contains an entry for the target date."""
    return target_date.strftime("%m/%d/%Y") in mypicks_text


async def submit_entry(
    page: Page,
    *,
    show: FantasyGooseShow,
    picks: Sequence[SongMatch],
) -> None:
    """Populate and submit the Fantasy Goose entry form."""
    song_ids = [pick.fantasy_goose_song_id for pick in picks]
    await page.goto(ENTRY_CREATE_URL, wait_until="networkidle")
    await page.evaluate(
        """
        ({ showId, songIds }) => {
          const form = Array.from(document.forms).find((candidate) =>
            candidate.action.includes('/entry/store')
          );
          if (!form) {
            throw new Error('Fantasy Goose entry form not found.');
          }

          const showSelect = form.querySelector('select[name="show_id"]');
          if (!showSelect) {
            throw new Error('Fantasy Goose show selector not found.');
          }

          showSelect.value = String(showId);
          showSelect.dispatchEvent(new Event('change', { bubbles: true }));

          await new Promise(resolve => setTimeout(resolve, 500));

          songIds.forEach((songId, index) => {
            const hidden = form.querySelector(`input[name="song[${index}]"]`);
            if (!hidden) {
              throw new Error(`Missing hidden song input at index ${index}.`);
            }
            hidden.value = String(songId);
          });

          form.requestSubmit();
        }
        """,
        {"showId": show.show_id, "songIds": song_ids},
    )
    await page.wait_for_load_state("networkidle")


async def run_fantasy_goose(
    *,
    target_date: date | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
    email: str | None = None,
    password: str | None = None,
) -> FantasyGooseRunResult:
    """Run the end-to-end Fantasy Goose automation flow."""
    load_dotenv()
    email = email or os.getenv("FG_USER_EMAIL")
    password = password or os.getenv("FG_PASSWORD")
    if not email or not password:
        raise RuntimeError("FG_USER_EMAIL and FG_PASSWORD must be configured.")

    now_et = now.astimezone(EASTERN_TZ) if now else datetime.now(EASTERN_TZ)
    target_date = target_date or now_et.date()

    async with async_playwright() as playwright:
        browser: Browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await login_to_fantasy_goose(page, email=email, password=password)
            mypicks_text = await fetch_my_picks_text(page)
            shows, songs = await fetch_entry_context(page)

            selection_result = select_target_show(
                shows, target_date=target_date, now_et=now_et
            )
            if selection_result.status != "ready":
                if selection_result.status == "no_show_tonight" and has_entry_for_date(
                    mypicks_text, target_date
                ):
                    return FantasyGooseRunResult(
                        status="already_submitted",
                        message=(
                            "Fantasy Goose already has a saved entry for "
                            f"{target_date.isoformat()}."
                        ),
                    )
                return selection_result

            assert selection_result.target_show is not None
            target_show = selection_result.target_show

            if has_existing_entry(mypicks_text, target_show):
                return FantasyGooseRunResult(
                    status="already_submitted",
                    message=f"Existing Fantasy Goose pick found for {target_show.label}.",
                    target_show=target_show,
                )

            predictions = fetch_goose_notebook_predictions(
                reference_date=target_show.show_date.isoformat(),
                limit=8,
            )
            if len(predictions) < 8:
                return FantasyGooseRunResult(
                    status="missing_predictions",
                    message=(
                        "JamBandNerd does not have a complete Goose notebook top-8 "
                        f"for {target_show.show_date.isoformat()}."
                    ),
                    target_show=target_show,
                )

            picks, missing = match_predictions_to_fg_songs(predictions, songs, limit=8)
            if missing or len(picks) < 8:
                return FantasyGooseRunResult(
                    status="mapping_failed",
                    message=(
                        "Could not map every JamBandNerd prediction onto a Fantasy Goose song."
                    ),
                    target_show=target_show,
                    picks=picks,
                    missing_predictions=missing,
                )

            if dry_run:
                return FantasyGooseRunResult(
                    status="dry_run",
                    message=f"Dry run prepared Fantasy Goose entry for {target_show.label}.",
                    target_show=target_show,
                    picks=picks,
                )

            await submit_entry(page, show=target_show, picks=picks)
            submit_url = page.url
            submit_body = await page.locator("body").inner_text()

            found = False
            for _attempt in range(FANTASY_GOOSE_VERIFICATION_RETRIES):
                await page.wait_for_timeout(FANTASY_GOOSE_VERIFICATION_DELAY_MS)
                mypicks_text = await fetch_my_picks_text(page)
                if has_existing_entry(mypicks_text, target_show):
                    found = True
                    break

            if not found:
                logger.warning("Post-submit URL: %s", submit_url)
                logger.warning("Post-submit body (first 500 chars): %s", submit_body[:500])
                logger.warning("My Picks body (first 500 chars): %s", mypicks_text[:500])
                raise RuntimeError(
                    f"Fantasy Goose submission did not appear in My Picks "
                    f"after {FANTASY_GOOSE_VERIFICATION_RETRIES} attempts "
                    f"for {target_show.label}."
                )

            return FantasyGooseRunResult(
                status="submitted",
                message=f"Submitted Fantasy Goose entry for {target_show.label}.",
                target_show=target_show,
                picks=picks,
            )
        finally:
            await browser.close()


def run_fantasy_goose_sync(
    *,
    target_date: date | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
    email: str | None = None,
    password: str | None = None,
) -> FantasyGooseRunResult:
    """Synchronous wrapper for CLI and workflow entrypoints."""
    return asyncio.run(
        run_fantasy_goose(
            target_date=target_date,
            dry_run=dry_run,
            now=now,
            email=email,
            password=password,
        )
    )
