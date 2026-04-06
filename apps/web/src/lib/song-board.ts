import { TIER_ORDER, type LikelihoodTier } from "@/lib/config";
import type { PredictionRow } from "@/lib/data";

export function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
}

export function groupPredictionRowsByTier(rows: PredictionRow[]) {
  const grouped = Object.fromEntries(
    TIER_ORDER.map((tier) => [tier, [] as PredictionRow[]]),
  ) as Record<LikelihoodTier, PredictionRow[]>;

  for (const row of rows) {
    grouped[row.tier].push(row);
  }

  return grouped;
}
