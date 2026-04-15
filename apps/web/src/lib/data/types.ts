/**
 * Shared types for the data layer.
 *
 * All route-facing types are defined here so domain modules and consumer pages
 * import from a single canonical location.
 */

import type { LikelihoodTier, ModelSlug } from "@/lib/config";
import type { ShowDetails } from "@/lib/next-show";

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
  ckplusScore: number | null;
  probability: number | null;
  tier: LikelihoodTier;
};

export type PredictionSnapshot = {
  targetShowDate: string | null;
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
  k10Recall: number | null;
  k25Recall: number | null;
  k50Recall: number | null;
  k10Precision: number | null;
  k25Precision: number | null;
  k50Precision: number | null;
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

export type ExplorerSnapshot = {
  availableDates: string[];
  selectedDate: string | null;
  predictions: PredictionSnapshot | null;
  setlist: SetlistSnapshot | null;
};

export type ReplayShowOption = {
  showDate: string;
  venueName: string | null;
};

export type ReplaySnapshot = {
  availableShows: ReplayShowOption[];
  selectedDate: string | null;
  show: ShowDetails | null;
  setlist: SetlistSnapshot | null;
  modelA: ModelSlug;
  modelB: ModelSlug;
  snapshots: Partial<Record<ModelSlug, PredictionSnapshot | null>>;
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
