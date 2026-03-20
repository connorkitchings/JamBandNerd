import "server-only";

import { cache } from "react";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

function getRequiredEnv(name: "SUPABASE_URL" | "SUPABASE_ANON_KEY"): string | null {
  return process.env[name] ?? null;
}

function looksLikeSecretKey(value: string | null): boolean {
  return typeof value === "string" && value.startsWith("sb_secret_");
}

export function hasSupabaseEnv(): boolean {
  const url = getRequiredEnv("SUPABASE_URL");
  const key = getRequiredEnv("SUPABASE_ANON_KEY");
  return Boolean(url && key && !looksLikeSecretKey(key));
}

export const getSupabaseServerClient = cache((): SupabaseClient | null => {
  const url = getRequiredEnv("SUPABASE_URL");
  const key = getRequiredEnv("SUPABASE_ANON_KEY");

  if (!url || !key || looksLikeSecretKey(key)) {
    return null;
  }

  return createClient(url, key, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  });
});
