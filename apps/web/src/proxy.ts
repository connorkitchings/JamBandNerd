import { NextRequest, NextResponse } from "next/server";

import { ADMIN_SESSION_COOKIE, verifyAdminSessionToken } from "@/lib/admin/session";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only gate admin routes
  if (!pathname.startsWith("/admin") && !pathname.startsWith("/api/admin")) {
    return NextResponse.next();
  }

  // Always allow the session endpoint — it is the login/logout mechanism itself
  if (pathname === "/api/admin/session") {
    return NextResponse.next();
  }

  // The admin page itself renders the configured / login / authenticated states.
  // Redirecting unauthenticated requests back to this same route causes a loop.
  if (pathname === "/admin/setlist") {
    return NextResponse.next();
  }

  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value;
  const isValid = verifyAdminSessionToken(token, process.env.ADMIN_SESSION_SECRET);

  if (!isValid) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/admin/setlist";
    loginUrl.searchParams.set("auth", "required");
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}
