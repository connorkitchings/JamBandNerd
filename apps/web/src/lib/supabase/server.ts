import "server-only";

import fs from "node:fs";
import path from "node:path";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

function getRequiredEnv(name: "SUPABASE_URL" | "SUPABASE_ANON_KEY" | "SUPABASE_SERVICE_ROLE_KEY"): string | null {
  const directValue = process.env[name];
  if (directValue) {
    return directValue;
  }

  const localFiles = [
    path.resolve(process.cwd(), ".env.local"),
    path.resolve(process.cwd(), ".env"),
    path.resolve(process.cwd(), "..", "..", ".env.local"),
    path.resolve(process.cwd(), "..", "..", ".env"),
  ];

  for (const filePath of localFiles) {
    try {
      if (!fs.existsSync(filePath)) {
        continue;
      }

      const contents = fs.readFileSync(filePath, "utf8");
      for (const line of contents.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
          continue;
        }

        const equalsIndex = trimmed.indexOf("=");
        const key = trimmed.slice(0, equalsIndex).trim();
        if (key !== name) {
          continue;
        }

        let value = trimmed.slice(equalsIndex + 1).trim();
        if (
          (value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))
        ) {
          value = value.slice(1, -1);
        }

        if (value) {
          return value;
        }
      }
    } catch {
      continue;
    }
  }

  return null;
}

function looksLikeSecretKey(value: string | null): boolean {
  return typeof value === "string" && value.startsWith("sb_secret_");
}

export function allowsLocalSecretAnonKey(): boolean {
  return process.env.NODE_ENV === "development" || process.env.VERCEL !== "1";
}

export function hasSupabaseEnv(): boolean {
  const url = getRequiredEnv("SUPABASE_URL");
  const key = getRequiredEnv("SUPABASE_ANON_KEY");
  if (!url || !key) return false;
  if (allowsLocalSecretAnonKey()) return true;
  return !looksLikeSecretKey(key);
}

export function getServiceRoleClient(): SupabaseClient | null {
  const url = getRequiredEnv("SUPABASE_URL");
  const key = getRequiredEnv("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !key) {
    return null;
  }
  return createClient(url, key) as SupabaseClient;
}

export function getSupabaseServerClient(): SupabaseClient | null {
  const url = getRequiredEnv("SUPABASE_URL");
  const key = getRequiredEnv("SUPABASE_ANON_KEY");

  if (!url || !key) return null;
  if (allowsLocalSecretAnonKey()) {
    return createClient(url, key, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }
  if (looksLikeSecretKey(key)) return null;

  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
