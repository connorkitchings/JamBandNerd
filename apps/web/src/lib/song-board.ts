import { TIER_ORDER, type LikelihoodTier } from "@/lib/config";
import type { PredictionRow } from "@/lib/data";

export function formatProbabilityLabel(probability: number | null): string {
  return probability !== null ? `${(probability * 100).toFixed(1)}%` : "Unknown";
}

export function formatGapLabel(currentGap: number | null): string {
  if (currentGap === null) return "Gap unknown";
  return `${currentGap} ${currentGap === 1 ? "show" : "shows"}`;
}

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
