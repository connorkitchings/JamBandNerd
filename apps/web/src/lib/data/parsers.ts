/**
 * Low-level parsing and normalization utilities for the data layer.
 *
 * These pure functions handle JSON parsing, number coercion, venue field
 * extraction, tier computation, and prediction row normalization. They have
 * no Supabase dependency and can be unit-tested in isolation.
 */

import type { BandSlug, LikelihoodTier } from "@/lib/config";
import type {
  JsonPrediction,
  PredictionRow,
  PredictionSnapshot,
} from "./types";

// ---------------------------------------------------------------------------
// Primitive parsers
// ---------------------------------------------------------------------------

export function buildSetlistSelectColumns(
  band: BandSlug,
  idColumn: string,
  positionColumn: string,
): string {
  const setColumns =
    band === "um" ? "set_label, set_sequence, encore" : "set_number";
  return `${idColumn}, song_name, ${setColumns}, ${positionColumn}`;
}

export function parseSetNumber(row: Record<string, unknown>): number | null {
  if (
    row.encore === true ||
    (typeof row.encore === "string" && row.encore.trim().toLowerCase() === "true")
  ) {
    return 99;
  }

  const rawSetValue =
    row.set_number !== undefined && row.set_number !== null
      ? row.set_number
      : row.set_label !== undefined && row.set_label !== null
        ? row.set_label
        : row.set_sequence;

  if (typeof rawSetValue === "string") {
    const normalized = rawSetValue.trim().toUpperCase();
    if (
      normalized === "E" ||
      normalized === "E1" ||
      normalized === "E2" ||
      normalized === "E3" ||
      normalized === "ENCORE" ||
      normalized === "99"
    ) {
      return 99;
    }
    if (normalized === "ONE SET" || normalized === "SET") {
      return parseNumber(row.set_sequence) ?? 1;
    }
  }

  return parseNumber(rawSetValue) ?? parseNumber(row.set_sequence);
}

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
  if (rank <= 10) return "prime";
  if (rank <= 25) return "likely";
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

// ---------------------------------------------------------------------------
// Snapshot builders
// ---------------------------------------------------------------------------

export function buildPredictionSnapshotFromCanonicalRow(
  row: Record<string, unknown>,
): PredictionSnapshot {
  return {
    targetShowDate:
      typeof row.target_show_date === "string" ? row.target_show_date : null,
    targetShowKey:
      typeof row.target_show_key === "string" ? row.target_show_key : null,
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
