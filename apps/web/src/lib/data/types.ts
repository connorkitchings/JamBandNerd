/**
 * Shared types for the data layer.
 *
 * All route-facing types are defined here so domain modules and consumer pages
 * import from a single canonical location.
 */

import type { LikelihoodTier } from "@/lib/config";

export type { ShowDetails } from "@/lib/next-show";

type JsonPrediction = Record<string, unknown>;
export type ProjectionRow = Record<string, unknown>;

export type PredictionRow = {
  rank: number;
  songName: string;
  lastPlayed: string | null;
  currentGap: number | null;
  recentPlays50: number | null;
  playsPastYear: number | null;
  avgGap: number | null;
  recentAvgGap: number | null;
  gapRatio: number | null;
  gapZScore: number | null;
  probability: number | null;
  tier: LikelihoodTier;
};

export type PredictionSnapshot = {
  targetShowDate: string | null;
  targetShowKey: string | null;
  referenceDate: string | null;
  predictedAt: string | null;
  modelVersion: string | null;
  predictions: PredictionRow[];
  raw: Record<string, unknown>;
};

export type AccuracyRow = {
  showDate: string | null;
  venueName: string | null;
  city: string | null;
  state: string | null;
  recall10: number | null;
  recall25: number | null;
  recall50: number | null;
  p10: number | null;
  p25: number | null;
  p50: number | null;
  weightedPrecisionScore: number | null;
};

export type SetlistSong = {
  setNumber: number | null;
  position: number | null;
  songName: string;
};

export type SetlistSnapshot = {
  showDetails: Record<string, unknown> | null;
  songs: SetlistSong[];
};

export type BandEntry = {
  slug: string;
  displayName: string;
  showsTable: string;
  idColumn: string;
};

export type RouteState<T> =
  | { status: "missing_env" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | ({ status: "ready" } & T);

export type { JsonPrediction };
