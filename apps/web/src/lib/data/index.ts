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
} from "./types";

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
} from "./parsers";

// --- Bands ---
export {
  bandEntryBySlug,
  getBandContext,
  getBands,
  getClientOrState,
  isValidBandSlug,
  resolveBandSelection,
} from "./bands";

// --- Predictions ---
export {
  getLatestPredictions,
  getPredictionDates,
  getPredictionsForDate,
} from "./predictions";

// --- Accuracy ---
export { getRecentAccuracy } from "./accuracy";

// --- Shows ---
export {
  buildFallbackSetlistFromHistoricalRow,
  getLastShowSetlist,
  getNextShowDetails,
  getSetlistForDate,
  getShowDetailsByDate,
} from "./shows";
