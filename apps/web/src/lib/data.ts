import "server-only";

import { cache } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";

import {
  ACTIVE_MODELS,
  DEFAULT_BAND_SLUG,
  type BandSlug,
  type LikelihoodTier,
  type ModelSlug,
  normalizeBand,
  normalizeModel,
} from "@/lib/config";
import { getSupabaseServerClient, hasSupabaseEnv } from "@/lib/supabase/server";
import {
  buildShowDetails,
  selectUmUpcomingShowRow,
  type ShowDetails,
} from "@/lib/next-show";
import { selectLivePredictionSeedRow } from "@/lib/prediction-selection";
export type { ModelAgreement, ModelAgreementTier } from "@/lib/model-agreement";
export { calculateModelAgreement } from "@/lib/model-agreement";
export type { ShowDetails } from "@/lib/next-show";

type JsonPrediction = Record<string, unknown>;
type ProjectionRow = Record<string, unknown>;

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

function parsePredictions(value: unknown): JsonPrediction[] {
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

function parseStringArray(value: unknown): string[] {
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

function parseNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string" && value.trim()) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }

  return null;
}

function getVenueNameFromRow(row: Record<string, unknown> | null): string | null {
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

function getVenueCityFromRow(row: Record<string, unknown> | null): string | null {
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

function getVenueRegionFromRow(row: Record<string, unknown> | null): string | null {
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

const SUPABASE_PAGE_SIZE = 1000;
const SHOW_ID_CHUNK_SIZE = 100;
type SupabaseSelectQuery = ReturnType<ReturnType<SupabaseClient["from"]>["select"]>;

async function fetchAllRecords(
  client: SupabaseClient,
  tableName: string,
  selectClause: string,
  configureQuery: (query: SupabaseSelectQuery) => SupabaseSelectQuery,
): Promise<Record<string, unknown>[]> {
  const rows: Record<string, unknown>[] = [];

  for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
    const { data, error } = await configureQuery(
      client.from(tableName).select(selectClause),
    ).range(offset, offset + SUPABASE_PAGE_SIZE - 1);

    if (error) {
      throw error;
    }

    const pageRows =
      (data ?? [])
        .map((row: unknown) => asRecord(row))
        .filter((row): row is Record<string, unknown> => row !== null);
    rows.push(...pageRows);

    if (pageRows.length < SUPABASE_PAGE_SIZE) {
      break;
    }
  }

  return rows;
}

function computeTier(rank: number): LikelihoodTier {
  if (rank <= 5) return "expected";
  if (rank <= 15) return "hot";
  if (rank <= 30) return "likely";
  return "possible";
}

function normalizePredictionRows(rows: JsonPrediction[]): PredictionRow[] {
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
      ckplusScore: parseNumber(row.ckplus_score),
      probability,
      tier: computeTier(rank),
    };
  });
}

function normalizeProjectedPredictionRows(rows: ProjectionRow[]): PredictionRow[] {
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
      ckplusScore: parseNumber(payload.ckplus_score),
      probability,
      tier: computeTier(rank),
    };
  });
}

