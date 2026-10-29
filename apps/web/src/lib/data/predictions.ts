import "server-only";

import { cacheTag } from "next/cache";

import { bandCacheTag, normalizeBand, type BandSlug } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { selectLivePredictionSeedRow } from "@/lib/prediction-selection";

import { getClientOrState, getBandContext } from "./bands";
import { applyBandCacheLife } from "./cache-policy";
import { getLatestSetlistPredictionModelVersion } from "./model-version";
import { asRecord, buildPredictionSnapshotFromCanonicalRow } from "./parsers";
import type { PredictionSnapshot, RouteState } from "./types";

const SETLIST_PREDICTION_SNAPSHOT_SELECT =
  "band, target_show_key, target_show_date, reference_date, model_version, generated_at, created_at, predictions";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function toSeedRows(data: unknown[]) {
  return data
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((row) => ({
      reference_date:
        typeof row.reference_date === "string" ? row.reference_date : null,
      target_show_date:
        typeof row.target_show_date === "string" ? row.target_show_date : null,
      target_show_key:
        typeof row.target_show_key === "string" ? row.target_show_key : null,
      predicted_at:
        typeof row.generated_at === "string"
          ? row.generated_at
          : null,
      model_version:
        typeof row.model_version === "string" ? row.model_version : null,
    }));
}

// ---------------------------------------------------------------------------
// Public cached fetchers
// ---------------------------------------------------------------------------

type PredictionState = RouteState<{
  band: BandSlug;
  snapshot: PredictionSnapshot;
}>;

/**
 * `todayIso` is the Eastern date, captured by the caller: cached functions must
 * not read the clock. Predictions for a show happening today are kept out of
 * the cache because the live tracker refreshes them while the show is on.
 */
export async function getLatestPredictions(
  bandInput: string | undefined,
  todayIso: string,
): Promise<PredictionState> {
  "use cache";
  cacheTag(bandCacheTag(normalizeBand(bandInput)));

  const state = await loadLatestPredictions(bandInput, todayIso);
  applyBandCacheLife(state.status, {
    live: state.status === "ready" && state.snapshot.targetShowDate === todayIso,
  });
  return state;
}

async function loadLatestPredictions(
  bandInput: string | undefined,
  todayIso: string,
): Promise<PredictionState> {
  const missingEnv = getClientOrState<{
    band: BandSlug;
    snapshot: PredictionSnapshot;
  }>();
  if (missingEnv) {
    return missingEnv;
  }

  const client = getSupabaseServerClient();

  if (!client) {
    return { status: "missing_env" };
  }

  try {
    const [bandState, modelVersion] = await Promise.all([
      getBandContext(bandInput),
      getLatestSetlistPredictionModelVersion(client, normalizeBand(bandInput)),
    ]);
    if (bandState.status !== "ready") {
      return bandState as PredictionState;
    }
    const band = bandState.band;
    let seedQuery = client
      .from("setlist_predictions")
      .select(
        "reference_date, target_show_date, generated_at, model_version, target_show_key",
      )
      .eq("band", band);

    if (modelVersion) {
      seedQuery = seedQuery.eq("model_version", modelVersion);
    }

    const { data: seedRows, error: seedError } = await seedQuery
      .order("generated_at", { ascending: false })
      .limit(100);

    if (seedError) {
      return { status: "error", message: seedError.message };
    }

    const seedRow = selectLivePredictionSeedRow(toSeedRows(seedRows ?? []), {
      todayIso,
      modelVersion,
    });

    if (!seedRow?.model_version || !seedRow.target_show_key) {
      return { status: "empty" };
    }

    const matchedSeed = (seedRows ?? []).find(
      (r) =>
        r.target_show_key === seedRow.target_show_key &&
        r.model_version === seedRow.model_version,
    );

    if (!matchedSeed?.target_show_key) {
      return { status: "empty" };
    }

    const { data, error } = await client
      .from("setlist_predictions")
      .select(SETLIST_PREDICTION_SNAPSHOT_SELECT)
      .eq("band", band)
      .eq("model_version", matchedSeed.model_version)
      .eq("target_show_key", matchedSeed.target_show_key)
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
      snapshot: buildPredictionSnapshotFromCanonicalRow(row),
    };
  } catch (error) {
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

export async function getPredictionsForDate(
  bandInput: string | undefined,
  targetShowDate: string,
): Promise<PredictionState> {
  "use cache";
  cacheTag(bandCacheTag(normalizeBand(bandInput)));

  const state = await loadPredictionsForDate(bandInput, targetShowDate);
  applyBandCacheLife(state.status);
  return state;
}

async function loadPredictionsForDate(
  bandInput: string | undefined,
  targetShowDate: string,
): Promise<PredictionState> {
  const missingEnv = getClientOrState<{
    band: BandSlug;
    snapshot: PredictionSnapshot;
  }>();
  if (missingEnv) {
    return missingEnv;
  }

  const client = getSupabaseServerClient();

  if (!client) {
    return { status: "missing_env" };
  }

  try {
    const [bandState, modelVersion] = await Promise.all([
      getBandContext(bandInput),
      getLatestSetlistPredictionModelVersion(client, normalizeBand(bandInput)),
    ]);
    if (bandState.status !== "ready") {
      return bandState as PredictionState;
    }
    const band = bandState.band;
    let resultQuery = client
      .from("setlist_results")
      .select(SETLIST_PREDICTION_SNAPSHOT_SELECT)
      .eq("band", band)
      .eq("target_show_date", targetShowDate)
      .order("generated_at", { ascending: false });

    if (modelVersion) {
      resultQuery = resultQuery.eq("model_version", modelVersion);
    }

    const { data: resultData, error: resultError } = await resultQuery.limit(1);

    if (resultError) {
      return { status: "error", message: resultError.message };
    }

    let row = resultData?.[0];
    if (!row) {
      let liveQuery = client
        .from("setlist_predictions")
        .select(SETLIST_PREDICTION_SNAPSHOT_SELECT)
        .eq("band", band)
        .eq("target_show_date", targetShowDate)
        .order("generated_at", { ascending: false });

      if (modelVersion) {
        liveQuery = liveQuery.eq("model_version", modelVersion);
      }

      const { data: liveData, error: liveError } = await liveQuery.limit(1);

      if (liveError) {
        return { status: "error", message: liveError.message };
      }

      row = liveData?.[0];
    }
    if (!row) {
      return { status: "empty" };
    }

    return {
      status: "ready",
      band,
      snapshot: buildPredictionSnapshotFromCanonicalRow(row),
    };
  } catch (error) {
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unknown error",
    };
  }
}
