import "server-only";

import { cache } from "react";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

function getRequiredEnv(name: "SUPABASE_URL" | "SUPABASE_KEY"): string | null {
  return process.env[name] ?? null;
}

export function hasSupabaseEnv(): boolean {
  return Boolean(getRequiredEnv("SUPABASE_URL") && getRequiredEnv("SUPABASE_KEY"));
}

export const getSupabaseServerClient = cache((): SupabaseClient | null => {
  const url = getRequiredEnv("SUPABASE_URL");
  const key = getRequiredEnv("SUPABASE_KEY");

  if (!url || !key) {
    return null;
  }

  return createClient(url, key, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  });
});
