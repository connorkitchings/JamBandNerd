"use client";

import { useEffect } from "react";

import { BAND_COOKIE } from "@/lib/band-cookie";

/** Remembers the viewed band so a bare `/` can return the visitor to it. */
export function RememberBand({ band }: { band: string }) {
  useEffect(() => {
    try {
      const current = document.cookie
        .split("; ")
        .find((entry) => entry.startsWith(`${BAND_COOKIE}=`))
        ?.slice(BAND_COOKIE.length + 1);
      if (current !== band) {
        document.cookie = `${BAND_COOKIE}=${band}; path=/; max-age=31536000; samesite=lax`;
      }
    } catch {
      // Cookies unavailable; the preference is optional.
    }
  }, [band]);

  return null;
}