function buildPredictionSnapshotFromCanonicalRow(
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

function buildPredictionSnapshotFromProjectionRows(rows: ProjectionRow[]): PredictionSnapshot {
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

async function fetchProjectedPredictionSnapshot(
  client: SupabaseClient,
  {
    band,
    model,
    referenceDate,
  }: {
    band: BandSlug;
    model: ModelSlug;
    referenceDate?: string;
  },
): Promise<PredictionSnapshot | null> {
  let seedQuery = client
    .from("prediction_songs")
    .select("reference_date, predicted_at, model_version")
    .eq("band", band)
    .eq("model_slug", model);

  const todayIso = new Date().toISOString().slice(0, 10);

  if (referenceDate) {
    seedQuery = seedQuery.eq("reference_date", referenceDate);
  }

  const { data: seedRows, error: seedError } = await seedQuery
    .order("predicted_at", { ascending: false })
    .order("reference_date", { ascending: false })
    .order("rank", { ascending: true })
    .limit(referenceDate ? 1 : 100);

  if (seedError) {
    throw seedError;
  }

  const seedRow = referenceDate
    ? asRecord(seedRows?.[0])
    : selectLivePredictionSeedRow(
        (seedRows ?? [])
          .map((item) => asRecord(item))
          .filter((item): item is Record<string, unknown> => item !== null)
          .map((row) => ({
            reference_date:
              typeof row.reference_date === "string" ? row.reference_date : null,
            predicted_at:
              typeof row.predicted_at === "string" ? row.predicted_at : null,
            model_version:
              typeof row.model_version === "string" ? row.model_version : null,
          })),
        { todayIso },
      );
  const seedReferenceDate =
    seedRow && typeof seedRow.reference_date === "string"
      ? seedRow.reference_date
      : null;
  const seedModelVersion =
    seedRow && typeof seedRow.model_version === "string"
      ? seedRow.model_version
      : null;

  if (!seedReferenceDate || !seedModelVersion) {
    return null;
  }

  const { data, error } = await client
    .from("prediction_songs")
    .select(
      "reference_date, predicted_at, model_version, rank, song_name, prediction_payload",
    )
    .eq("band", band)
    .eq("model_slug", model)
    .eq("reference_date", seedReferenceDate)
    .eq("model_version", seedModelVersion)
    .order("rank", { ascending: true });

  if (error) {
    throw error;
  }

  const rows = (data ?? [])
    .map((item) => asRecord(item))
    .filter((item): item is ProjectionRow => item !== null);

  if (rows.length === 0) {
    return null;
  }

  return buildPredictionSnapshotFromProjectionRows(rows);
}

async function getCurrentModelVersion(
  client: SupabaseClient,
  band: BandSlug,
  model: ModelSlug,
): Promise<string> {
  try {
    const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
      band,
      model,
    });
    if (projectionSnapshot?.modelVersion) {
      return projectionSnapshot.modelVersion;
    }
  } catch (error) {
    console.error("Failed to resolve model version from prediction_songs", error);
  }

  const { data } = await client
    .from(`predictions_${model}`)
    .select("model_version")
    .eq("band", band)
    .order("predicted_at", { ascending: false })
    .order("reference_date", { ascending: false })
    .limit(1);

  const row = asRecord(data?.[0]);
  if (row && typeof row.model_version === "string") {
    return row.model_version;
  }

  return `${model}_v1`;
}

function getClientOrState<T>(): RouteState<T> | null {
  if (!hasSupabaseEnv()) {
    return { status: "missing_env" };
  }

  return null;
}

function resolveReplayModels(
  modelAInput: string | undefined,
  modelBInput: string | undefined,
): [ModelSlug, ModelSlug] {
  const modelA = ACTIVE_MODELS.includes(modelAInput as ModelSlug)
    ? (modelAInput as ModelSlug)
    : (ACTIVE_MODELS[0] ?? "notebook");
  const fallbackModelB =
    ACTIVE_MODELS.find((item) => item !== modelA) ?? ACTIVE_MODELS[0] ?? modelA;
  const requestedModelB = ACTIVE_MODELS.includes(modelBInput as ModelSlug)
    ? (modelBInput as ModelSlug)
    : fallbackModelB;
  const modelB =
    requestedModelB === modelA && ACTIVE_MODELS.length > 1
      ? fallbackModelB
      : requestedModelB;
  return [modelA, modelB];
}

type BandSelection = {
  requestedSlug: string;
  bandEntry: BandEntry | null;
  isInvalid: boolean;
};

