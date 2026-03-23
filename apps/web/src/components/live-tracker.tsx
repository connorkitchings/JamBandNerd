"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@supabase/supabase-js";

type Props = {
  supabaseUrl: string;
  supabaseAnonKey: string;
};

export function LiveTracker({ supabaseUrl, supabaseAnonKey }: Props) {
  const router = useRouter();

  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) return;

    // Create a temporary client just for listening to the realtime channel
    // We intentionally don't try to reuse a global instance because we only need it for the socket connection.
    const supabase = createClient(supabaseUrl, supabaseAnonKey);
    const channel = supabase
      .channel('live-updates')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'prediction_songs' },
        () => {
          // When the database updates with new predictions while the user is looking at the page,
          // router.refresh() fetches the new server component payload without losing client state (like scroll).
          router.refresh();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [supabaseUrl, supabaseAnonKey, router]);

  return null;
}
