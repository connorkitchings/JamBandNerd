import "server-only";

import { cache } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";

import {
  BAND_CONFIG,
  BAND_ID_COLUMNS,
  type BandSlug,
  type LikelihoodTier,
  type ModelSlug,
  normalizeBand,
  normalizeModel,
} from "@/lib/config";
import { getSupabaseServerClient, hasSupabaseEnv } from "@/lib/supabase/server";

type JsonPrediction = Record<string, unknown>;
type ProjectionRow = Record<string, unknown>;

export type PredictionRow = {
  rank: number;
  songName: string;
  lastPlayed: string | null;
  currentGap: number | null;
  playsPastYear: number | null;
  avgGap: number | null;
  gapRatio: number | null;
  gapZScore: number | null;
  ckplusScore: number | null;
  probability: number | null;
  tier: LikelihoodTier;
};

export type PredictionSnapshot = {
  referenceDate: string | null;
  predictedAt: string | null;
  modelVersion: string | null;
  predictions: PredictionRow[];
  raw: Record<string, unknown>;
};

export type AccuracyRow = {
  showDate: string | null;
  venueName: string | null;
  k10Recall: number | null;
  k25Recall: number | null;
  k50Recall: number | null;
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

export type ShowDetails = {
  venueName: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  showDate: string | null;
  raw: Record<string, unknown>;
};

export type ExplorerSnapshot = {
  availableDates: string[];
  selectedDate: string | null;
  predictions: PredictionSnapshot | null;
  setlist: SetlistSnapshot | null;
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

function computeTier(rank: number, probability: number | null): LikelihoodTier {
  // When a future model supplies real probabilities, use those
  if (probability !== null) {
    if (probability >= 0.15) return "expected";
    if (probability >= 0.08) return "hot";
    if (probability >= 0.03) return "likely";
    return "possible";
  }

  // Rank-based tiers
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
      playsPastYear: parseNumber(row.plays_past_year),
      avgGap: parseNumber(row.avg_gap),
      gapRatio: parseNumber(row.gap_ratio),
      gapZScore: parseNumber(row.gap_z_score),
      ckplusScore: parseNumber(row.ckplus_score),
      probability,
      tier: computeTier(rank, probability),
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
      playsPastYear: parseNumber(payload.plays_past_year),
      avgGap: parseNumber(payload.avg_gap),
      gapRatio: parseNumber(payload.gap_ratio),
      gapZScore: parseNumber(payload.gap_z_score),
      ckplusScore: parseNumber(payload.ckplus_score),
      probability,
      tier: computeTier(rank, probability),
    };
  });
}

