/**
 * Barrel re-export for the data layer.
 *
 * All domain logic has been decomposed into focused modules under `data/`.
 * This file re-exports everything so existing import paths (`@/lib/data`)
 * continue to work without changes.
 *
 * New code should prefer importing from the specific domain module
 * (e.g. `@/lib/data/predictions`) for better tree-shaking.
 */

// --- Types ---
export type {
  AccuracyRow,
  BandEntry,
  ExplorerSnapshot,
  PredictionRow,
  PredictionSnapshot,
  ReplayShowOption,
  ReplaySnapshot,
  RouteState,
  SetlistSong,
  SetlistSnapshot,
  ShowDetails,
} from "./data/types";

// --- Parsers (pure utilities) ---
export {
  asRecord,
  buildPredictionSnapshotFromCanonicalRow,
  buildPredictionSnapshotFromProjectionRows,
  computeTier,
  getVenueCityFromRow,
  getVenueNameFromRow,
  getVenueRegionFromRow,
  normalizePredictionRows,
  normalizeProjectedPredictionRows,
  parseNumber,
  parsePredictions,
  parseStringArray,
} from "./data/parsers";

// --- Bands ---
export {
  bandEntryBySlug,
  getBandContext,
  getBands,
  getClientOrState,
  isValidBandSlug,
  resolveBandSelection,
} from "./data/bands";

// --- Predictions ---
export {
  getCurrentModelVersion,
  getExplorerSnapshot,
  getLatestPredictions,
  getPredictionDates,
  getPredictionsForDate,
  resolveReplayModels,
} from "./data/predictions";

// --- Accuracy ---
export { getRecentAccuracy } from "./data/accuracy";

// --- Shows ---
export {
  buildFallbackSetlistFromHistoricalRow,
  getLastShowSetlist,
  getNextShowDetails,
  getSetlistForDate,
  getShowDetailsByDate,
} from "./data/shows";

// --- Replay ---
export { getReplaySnapshot } from "./data/replay";

// --- Model agreement (pass-through) ---
export type { ModelAgreement, ModelAgreementTier } from "@/lib/model-agreement";
export { calculateModelAgreement } from "@/lib/model-agreement";
