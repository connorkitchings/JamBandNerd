import { createHash, timingSafeEqual } from "node:crypto";

import { bandCacheTag } from "./config.ts";

export type RevalidateDeps = {
  /** Shared secret from `REVALIDATE_SECRET`; requests fail closed when unset. */
  secret: string | undefined;
  /** Active band slugs, or `null` when the band list is unavailable. */
  getBandSlugs: () => Promise<readonly string[] | null>;
  /** Expires a cache tag immediately. */
  revalidate: (tag: string) => void;
};

function jsonResponse(body: Record<string, unknown>, status: number, headers?: HeadersInit) {
  return Response.json(body, { status, headers });
}

// Hash first so the comparison is constant-time even when lengths differ.
function tokensMatch(provided: string, expected: string) {
  const digest = (value: string) => createHash("sha256").update(value).digest();
  return timingSafeEqual(digest(provided), digest(expected));
}

function readBearerToken(request: Request): string | null {
  const header = request.headers.get("authorization");
  const match = header ? /^Bearer\s+(\S+)$/i.exec(header.trim()) : null;
  return match ? match[1] : null;
}

/**
 * Expires the cached data for one band. Called by the daily pipeline once new
 * data has landed. Error bodies are deliberately generic.
 */
export async function handleRevalidateRequest(
  request: Request,
  deps: RevalidateDeps,
): Promise<Response> {
  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405, { Allow: "POST" });
  }

  const token = readBearerToken(request);
  if (!deps.secret || !token || !tokensMatch(token, deps.secret)) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  let band: unknown;
  try {
    const body: unknown = await request.json();
    band =
      typeof body === "object" && body !== null
        ? (body as Record<string, unknown>).band
        : undefined;
  } catch {
    return jsonResponse({ error: "Invalid request" }, 400);
  }

  if (typeof band !== "string" || band.length === 0) {
    return jsonResponse({ error: "Invalid request" }, 400);
  }

  const slugs = await deps.getBandSlugs();
  if (!slugs) {
    return jsonResponse({ error: "Service unavailable" }, 503);
  }
  if (!slugs.includes(band)) {
    return jsonResponse({ error: "Invalid request" }, 400);
  }

  deps.revalidate(bandCacheTag(band));
  return jsonResponse({ revalidated: true, band }, 200);
}
