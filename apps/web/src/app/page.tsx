import { redirect } from "next/navigation";

import { bandPath } from "@/lib/band-routes";
import { DEFAULT_BAND_SLUG } from "@/lib/config";

// The site is band-scoped: the root sends visitors to the default band.
// This is a temporary redirect because the default band can change.
export default function RootPage() {
  redirect(bandPath(DEFAULT_BAND_SLUG));
}