export function resolveBandSelection(
  bands: BandEntry[],
  bandInput: string | undefined,
): BandSelection {
  const requestedSlug = normalizeBand(bandInput);
  const matchedBand = bandEntryBySlug(bands, requestedSlug) ?? null;

  if (matchedBand) {
    return {
      requestedSlug,
      bandEntry: matchedBand,
      isInvalid: false,
    };
  }

  if (typeof bandInput === "string" && bandInput.trim().length > 0) {
    return {
      requestedSlug,
      bandEntry: null,
      isInvalid: true,
    };
  }

  return {
    requestedSlug,
    bandEntry: bandEntryBySlug(bands, DEFAULT_BAND_SLUG) ?? bands[0] ?? null,
    isInvalid: false,
  };
}

async function getBandContext(
  bandInput: string | undefined,
): Promise<RouteState<{ band: BandSlug; bandEntry: BandEntry }>> {
  const bandsState = await getBands();
  if (bandsState.status !== "ready") {
    return bandsState as RouteState<{ band: BandSlug; bandEntry: BandEntry }>;
  }

  const selection = resolveBandSelection(bandsState.bands, bandInput);
  if (!selection.bandEntry || selection.isInvalid) {
    return { status: "empty" };
  }

  return {
    status: "ready",
    band: selection.bandEntry.slug,
    bandEntry: selection.bandEntry,
  };
}

