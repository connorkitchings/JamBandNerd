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
            router.refresh();
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [band, targetShowKey, targetShowDate, router]);

  return null;
}
