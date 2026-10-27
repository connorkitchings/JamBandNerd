/**
 * Pure helpers for choosing which show row to display when a date maps to more
 * than one show (e.g. a short promo set plus the full show on the same night).
 */

import { EXCLUDED_PREDICTION_SHOW_IDS } from "./config.ts";
import type { ShowDetails } from "./next-show.ts";

type Row = Record<string, unknown>;

function rowShowId(row: Row, idColumn: string): string | null {
  const raw = row[idColumn];
  return raw === undefined || raw === null ? null : String(raw);
}

/** Drops shows that are excluded from prediction windows for this band. */
export function filterExcludedShows<T extends Row>(
  band: string,
  rows: T[],
  idColumn: string,
): T[] {
  const excluded = new Set(EXCLUDED_PREDICTION_SHOW_IDS[band] ?? []);
  return rows.filter((row) => {
    const id = rowShowId(row, idColumn);
    return id === null || !excluded.has(id);
  });
}

/** Counts setlist rows per show id. */
export function countRowsByShowId(
  setlistRows: Row[],
  idColumn: string,
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of setlistRows) {
    const id = rowShowId(row, idColumn);
    if (id !== null) {
      counts.set(id, (counts.get(id) ?? 0) + 1);
    }
  }
  return counts;
}

/**
 * Picks the show with the most songs. Ties (including all-zero) keep the
 * earliest row so the result is deterministic.
 */
export function pickShowWithMostSongs<T extends Row>(
  rows: T[],
  idColumn: string,
  songCounts: Map<string, number>,
): T | null {
  let best: T | null = null;
  let bestCount = -1;
  for (const row of rows) {
    const id = rowShowId(row, idColumn);
    const count = id === null ? 0 : (songCounts.get(id) ?? 0);
    if (count > bestCount) {
      best = row;
      bestCount = count;
    }
  }
  return best;
}

/**
 * Show whose details head the home teaser. The teaser lists songs from the
 * latest prediction snapshot, so the header must describe that snapshot's
 * target date, not whatever the next scheduled show happens to be.
 */
export function selectTeaserShow(
  snapshotTargetDate: string,
  nextShow: ShowDetails | null,
  snapshotDateShow: ShowDetails | null,
): ShowDetails | null {
  return nextShow?.showDate === snapshotTargetDate ? nextShow : snapshotDateShow;
}
