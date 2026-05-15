"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@supabase/supabase-js";

import { matchesPredictionUpdateScope } from "@/lib/live-updates";

type Props = {
  band: string;
  targetShowKey?: string | null;
  targetShowDate?: string | null;
  supabaseUrl: string;
  supabaseAnonKey: string;
};

export function LiveTracker({
  band,
  targetShowKey,
  targetShowDate,
  supabaseUrl,
  supabaseAnonKey,
}: Props) {
  const router = useRouter();

  useEffect(() => {
    if (
      !supabaseUrl ||
      !supabaseAnonKey ||
      !band ||
      (!targetShowKey && !targetShowDate)
    ) {
      return;
    }

    const supabase = createClient(supabaseUrl, supabaseAnonKey);
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
  }, [band, targetShowKey, targetShowDate, supabaseUrl, supabaseAnonKey, router]);

  return null;
}
