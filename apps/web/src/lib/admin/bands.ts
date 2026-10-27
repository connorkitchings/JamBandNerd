// The admin entry tool writes `city`/`state` and `source_hash`, which only the
// WSP raw tables have. Other bands use different show schemas, so writes for
// them would fail or silently drop data. Keep the tool WSP-only until each band
// gets its own schema-aware path.
export const ADMIN_BAND_SLUGS: readonly string[] = ["wsp"];

export function isAdminBand(band: unknown): band is string {
  return typeof band === "string" && ADMIN_BAND_SLUGS.includes(band);
}