function buildPredictionSnapshotFromCanonicalRow(
  row: Record<string, unknown>,
): PredictionSnapshot {
  return {
    referenceDate:
      typeof row.reference_date === "string" ? row.reference_date : null,
    predictedAt:
      typeof row.predicted_at === "string"
        ? row.predicted_at
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

  if (referenceDate) {
    seedQuery = seedQuery.eq("reference_date", referenceDate);
  }

  const { data: seedRows, error: seedError } = await seedQuery
    .order("predicted_at", { ascending: false })
    .order("reference_date", { ascending: false })
    .order("rank", { ascending: true })
    .limit(1);

  if (seedError) {
    throw seedError;
  }

  const seedRow = asRecord(seedRows?.[0]);
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

    const band = normalizeBand(bandInput);
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

export function calculateModelAgreement(
  primaryRows: PredictionRow[],
  secondaryRows: PredictionRow[],
  k = 25
): { percentage: number; matchCount: number; k: number } | null {
  if (!primaryRows.length || !secondaryRows.length) return null;

  const primaryTopK = primaryRows.slice(0, k).map(r => r.songName.toLowerCase());
  const secondaryTopK = secondaryRows.slice(0, k).map(r => r.songName.toLowerCase());
  
  const secondarySet = new Set(secondaryTopK);
  let matchCount = 0;
  
  for (const song of primaryTopK) {
    if (secondarySet.has(song)) {
      matchCount++;
    }
  }

  // Calculate percentage against the actual number of items we could compare 
  // (in case a brand new band has fewer than K total songs predicted)
  const actualK = Math.min(k, primaryTopK.length, secondaryTopK.length);
  const percentage = actualK > 0 ? matchCount / actualK : 0;

  return {
    percentage,
    matchCount,
    k: actualK
  };
}

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

    const band = normalizeBand(bandInput);
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

    const band = normalizeBand(bandInput);
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { data, error } = await client
        .from(`predictions_${model}`)
        .select("reference_date")
        .eq("band", band)
        .order("reference_date", { ascending: false });

      if (error) {
        return { status: "error", message: error.message };
      }

      const dates = [...new Set((data ?? []).map((row) => row.reference_date).filter(Boolean))];
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

    const band = normalizeBand(bandInput);
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const modelVersion = await getCurrentModelVersion(client, band, model);
      const { data, error } = await client
        .from("accuracy_per_show")
        .select("show_id, show_date, k10_recall, k25_recall, k50_recall")
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
        })) ?? [];

      if (accuracyRows.length === 0) {
        return { status: "empty" };
      }

      const idColumn = BAND_ID_COLUMNS[band];
      const showsTable = BAND_CONFIG[band].showsTable;
      const showIds = [...new Set(accuracyRows.map((row) => row.showId).filter(Boolean))];
      const showDates = [...new Set(accuracyRows.map((row) => row.showDate).filter(Boolean))];
      const venueByShowId = new Map<string, string | null>();
      const venueByShowDate = new Map<string, string | null>();

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

          const venueName = getVenueNameFromRow(row);
          const showIdValue = row[idColumn];
          if (typeof showIdValue === "string" || typeof showIdValue === "number") {
            venueByShowId.set(String(showIdValue), venueName);
          }

          if (typeof row.show_date === "string") {
            venueByShowDate.set(row.show_date, venueName);
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

          venueByShowDate.set(row.show_date, getVenueNameFromRow(row));
        }
      }

      const rows: AccuracyRow[] = accuracyRows.map((row) => ({
        showDate: row.showDate,
        venueName:
          (row.showId ? venueByShowId.get(row.showId) : null) ??
          (row.showDate ? venueByShowDate.get(row.showDate) : null) ??
          null,
        k10Recall: row.k10Recall,
        k25Recall: row.k25Recall,
        k50Recall: row.k50Recall,
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

    const band = normalizeBand(bandInput);
    if (!showDate) {
      return { status: "empty" };
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const showsTable = BAND_CONFIG[band].showsTable;
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
        show: {
          venueName:
            typeof row.venue_name === "string"
              ? row.venue_name
              : typeof row.venue === "string"
                ? row.venue
                : null,
          city:
            typeof row.venue_city === "string"
              ? row.venue_city
              : typeof row.city === "string"
                ? row.city
                : null,
          state:
            typeof row.venue_state === "string"
              ? row.venue_state
              : typeof row.state === "string"
                ? row.state
                : null,
          country:
            typeof row.venue_country === "string"
              ? row.venue_country
              : typeof row.country === "string"
                ? row.country
                : null,
          showDate: typeof row.show_date === "string" ? row.show_date : null,
          raw: row,
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

async function getSetlistForDate(
  band: BandSlug,
  showDate: string,
): Promise<SetlistSnapshot | null> {
  const client = getSupabaseServerClient();
  if (!client) {
    return null;
  }

  const idColumn = BAND_ID_COLUMNS[band];
  const positionColumn = band === "phish" ? "position" : "song_position";
  const showsTable = BAND_CONFIG[band].showsTable;
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

export const getLastShowSetlist = cache(
  async (bandInput: string | undefined): Promise<RouteState<{ band: BandSlug; setlist: SetlistSnapshot }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; setlist: SetlistSnapshot }>();
    if (missingEnv) {
      return missingEnv;
    }

    const band = normalizeBand(bandInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const showsTable = BAND_CONFIG[band].showsTable;
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

export const getGlobalSearchData = cache(
  async (): Promise<RouteState<{ items: { band: BandSlug; songName: string; rank: number }[] }>> => {
    const missingEnv = getClientOrState<{ items: { band: BandSlug; songName: string; rank: number }[] }>();
    if (missingEnv) return missingEnv;

    const client = getSupabaseServerClient();
    if (!client) return { status: "missing_env" };

    try {
      const bands = Object.keys(BAND_CONFIG) as BandSlug[];
      const items: { band: BandSlug; songName: string; rank: number }[] = [];

      await Promise.all(
        bands.map(async (band) => {
          // Default to fetching Notebook model for search index for now
          const model: ModelSlug = "notebook";
          
          try {
            const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
              band,
              model,
            });
            
            if (projectionSnapshot && projectionSnapshot.predictions) {
              for (const p of projectionSnapshot.predictions) {
                items.push({
                  band,
                  songName: p.songName,
                  rank: p.rank,
                });
              }
              return;
            }
          } catch (error) {
            console.error(`Failed to load search data for ${band} (projection)`, error);
          }

          const { data } = await client
            .from(`predictions_${model}`)
            .select("*")
            .eq("band", band)
            .order("reference_date", { ascending: false })
            .limit(1);

          const row = data?.[0];
          if (row) {
            const snapshot = buildPredictionSnapshotFromCanonicalRow(row);
            for (const p of snapshot.predictions) {
              items.push({
                band,
                songName: p.songName,
                rank: p.rank,
              });
            }
          }
        })
      );

      if (items.length === 0) return { status: "empty" };

      // Sort globally alphabetically
      items.sort((a, b) => a.songName.localeCompare(b.songName));
      return { status: "ready", items };
      
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
);
