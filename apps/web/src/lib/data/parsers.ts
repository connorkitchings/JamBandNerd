/**
 * Low-level parsing and normalization utilities for the data layer.
 *
 * These pure functions handle JSON parsing, number coercion, venue field
 * extraction, tier computation, and prediction row normalization. They have
 * no Supabase dependency and can be unit-tested in isolation.
 */

import type { LikelihoodTier } from "@/lib/config";
import type {
  JsonPrediction,
  PredictionRow,
  PredictionSnapshot,
  ProjectionRow,
} from "./types";

// ---------------------------------------------------------------------------
// Primitive parsers
// ---------------------------------------------------------------------------

export function parsePredictions(value: unknown): JsonPrediction[] {
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? (parsed as JsonPrediction[]) : [];
    } catch {
      return [];
    }
  }

  return Array.isArray(value) ? (value as JsonPrediction[]) : [];
}

export function parseStringArray(value: unknown): string[] {
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed)
        ? parsed.filter((item): item is string => typeof item === "string")
        : [];
    } catch {
      return [];
    }
  }

  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

export function parseNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string" && value.trim()) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  return null;
}

export function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }

  return null;
}

// ---------------------------------------------------------------------------
// Venue field extractors
// ---------------------------------------------------------------------------

export function getVenueNameFromRow(row: Record<string, unknown> | null): string | null {
  if (!row) {
    return null;
  }

  if (typeof row.venue_name === "string") {
    return row.venue_name;
  }

  if (typeof row.venue === "string") {
    return row.venue;
  }

  return null;
}

export function getVenueCityFromRow(row: Record<string, unknown> | null): string | null {
  if (!row) {
    return null;
  }

  if (typeof row.venue_city === "string") {
    return row.venue_city;
  }

  if (typeof row.city === "string") {
    return row.city;
  }

  return null;
}

export function getVenueRegionFromRow(row: Record<string, unknown> | null): string | null {
  if (!row) {
    return null;
  }

  if (typeof row.region === "string") {
    return row.region;
  }

  if (typeof row.venue_state === "string") {
    return row.venue_state;
  }

  if (typeof row.state === "string") {
    return row.state;
  }

  if (typeof row.venue_country === "string") {
    return row.venue_country;
  }

  if (typeof row.country === "string") {
    return row.country;
  }

  return null;
}

// ---------------------------------------------------------------------------
// Tier & prediction normalization
// ---------------------------------------------------------------------------

export function computeTier(rank: number): LikelihoodTier {
  if (rank <= 5) return "expected";
  if (rank <= 15) return "hot";
  if (rank <= 30) return "likely";
  return "possible";
}

export function normalizePredictionRows(rows: JsonPrediction[]): PredictionRow[] {
  return rows.map((row, index) => {
    const rank = index + 1;
    const probability = parseNumber(row.probability);
    return {
      rank,
      songName: String(row.song_name ?? "Unknown Song"),
      lastPlayed:
        typeof row.LTP === "string"
          ? row.LTP
          : typeof row.last_played_date === "string"
            ? row.last_played_date
            : null,
      currentGap: parseNumber(row.current_gap),
      recentPlays50: parseNumber(row.recent_plays_50),
      playsPastYear: parseNumber(row.plays_past_year),
      avgGap: parseNumber(row.avg_gap),
      recentAvgGap: parseNumber(row.recent_avg_gap),
      gapRatio: parseNumber(row.gap_ratio),
      gapZScore: parseNumber(row.gap_z_score),
      probability,
      tier: computeTier(rank),
    };
  });
}

export function normalizeProjectedPredictionRows(rows: ProjectionRow[]): PredictionRow[] {
  return rows.map((row, index) => {
    const payload = asRecord(row.prediction_payload) ?? {};
    const rank = parseNumber(row.rank) ?? parseNumber(payload.rank) ?? index + 1;
    const probability = parseNumber(payload.probability);

    return {
      rank,
      songName:
        typeof row.song_name === "string"
          ? row.song_name
          : String(payload.song_name ?? "Unknown Song"),
      lastPlayed:
        typeof payload.LTP === "string"
          ? payload.LTP
          : typeof payload.last_played_date === "string"
            ? payload.last_played_date
            : null,
      currentGap: parseNumber(payload.current_gap),
      recentPlays50: parseNumber(payload.recent_plays_50),
      playsPastYear: parseNumber(payload.plays_past_year),
      avgGap: parseNumber(payload.avg_gap),
      recentAvgGap: parseNumber(payload.recent_avg_gap),
      gapRatio: parseNumber(payload.gap_ratio),
      gapZScore: parseNumber(payload.gap_z_score),
      probability,
      tier: computeTier(rank),
    };
  });
}

// ---------------------------------------------------------------------------
// Snapshot builders
// ---------------------------------------------------------------------------

export function buildPredictionSnapshotFromCanonicalRow(
  row: Record<string, unknown>,
): PredictionSnapshot {
  return {
    targetShowDate:
      typeof row.target_show_date === "string" ? row.target_show_date : null,
    referenceDate:
      typeof row.reference_date === "string" ? row.reference_date : null,
    predictedAt:
      typeof row.predicted_at === "string"
        ? row.predicted_at
        : typeof row.generated_at === "string"
          ? row.generated_at
        : typeof row.created_at === "string"
          ? row.created_at
          : null,
    modelVersion: typeof row.model_version === "string" ? row.model_version : null,
    predictions: normalizePredictionRows(parsePredictions(row.predictions)),
    raw: row,
  };
}

export function buildPredictionSnapshotFromProjectionRows(rows: ProjectionRow[]): PredictionSnapshot {
  const firstRow = rows[0] ?? null;

  return {
    targetShowDate: null,
    referenceDate:
      firstRow && typeof firstRow.reference_date === "string"
        ? firstRow.reference_date
        : null,
    predictedAt:
      firstRow && typeof firstRow.predicted_at === "string"
        ? firstRow.predicted_at
        : null,
    modelVersion:
      firstRow && typeof firstRow.model_version === "string"
        ? firstRow.model_version
        : null,
    predictions: normalizeProjectedPredictionRows(rows),
    raw: {
      source: "prediction_songs",
      rowCount: rows.length,
      referenceDate:
        firstRow && typeof firstRow.reference_date === "string"
          ? firstRow.reference_date
          : null,
      predictedAt:
        firstRow && typeof firstRow.predicted_at === "string"
          ? firstRow.predicted_at
          : null,
      modelVersion:
        firstRow && typeof firstRow.model_version === "string"
          ? firstRow.model_version
          : null,
    },
  };
}
