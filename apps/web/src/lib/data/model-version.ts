import "server-only";

import type { SupabaseClient } from "@supabase/supabase-js";

export async function getLatestSetlistPredictionModelVersion(
  client: SupabaseClient,
  band: string,
) {
  const { data, error } = await client
    .from("setlist_predictions")
    .select("model_version")
    .eq("band", band)
    .order("generated_at", { ascending: false })
    .limit(1);

  if (error) {
    throw new Error(error.message);
  }

  const modelVersion = data?.[0]?.model_version;
  return typeof modelVersion === "string" && modelVersion.length > 0
    ? modelVersion
    : null;
}
