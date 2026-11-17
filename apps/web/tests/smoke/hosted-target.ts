const VERCEL_PREVIEW_HOST_SUFFIX = ".vercel.app";

export function normalizeHostedBaseUrl(baseUrl?: string): string | undefined {
  if (!baseUrl) return undefined;
  const url = new URL(baseUrl);
  if (
    (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))) ||
    url.username || url.password || url.search || url.hash || url.pathname !== "/"
  ) {
    throw new Error("SMOKE_BASE_URL must be an HTTPS origin (HTTP allowed for loopback) without credentials, path, query, or fragment.");
  }
  return url.origin;
}

export function requiresVercelProtectionBypass(baseUrl?: string): boolean {
  const origin = normalizeHostedBaseUrl(baseUrl);
  return Boolean(origin && new URL(origin).hostname.endsWith(VERCEL_PREVIEW_HOST_SUFFIX));
}

export function getHostedAuthHeaders(
  baseUrl?: string,
  bypassToken?: string,
): Record<string, string> | undefined {
  if (!requiresVercelProtectionBypass(baseUrl)) return undefined;
  if (!bypassToken) {
    throw new Error("Protected preview smoke requires VERCEL_PROTECTION_BYPASS_TOKEN; use the Hosted Website Smoke workflow with its configured secret.");
  }
  return {
    "x-vercel-protection-bypass": bypassToken,
    "x-vercel-set-bypass-cookie": "true",
  };
}

export function validateHostedAuthResponse(origin: string, status: number, location?: string) {
  if (status < 200 || status >= 400) {
    throw new Error(`Preview authentication failed with HTTP ${status}.`);
  }

  if (location && new URL(location, origin).origin !== origin) {
    throw new Error("Preview authentication redirected outside the configured origin.");
  }
}
