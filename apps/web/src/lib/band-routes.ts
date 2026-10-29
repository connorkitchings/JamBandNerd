/**
 * Band-scoped URL building. Every band page lives under `/<band>`; this is the
 * single place that knows the shape of those paths.
 */

import type { BandSlug } from "./config.ts";

export type BandPage = "overview" | "predictions" | "performance" | "replay";

/** Lowercase letters, digits, `-` and `_` only; rejects path separators and dots. */
const BAND_SLUG_PATTERN = /^[a-z0-9][a-z0-9_-]{0,31}$/;

const SHOW_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function isBandSlug(value: string): boolean {
  return BAND_SLUG_PATTERN.test(value);
}

export function isShowDate(value: string): boolean {
  return SHOW_DATE_PATTERN.test(value);
}

export function bandPath(
  band: BandSlug,
  page: BandPage = "overview",
  showDate?: string | null,
): string {
  if (page === "overview") {
    return `/${band}`;
  }
  if (page === "replay" && showDate) {
    return `/${band}/replay/${showDate}`;
  }
  return `/${band}/${page}`;
}
