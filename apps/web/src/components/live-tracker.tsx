"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { matchesPredictionUpdateScope } from "@/lib/live-updates";

type Props = {
  band: string;
  targetShowKey?: string | null;
  targetShowDate?: string | null;
};

// Bursts of row changes (a snapshot rewrites many rows) collapse into one
// trailing refresh.
const REFRESH_DEBOUNCE_MS = 3000;

let browserSupabase: SupabaseClient | null = null;

function getBrowserSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    return null;
  }

  browserSupabase ??= createClient(url, key);
  return browserSupabase;
}

export function LiveTracker({
  band,
  targetShowKey,
  targetShowDate,
}: Props) {
  const router = useRouter();

  useEffect(() => {
    const supabase = getBrowserSupabase();

    if (!supabase || !band || (!targetShowKey && !targetShowDate)) {
      return;
    }

    let refreshTimer: ReturnType<typeof setTimeout> | null = null;
    const scheduleRefresh = () => {
      if (refreshTimer !== null) {
        clearTimeout(refreshTimer);
      }
      refreshTimer = setTimeout(() => {
        refreshTimer = null;
        router.refresh();
      }, REFRESH_DEBOUNCE_MS);
    };

    const channel = supabase
      .channel(`live-updates-${band}-${targetShowKey ?? targetShowDate}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "setlist_prediction_songs",
          filter: `band=eq.${band}`,
        },
        (payload) => {
          const scopedUpdate =
            matchesPredictionUpdateScope(payload.new, {
              band,
              targetShowKey,
              targetShowDate,
            }) ||
            matchesPredictionUpdateScope(payload.old, {
              band,
              targetShowKey,
              targetShowDate,
            });
          if (scopedUpdate) {
            scheduleRefresh();
          }
        }
      )
      .subscribe();

    return () => {
      if (refreshTimer !== null) {
        clearTimeout(refreshTimer);
      }
      supabase.removeChannel(channel);
    };
  }, [band, targetShowKey, targetShowDate, router]);

  return null;
}
