import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Internal design previews must be a real 404 outside development. The page's
  // own notFound() cannot set the status because the root loading boundary has
  // already streamed a 200.
  if (pathname.startsWith("/preview") && process.env.NODE_ENV !== "development") {
    return new NextResponse("Not found", { status: 404 });
  }

  return NextResponse.next();
}
