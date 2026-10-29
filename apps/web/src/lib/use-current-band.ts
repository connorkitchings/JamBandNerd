"use client";

import { useParams } from "next/navigation";

import { isBandSlug } from "./band-routes";
import { DEFAULT_BAND_SLUG, type BandSlug } from "./config";

/** The band in the current URL, or the default band on pages outside `/<band>` (e.g. `/about`). */
export function useCurrentBand(): BandSlug {
  const { band } = useParams<{ band?: string }>();
  return band && isBandSlug(band) ? band : DEFAULT_BAND_SLUG;
}
