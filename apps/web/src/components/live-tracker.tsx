"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@supabase/supabase-js";

import { matchesPredictionUpdateScope } from "@/lib/live-updates";

type Props = {
  band: string;
  model: string;
  referenceDate: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
};

export function LiveTracker({
  band,
  model,
  referenceDate,
  supabaseUrl,
  supabaseAnonKey,
}: Props) {
  const router = useRouter();

  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey || !band || !model || !referenceDate) return;

    const supabase = createClient(supabaseUrl, supabaseAnonKey);
    const channel = supabase
      .channel(`live-updates-${band}-${model}-${referenceDate}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "prediction_songs",
          filter: `band=eq.${band}`,
        },
        (payload) => {
          const scopedUpdate =
            matchesPredictionUpdateScope(payload.new, { band, model, referenceDate }) ||
            matchesPredictionUpdateScope(payload.old, { band, model, referenceDate });
          if (scopedUpdate) {
            router.refresh();
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [band, model, referenceDate, supabaseUrl, supabaseAnonKey, router]);

  return null;
}
