export type SongBoardTier = "expected" | "hot" | "likely" | "possible";

export const SONG_BOARD_TIER_ORDER: SongBoardTier[] = [
  "expected",
  "hot",
  "likely",
  "possible",
];

export function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
}

export function computeTopKHits(
  rows: Array<{ songName: string }>,
  actualSongs: Set<string>,
  k: number,
) {
  return rows
    .slice(0, k)
    .filter((row) => actualSongs.has(normalizeSongName(row.songName))).length;
}

export function computeTopKRecall(
  rows: Array<{ songName: string }>,
  actualSongs: Set<string>,
  k: number,
) {
  if (actualSongs.size === 0) {
    return null;
  }

  return computeTopKHits(rows, actualSongs, k) / actualSongs.size;
}

export function groupPredictionRowsByTier<T extends { tier: SongBoardTier }>(
  rows: T[],
) {
  const grouped = Object.fromEntries(
    SONG_BOARD_TIER_ORDER.map((tier) => [tier, [] as T[]]),
  ) as Record<SongBoardTier, T[]>;

  for (const row of rows) {
    grouped[row.tier].push(row);
  }

  return grouped;
}
