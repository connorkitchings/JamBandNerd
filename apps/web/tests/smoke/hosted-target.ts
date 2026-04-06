const VERCEL_PREVIEW_HOST_SUFFIX = ".vercel.app";
const PRODUCTION_HOSTS = new Set(["jambandnerd.com", "www.jambandnerd.com"]);

function parseHostedUrl(baseUrl?: string): URL | undefined {
  if (!baseUrl) {
    return undefined;
  }

  return new URL(baseUrl);
}

export function normalizeHostedBaseUrl(baseUrl?: string): string | undefined {
  return baseUrl?.replace(/\/+$/, "");
}

export function requiresVercelProtectionBypass(baseUrl?: string): boolean {
  const parsedUrl = parseHostedUrl(baseUrl);

  if (!parsedUrl) {
    return false;
  }

  return (
    parsedUrl.hostname.endsWith(VERCEL_PREVIEW_HOST_SUFFIX) &&
    !PRODUCTION_HOSTS.has(parsedUrl.hostname)
  );
}

export function getVercelProtectionBypassToken(
  baseUrl: string | undefined,
  bypassToken: string | undefined,
): string | undefined {
  if (!requiresVercelProtectionBypass(baseUrl)) {
    return undefined;
  }

  if (!bypassToken) {
    throw new Error(
      "Hosted smoke against Vercel preview deployments requires VERCEL_PROTECTION_BYPASS_TOKEN.",
    );
  }

  return bypassToken;
}

export function getVercelProtectionBypassUrl(
  baseUrl: string,
  bypassToken: string,
): string {
  const parsedUrl = new URL(baseUrl);

  parsedUrl.searchParams.set("x-vercel-protection-bypass", bypassToken);
  parsedUrl.searchParams.set("x-vercel-set-bypass-cookie", "true");

  return parsedUrl.toString();
}
