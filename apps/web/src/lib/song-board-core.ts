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
