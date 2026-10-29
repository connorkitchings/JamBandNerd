import { NextRequest, NextResponse } from "next/server";

import { getLegacyRedirect } from "@/lib/legacy-redirects";

// Permanently redirects pre-`/<band>` URLs (`/predictions?band=goose`, ...).
export function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const target = getLegacyRedirect(pathname, searchParams);
  if (!target) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = target.pathname;
  url.search = target.search;
  return NextResponse.redirect(url, 308);
}

// Must be a literal (statically analyzed); keep in sync with `PAGE_BY_LEGACY_PATH`.
export const config = {
  matcher: ["/", "/predictions", "/performance", "/replay", "/last-show"],
};
