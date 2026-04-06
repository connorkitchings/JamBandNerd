import { createHmac, timingSafeEqual } from "node:crypto";

export const ADMIN_SESSION_COOKIE = "jbn_admin_session";

const SESSION_TTL_SECONDS = 60 * 60 * 8;

function signTimestamp(secret: string, timestamp: string) {
  return createHmac("sha256", secret).update(timestamp).digest("hex");
}

export function createAdminSessionToken(secret: string, now = Date.now()): string {
  const timestamp = Math.floor(now / 1000).toString();
  return `${timestamp}.${signTimestamp(secret, timestamp)}`;
}

export function verifyAdminSessionToken(
  token: string | undefined,
  secret: string | undefined,
  now = Date.now(),
): boolean {
  if (!token || !secret) {
    return false;
  }

  const [timestamp, providedSignature] = token.split(".");
  if (!timestamp || !providedSignature) {
    return false;
  }

  const issuedAtSeconds = Number(timestamp);
  if (!Number.isFinite(issuedAtSeconds)) {
    return false;
  }

  const ageSeconds = Math.floor(now / 1000) - issuedAtSeconds;
  if (ageSeconds < 0 || ageSeconds > SESSION_TTL_SECONDS) {
    return false;
  }

  const expectedSignature = signTimestamp(secret, timestamp);
  const expectedBuffer = Buffer.from(expectedSignature);
  const providedBuffer = Buffer.from(providedSignature);

  if (expectedBuffer.length !== providedBuffer.length) {
    return false;
  }

  return timingSafeEqual(expectedBuffer, providedBuffer);
}

export function buildAdminSessionCookie(secret: string) {
  return {
    name: ADMIN_SESSION_COOKIE,
    value: createAdminSessionToken(secret),
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  };
}

export function buildClearedAdminSessionCookie() {
  return {
    name: ADMIN_SESSION_COOKIE,
    value: "",
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  };
}
