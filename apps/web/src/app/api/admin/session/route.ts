import { NextResponse } from "next/server";

import {
  ADMIN_SESSION_COOKIE,
  buildAdminSessionCookie,
  buildClearedAdminSessionCookie,
  verifyAdminSessionToken,
} from "@/lib/admin/session";

function isAuthenticated(request: Request) {
  const token = request.headers
    .get("cookie")
    ?.split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(`${ADMIN_SESSION_COOKIE}=`))
    ?.split("=")
    .slice(1)
    .join("=");

  return verifyAdminSessionToken(token, process.env.ADMIN_SESSION_SECRET);
}

function isAdminConfigured() {
  return Boolean(process.env.ADMIN_PASSWORD && process.env.ADMIN_SESSION_SECRET);
}

export async function GET(request: Request) {
  if (!isAdminConfigured()) {
    return NextResponse.json({ authenticated: false, configured: false }, { status: 503 });
  }

  return NextResponse.json({ authenticated: isAuthenticated(request), configured: true });
}

export async function POST(request: Request) {
  if (!isAdminConfigured()) {
    return NextResponse.json({ error: "Admin not configured" }, { status: 503 });
  }

  const body = await request.json();
  const password = typeof body?.password === "string" ? body.password : "";
  if (!password || password !== process.env.ADMIN_PASSWORD) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const response = NextResponse.json({ authenticated: true });
  response.cookies.set(buildAdminSessionCookie(process.env.ADMIN_SESSION_SECRET!));
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ authenticated: false });
  response.cookies.set(buildClearedAdminSessionCookie());
  return response;
}
