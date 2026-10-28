import {
  EXCLUDED_PREDICTION_SHOW_DATES,
  EXCLUDED_PREDICTION_SHOW_IDS,
} from "./config.ts";
import { buildShowDetails } from "./next-show.ts";

export const TONIGHT_STATUS_LABEL = "Tonight!";

/**
 * Daily ingestion runs via `.github/workflows/daily-pipeline.yml` at 19:00 UTC.
 * 19:15 UTC (1155 minutes) allows 15 minutes for collection + freshness checks.
 */
const DAILY_INGESTION_CUTOFF_UTC_MINUTES = 19 * 60 + 15;

export type PredictionDisplayState = "previous" | "tonight" | "next";

export type MissingSetlistShow = {
  showId: string;
  showDate: string;
  venueName: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
};

export function getEasternTodayIso(now: Date = new Date()) {
  return now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

export function getEasternDateOffsetIso(
  daysOffset: number,
  now: Date = new Date(),
): string {
  const todayIso = getEasternTodayIso(now);
  const utcDate = new Date(`${todayIso}T00:00:00Z`);
  utcDate.setUTCDate(utcDate.getUTCDate() + daysOffset);
  return utcDate.toISOString().slice(0, 10);
}

export function hasDailyIngestionWindowPassed(
  showDate: string | null,
  now: Date = new Date(),
  latestPredictionTargetDate: string | null = null,
): boolean {
  if (!showDate) {
    return false;
  }

  const todayIso = getEasternTodayIso(now);
  if (showDate >= todayIso) {
    return false;
  }

  const yesterdayIso = getEasternDateOffsetIso(-1, now);
  if (showDate < yesterdayIso) {
    return true;
  }

  if (
    latestPredictionTargetDate &&
    latestPredictionTargetDate < yesterdayIso
  ) {
    return true;
  }

  const utcMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
  return utcMinutes >= DAILY_INGESTION_CUTOFF_UTC_MINUTES;
}

export function isShowTonight(showDate: string | null, now: Date = new Date()) {
  if (!showDate) {
    return false;
  }

  return showDate === getEasternTodayIso(now);
}

export function getPredictionDisplayState(
  targetShowDate: string | null,
  now: Date = new Date(),
): PredictionDisplayState | null {
  if (!targetShowDate) {
    return null;
  }

  const easternDate = getEasternTodayIso(now);
  if (targetShowDate === easternDate) {
    return "tonight";
  }
  if (targetShowDate < easternDate) {
    return "previous";
  }
  return "next";
}

export function shouldShowAfternoonUpdateScheduled(
  targetShowDate: string | null,
  now: Date = new Date(),
  hasMissingSetlists: boolean = false,
): boolean {
  if (hasMissingSetlists) {
    return false;
  }

  if (getPredictionDisplayState(targetShowDate, now) !== "previous") {
    return false;
  }

  const yesterdayIso = getEasternDateOffsetIso(-1, now);
  if (targetShowDate !== yesterdayIso) {
    return false;
  }

  return !hasDailyIngestionWindowPassed(targetShowDate, now);
}

export function getPredictionStatusLabel(showDate: string | null, now: Date = new Date()) {
  const state = getPredictionDisplayState(showDate, now);
  if (!state) {
    return "Prediction Outlook";
  }

  if (state === "tonight") {
    return TONIGHT_STATUS_LABEL;
  }
  if (state === "previous") {
    return "Previous Show";
  }
  return "Next Show";
}

export function findMissingSetlistShows(
  band: string,
  showRows: ReadonlyArray<Record<string, unknown>>,
  setlistRows: ReadonlyArray<Record<string, unknown>>,
  options?: {
    idColumn?: string;
    now?: Date;
    lookbackDays?: number;
    minUniqueSongs?: number;
    latestPredictionTargetDate?: string | null;
  },
): MissingSetlistShow[] {
  const idColumn = options?.idColumn ?? "show_id";
  const now = options?.now ?? new Date();
  const lookbackDays = options?.lookbackDays ?? 7;
  const minUniqueSongs = options?.minUniqueSongs ?? 3;
  const latestPredictionTargetDate =
    options?.latestPredictionTargetDate ?? null;

  const todayIso = getEasternTodayIso(now);
  const cutoffIso = getEasternDateOffsetIso(-lookbackDays, now);
  const excludedIds = new Set(EXCLUDED_PREDICTION_SHOW_IDS[band] ?? []);
  const excludedDates = new Set(EXCLUDED_PREDICTION_SHOW_DATES[band] ?? []);

  const candidateShows = showRows
    .map((row) => {
      const rawId = row[idColumn] ?? row.show_id;
      const showId =
        rawId !== undefined && rawId !== null ? String(rawId).trim() : "";
      const details = buildShowDetails(row);
      const showDate = details.showDate?.trim() ?? "";
      return {
        showId,
        showDate,
        details,
      };
    })
    .filter(
      (item) =>
        item.showId.length > 0 &&
        item.showDate.length > 0 &&
        item.showDate >= cutoffIso &&
        item.showDate < todayIso &&
        !excludedIds.has(item.showId) &&
        !excludedDates.has(item.showDate),
    );

  if (candidateShows.length === 0) {
    return [];
  }

  const uniqueSongsByShowId = new Map<string, Set<string>>();
  for (const row of setlistRows) {
    const rawId = row[idColumn] ?? row.show_id;
    const rawSong = row.song_name ?? row.song;
    if (rawId === undefined || rawId === null || typeof rawSong !== "string") {
      continue;
    }
    const showId = String(rawId).trim();
    const songName = rawSong.trim();
    if (!showId || !songName) {
      continue;
    }
    let songSet = uniqueSongsByShowId.get(showId);
    if (!songSet) {
      songSet = new Set<string>();
      uniqueSongsByShowId.set(showId, songSet);
    }
    songSet.add(songName);
  }

  const coveredDates = new Set<string>();
  for (const item of candidateShows) {
    const count = uniqueSongsByShowId.get(item.showId)?.size ?? 0;
    if (count >= minUniqueSongs) {
      coveredDates.add(item.showDate);
    }
  }

  const seenDates = new Set<string>();
  const missing: MissingSetlistShow[] = [];
  const sortedCandidates = candidateShows.toSorted((left, right) => {
    const dateCompare = left.showDate.localeCompare(right.showDate);
    if (dateCompare !== 0) {
      return dateCompare;
    }
    return left.showId.localeCompare(right.showId);
  });

  for (const item of sortedCandidates) {
    if (coveredDates.has(item.showDate) || seenDates.has(item.showDate)) {
      continue;
    }
    if (
      !hasDailyIngestionWindowPassed(
        item.showDate,
        now,
        latestPredictionTargetDate,
      )
    ) {
      continue;
    }
    seenDates.add(item.showDate);
    missing.push({
      showId: item.showId,
      showDate: item.showDate,
      venueName: item.details.venueName,
      city: item.details.city,
      state: item.details.state,
      country: item.details.country,
    });
  }

  return missing;
}
