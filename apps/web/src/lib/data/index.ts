// --- Types ---
export type {
  AccuracyRow,
  BandEntry,
  PredictionRow,
  RouteState,
  SetlistSong,
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

// --- Band page resolution ---
export { resolveBandPage } from "./resolve-band-page";

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
