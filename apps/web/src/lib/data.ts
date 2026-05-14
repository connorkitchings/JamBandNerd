// --- Types ---
export type {
  AccuracyRow,
  BandEntry,
  PredictionRow,
  PredictionSnapshot,
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
  getLatestPredictions,
  getPredictionDates,
  getPredictionsForDate,
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