export const getLatestPredictions = cache(
  async (
    bandInput: string | undefined,
    modelInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; snapshot: PredictionSnapshot }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      snapshot: PredictionSnapshot;
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        snapshot: PredictionSnapshot;
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      try {
        const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
          band,
          model,
        });
        if (projectionSnapshot) {
          return { status: "ready", band, model, snapshot: projectionSnapshot };
        }
      } catch (error) {
        console.error("Failed to load latest projected predictions", error);
      }

      const { data, error } = await client
        .from(`predictions_${model}`)
        .select("*")
        .eq("band", band)
        .order("reference_date", { ascending: false })
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = data?.[0];
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        model,
        snapshot: buildPredictionSnapshotFromCanonicalRow(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getPredictionsForDate = cache(
  async (
    bandInput: string | undefined,
    modelInput: string | undefined,
    referenceDate: string,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; snapshot: PredictionSnapshot }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      snapshot: PredictionSnapshot;
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        snapshot: PredictionSnapshot;
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      try {
        const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
          band,
          model,
          referenceDate,
        });
        if (projectionSnapshot) {
          return { status: "ready", band, model, snapshot: projectionSnapshot };
        }
      } catch (error) {
        console.error("Failed to load projected predictions for date", error);
      }

      const { data, error } = await client
        .from(`predictions_${model}`)
        .select("*")
        .eq("band", band)
        .eq("reference_date", referenceDate)
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = data?.[0];
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        model,
        snapshot: buildPredictionSnapshotFromCanonicalRow(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getPredictionDates = cache(
  async (
    bandInput: string | undefined,
    modelInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; dates: string[] }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      dates: string[];
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        dates: string[];
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      let dates: string[] = [];

      try {
        const { data: projectionData, error: projectionError } = await client
          .from("prediction_songs")
          .select("reference_date")
          .eq("band", band)
          .eq("model_slug", model)
          .order("reference_date", { ascending: false })
          .limit(100);

        if (!projectionError && projectionData && projectionData.length > 0) {
          dates = [...new Set(
            projectionData
              .map((row) => asRecord(row)?.reference_date)
              .filter((d): d is string => typeof d === "string")
          )];
        }
      } catch {
      }

      if (dates.length === 0) {
        const { data, error } = await client
          .from(`predictions_${model}`)
          .select("reference_date")
          .eq("band", band)
          .order("reference_date", { ascending: false })
          .limit(100);

        if (error) {
          return { status: "error", message: error.message };
        }

        dates = [...new Set(
          (data ?? [])
            .map((row) => asRecord(row)?.reference_date)
            .filter((d): d is string => typeof d === "string")
        )];
      }

      return dates.length === 0
        ? { status: "empty" }
        : { status: "ready", band, model, dates };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getRecentAccuracy = cache(
  async (
    bandInput: string | undefined,
    modelInput: string | undefined,
    limit = 25,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; rows: AccuracyRow[] }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      rows: AccuracyRow[];
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        rows: AccuracyRow[];
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const modelVersion = await getCurrentModelVersion(client, band, model);
      const { data, error } = await client
        .from("accuracy_per_show")
        .select("show_id, show_date, k10_recall, k25_recall, k50_recall, k10_precision, k25_precision, k50_precision")
        .eq("band", band)
        .eq("model_version", modelVersion)
        .order("show_date", { ascending: false })
        .limit(limit);

      if (error) {
        return { status: "error", message: error.message };
      }

      const accuracyRows =
        data?.map((row) => ({
          showId:
            typeof row.show_id === "string" || typeof row.show_id === "number"
              ? String(row.show_id)
              : null,
          showDate: typeof row.show_date === "string" ? row.show_date : null,
          k10Recall: parseNumber(row.k10_recall),
          k25Recall: parseNumber(row.k25_recall),
          k50Recall: parseNumber(row.k50_recall),
          k10Precision: parseNumber(row.k10_precision),
          k25Precision: parseNumber(row.k25_precision),
          k50Precision: parseNumber(row.k50_precision),
        })) ?? [];

      if (accuracyRows.length === 0) {
        return { status: "empty" };
      }

      const { idColumn, showsTable } = bandState.bandEntry;
      const showIds = [...new Set(accuracyRows.map((row) => row.showId).filter(Boolean))];
      const showDates = [...new Set(accuracyRows.map((row) => row.showDate).filter(Boolean))];
      const showMetaByShowId = new Map<
        string,
        { venueName: string | null; city: string | null; state: string | null }
      >();
      const showMetaByShowDate = new Map<
        string,
        { venueName: string | null; city: string | null; state: string | null }
      >();

      if (showIds.length > 0) {
        const { data: showData, error: showError } = await client
          .from(showsTable)
          .select("*")
          .in(idColumn, showIds);

        if (showError) {
          return { status: "error", message: showError.message };
        }

        for (const item of showData ?? []) {
          const row = asRecord(item);
          if (!row) {
            continue;
          }

          const showMeta = {
            venueName: getVenueNameFromRow(row),
            city: getVenueCityFromRow(row),
            state: getVenueRegionFromRow(row),
          };
          const showIdValue = row[idColumn];
          if (typeof showIdValue === "string" || typeof showIdValue === "number") {
            showMetaByShowId.set(String(showIdValue), showMeta);
          }

          if (typeof row.show_date === "string") {
            showMetaByShowDate.set(row.show_date, showMeta);
          }
        }
      } else if (showDates.length > 0) {
        const { data: showData, error: showError } = await client
          .from(showsTable)
          .select("*")
          .in("show_date", showDates);

        if (showError) {
          return { status: "error", message: showError.message };
        }

        for (const item of showData ?? []) {
          const row = asRecord(item);
          if (!row || typeof row.show_date !== "string") {
            continue;
          }

          showMetaByShowDate.set(row.show_date, {
            venueName: getVenueNameFromRow(row),
            city: getVenueCityFromRow(row),
            state: getVenueRegionFromRow(row),
          });
        }
      }

      const rows: AccuracyRow[] = accuracyRows.map((row) => ({
        ...(row.showId ? showMetaByShowId.get(row.showId) : null) ??
          (row.showDate ? showMetaByShowDate.get(row.showDate) : null) ?? {
            venueName: null,
            city: null,
            state: null,
          },
        showDate: row.showDate,
        k10Recall: row.k10Recall,
        k25Recall: row.k25Recall,
        k50Recall: row.k50Recall,
        k10Precision: row.k10Precision,
        k25Precision: row.k25Precision,
        k50Precision: row.k50Precision,
      }));

      return rows.length === 0
        ? { status: "empty" }
        : { status: "ready", band, model, rows };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getShowDetailsByDate = cache(
  async (
    bandInput: string | undefined,
    showDate: string | null,
  ): Promise<RouteState<{ band: BandSlug; show: ShowDetails }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; show: ShowDetails }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; show: ShowDetails }>;
    }

    const band = bandState.band;
    if (!showDate) {
      return { status: "empty" };
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { showsTable } = bandState.bandEntry;
      const { data, error } = await client
        .from(showsTable)
        .select("*")
        .eq("show_date", showDate)
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = asRecord(data?.[0]);
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        show: buildShowDetails(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getNextShowDetails = cache(
  async (
    bandInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; show: ShowDetails }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; show: ShowDetails }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; show: ShowDetails }>;
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const todayIso = new Date().toISOString().slice(0, 10);
      if (bandState.band === "um") {
        const { data: upcomingData, error: upcomingError } = await client
          .from("um_upcoming_shows")
          .select("*")
          .gte("starts_at_local", todayIso)
          .order("starts_at_local", { ascending: true })
          .order("starts_at", { ascending: true })
          .limit(25);

        if (upcomingError) {
          return { status: "error", message: upcomingError.message };
        }

        const upcomingRows = (upcomingData ?? [])
          .map((item) => asRecord(item))
          .filter((item): item is Record<string, unknown> => item !== null);
        const upcomingRow = selectUmUpcomingShowRow(upcomingRows);

        if (upcomingRow) {
          return {
            status: "ready",
            band: bandState.band,
            show: buildShowDetails(upcomingRow),
          };
        }
      }

      const { data, error } = await client
        .from(bandState.bandEntry.showsTable)
        .select("*")
        .gte("show_date", todayIso)
        .order("show_date", { ascending: true })
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = asRecord(data?.[0]);
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band: bandState.band,
        show: buildShowDetails(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

async function getSetlistForDate(
  band: BandSlug,
  showDate: string,
): Promise<SetlistSnapshot | null> {
  const client = getSupabaseServerClient();
  if (!client) {
    return null;
  }

  const bandsState = await getBands();
  if (bandsState.status !== "ready") {
    return null;
  }

  const bandEntry = bandEntryBySlug(bandsState.bands, band);
  if (!bandEntry) {
    return null;
  }

  const { idColumn, showsTable } = bandEntry;
  const positionColumn = band === "phish" ? "position" : "song_position";
  const setlistTable = `${band}_setlists_raw`;

  const { data: showRows, error: showError } = await client
    .from(showsTable)
    .select("*")
    .eq("show_date", showDate)
    .limit(1);

  const showRow = asRecord(showRows?.[0]);
  const showId = showRow?.[idColumn];

  if (showError || !showId) {
    return null;
  }

  const [setlistResponse, detailResponse] = await Promise.all([
    client
      .from(setlistTable)
      .select("*")
      .eq(idColumn, showId)
      .order("set_number", { ascending: true })
      .order(positionColumn, { ascending: true }),
    client.from(showsTable).select("*").eq(idColumn, showId).limit(1),
  ]);

  if (setlistResponse.error || detailResponse.error) {
    return null;
  }

  const seen = new Set<string>();
  const songs: SetlistSong[] =
    setlistResponse.data?.flatMap((item) => {
      const row = asRecord(item);
      if (!row) {
        return [];
      }

      const key = `${row.set_number}-${row[positionColumn]}`;
      if (seen.has(key)) {
        return [];
      }
      seen.add(key);
      return [
        {
          setNumber: parseNumber(row.set_number),
          position: parseNumber(row[positionColumn]),
          songName: String(row.song_name ?? "Unknown Song"),
        },
      ];
    }) ?? [];

  return {
    showDetails: detailResponse.data?.[0] ?? null,
    songs,
  };
}

function buildFallbackSetlistFromHistoricalRow(
  row: Record<string, unknown> | null,
): SetlistSnapshot | null {
  if (!row) {
    return null;
  }

  const actualSongs = parseStringArray(row.actual_songs);
  if (actualSongs.length === 0) {
    return null;
  }

  return {
    showDetails: null,
    songs: actualSongs.map((songName, index) => ({
      setNumber: null,
      position: index + 1,
      songName,
    })),
  };
}

export const getLastShowSetlist = cache(
  async (bandInput: string | undefined): Promise<RouteState<{ band: BandSlug; setlist: SetlistSnapshot }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; setlist: SetlistSnapshot }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; setlist: SetlistSnapshot }>;
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { showsTable } = bandState.bandEntry;
      const todayIso = new Date().toISOString().slice(0, 10);

      const { data: recentShows, error } = await client
        .from(showsTable)
        .select("*")
        .lt("show_date", todayIso)
        .order("show_date", { ascending: false })
        .limit(50);

      if (error) {
        return { status: "error", message: error.message };
      }

      const selectedDate = recentShows?.[0]?.show_date;
      if (typeof selectedDate !== "string") {
        return { status: "empty" };
      }

      const setlist = await getSetlistForDate(band, selectedDate);
      if (!setlist) {
        return { status: "empty" };
      }

      return { status: "ready", band, setlist };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export async function getExplorerSnapshot(
  bandInput: string | undefined,
  modelInput: string | undefined,
  selectedDateInput?: string,
): Promise<RouteState<{ band: BandSlug; model: ModelSlug; explorer: ExplorerSnapshot }>> {
  const datesState = await getPredictionDates(bandInput, modelInput);

  if (datesState.status !== "ready") {
    return datesState as RouteState<{
      band: BandSlug;
      model: ModelSlug;
      explorer: ExplorerSnapshot;
    }>;
  }

  const selectedDate =
    selectedDateInput && datesState.dates.includes(selectedDateInput)
      ? selectedDateInput
      : datesState.dates[0] ?? null;
  if (!selectedDate) {
    return { status: "empty" };
  }

  const [predictionsState, setlist] = await Promise.all([
    getPredictionsForDate(datesState.band, datesState.model, selectedDate),
    getSetlistForDate(datesState.band, selectedDate),
  ]);

  if (predictionsState.status !== "ready") {
    return predictionsState as RouteState<{
      band: BandSlug;
      model: ModelSlug;
      explorer: ExplorerSnapshot;
    }>;
  }

  return {
    status: "ready",
    band: datesState.band,
    model: datesState.model,
    explorer: {
      availableDates: datesState.dates,
      selectedDate,
      predictions: predictionsState.snapshot,
      setlist,
    },
  };
}

export const getReplaySnapshot = cache(
  async (
    bandInput: string | undefined,
    selectedDateInput?: string,
    modelAInput?: string,
    modelBInput?: string,
    replayWindow = 50,
  ): Promise<RouteState<{ band: BandSlug; replay: ReplaySnapshot }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; replay: ReplaySnapshot }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; replay: ReplaySnapshot }>;
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const band = bandState.band;
      const { showsTable } = bandState.bandEntry;
      const [modelA, modelB] = resolveReplayModels(modelAInput, modelBInput);
      const modelVersions = await Promise.all(
        [modelA, modelB].map(async (model) => ({
          model,
          version: await getCurrentModelVersion(client, band, model),
        })),
      );

      const historicalRowsByModel = await Promise.all(
        modelVersions.map(async ({ model, version }) => {
          const { data, error } = await client
            .from("historical_prediction_runs")
            .select("target_show_date, generated_at")
            .eq("band", band)
            .eq("model_slug", model)
            .eq("model_version", version)
            .order("target_show_date", { ascending: false })
            .order("generated_at", { ascending: false })
            .limit(Math.max(replayWindow * 4, 100));

          if (error) {
            throw new Error(error.message);
          }

          const dedupedDates: string[] = [];
          const seen = new Set<string>();
          for (const item of data ?? []) {
            const row = asRecord(item);
            const showDate =
              row && typeof row.target_show_date === "string"
                ? row.target_show_date
                : null;
            if (!showDate || seen.has(showDate)) {
              continue;
            }
            seen.add(showDate);
            dedupedDates.push(showDate);
          }

          return { model, dates: dedupedDates };
        }),
      );

      const replayableDateSet = historicalRowsByModel.reduce<Set<string> | null>(
        (shared, entry) => {
          const dates = new Set(entry.dates);
          if (!shared) {
            return dates;
          }

          return new Set([...shared].filter((date) => dates.has(date)));
        },
        null,
      );

      const availableDates = [...(replayableDateSet ?? new Set<string>())]
        .sort((left, right) => right.localeCompare(left))
        .slice(0, replayWindow);

      if (availableDates.length === 0) {
        return { status: "empty" };
      }

      const selectedDate =
        selectedDateInput && availableDates.includes(selectedDateInput)
          ? selectedDateInput
          : availableDates[0] ?? null;

      if (!selectedDate) {
        return { status: "empty" };
      }

      const { data: showRows, error: showError } = await client
        .from(showsTable)
        .select("*")
        .in("show_date", availableDates);

      if (showError) {
        return { status: "error", message: showError.message };
      }

      const showByDate = new Map<string, Record<string, unknown>>();
      for (const item of showRows ?? []) {
        const row = asRecord(item);
        if (!row || typeof row.show_date !== "string") {
          continue;
        }
        showByDate.set(row.show_date, row);
      }

      const availableShows = availableDates.map((showDate) => ({
        showDate,
        venueName: getVenueNameFromRow(showByDate.get(showDate) ?? null),
      }));

      const historicalSnapshots = await Promise.all(
        modelVersions.map(async ({ model, version }) => {
          const { data, error } = await client
            .from("historical_prediction_runs")
            .select("*")
            .eq("band", band)
            .eq("model_slug", model)
            .eq("model_version", version)
            .eq("target_show_date", selectedDate)
            .order("generated_at", { ascending: false })
            .limit(1);

          if (error) {
            throw new Error(error.message);
          }

          const row = asRecord(data?.[0]);
          return {
            model,
            row,
            snapshot: row ? buildPredictionSnapshotFromCanonicalRow(row) : null,
          };
        }),
      );

      const snapshots = historicalSnapshots.reduce<Partial<Record<ModelSlug, PredictionSnapshot | null>>>(
        (acc, entry) => {
          acc[entry.model] = entry.snapshot;
          return acc;
        },
        {},
      );

      const setlist =
        (await getSetlistForDate(band, selectedDate)) ??
        buildFallbackSetlistFromHistoricalRow(
          historicalSnapshots.find((entry) => entry.row)?.row ?? null,
        );

      const selectedShow = showByDate.get(selectedDate) ?? null;

      return {
        status: "ready",
        band,
        replay: {
          availableShows,
          selectedDate,
          show: selectedShow ? buildShowDetails(selectedShow) : null,
          setlist,
          modelA,
          modelB,
          snapshots,
        },
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getBands = cache(
  async (): Promise<RouteState<{ bands: BandEntry[] }>> => {
    const missingEnv = getClientOrState<{ bands: BandEntry[] }>();
    if (missingEnv) {
      return missingEnv;
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { data, error } = await client
        .from("bands")
        .select("slug, display_name, shows_table, id_column")
        .eq("is_active", true)
        .order("display_name", { ascending: true });

      if (error) {
        return { status: "error", message: error.message };
      }

      const bands: BandEntry[] =
        data?.map((row) => ({
          slug: String(row.slug),
          displayName: String(row.display_name),
          showsTable: String(row.shows_table),
          idColumn: String(row.id_column),
        })) ?? [];

      if (bands.length === 0) {
        return { status: "empty" };
      }

      return { status: "ready", bands };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
);

export function bandEntryBySlug(
  bands: BandEntry[],
  slug: string,
): BandEntry | undefined {
  return bands.find((b) => b.slug === slug);
}

export function isValidBandSlug(bands: BandEntry[], slug: string): boolean {
  return bands.some((b) => b.slug === slug);
}
