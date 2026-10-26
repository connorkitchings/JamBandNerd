// --- Types ---
export type {
  AccuracyRow,
  BandEntry,
  MissingSetlistShow,
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
  buildSetlistSelectColumns,
  computeTier,
  getVenueCityFromRow,
  getVenueNameFromRow,
  getVenueRegionFromRow,
  normalizePredictionRows,
  normalizeProjectedPredictionRows,
  parseNumber,
  parsePredictions,
  parseSetNumber,
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
  getRecentMissingSetlistShows,
  getSetlistForDate,
  getShowDetailsByDate,
} from "./shows";
