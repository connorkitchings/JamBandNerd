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
  buildSetlistSelectColumns,
  computeTier,
  getVenueCityFromRow,
  getVenueNameFromRow,
  getVenueRegionFromRow,
  normalizePredictionRows,
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
  resolveBandSelection,
} from "./bands";

// --- Predictions ---
export {
  getLatestPredictions,
  getPredictionsForDate,
} from "./predictions";

// --- Accuracy ---
export { getRecentAccuracy } from "./accuracy";

// --- Shows ---
export {
  getLastShowSetlist,
  getNextShowDetails,
  getRecentMissingSetlistShows,
  getSetlistForDate,
  getShowDetailsByDate,
} from "./shows";
