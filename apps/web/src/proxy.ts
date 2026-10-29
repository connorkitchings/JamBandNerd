import { NextRequest, NextResponse } from "next/server";

import { BAND_COOKIE } from "@/lib/band-cookie";
import { getLegacyRedirect, getRootRedirect } from "@/lib/legacy-redirects";

// Permanently redirects pre-`/<band>` URLs (`/predictions?band=goose`, ...) and
// sends a bare `/` to the visitor's remembered band (temporary, per visitor).
export function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const target =
    pathname === "/"
      ? getRootRedirect(searchParams, request.cookies.get(BAND_COOKIE)?.value)
      : getLegacyRedirect(pathname, searchParams);
  if (!target) {
    return NextResponse.next();
  }
  const permanent = !("permanent" in target) || target.permanent;

  const url = request.nextUrl.clone();
  url.pathname = target.pathname;
  url.search = target.search;
  const response = NextResponse.redirect(url, permanent ? 308 : 307);
  if (!permanent) {
    // The destination depends on the visitor's cookie; never let a CDN share it.
    response.headers.set("Cache-Control", "private, no-store");
  }
  return response;
}

// Must be a literal (statically analyzed); keep in sync with `PAGE_BY_LEGACY_PATH`.
export const config = {
  matcher: ["/", "/predictions", "/performance", "/replay", "/last-show"],
};
