"""Confirm website cache invalidation without forwarding credentials to redirects."""

from __future__ import annotations

import os
import time
from urllib.parse import urlsplit, urlunsplit

import requests

MAX_ATTEMPTS = 4
RETRY_DELAY_SECONDS = 5


def revalidate_website_cache(*, band: str, site_url: str, secret: str) -> None:
    """Require an exact server acknowledgement, retrying transient failures only."""
    if not all(value.strip() for value in (band, site_url, secret)):
        raise RuntimeError("BAND, SITE_URL and REVALIDATE_SECRET must be set")
    try:
        origin = urlsplit(site_url)
        valid_origin = (
            origin.scheme == "https"
            and bool(origin.hostname)
            and origin.username is None
            and origin.password is None
            and origin.path in {"", "/"}
            and "?" not in site_url
            and "#" not in site_url
            and "\\" not in site_url
            and "%" not in origin.netloc
            and not any(
                char.isspace() or ord(char) < 32 or ord(char) == 127
                for char in site_url
            )
            and (origin.port is None or origin.port > 0)
        )
    except ValueError:
        valid_origin = False
    if not valid_origin:
        raise RuntimeError(
            "SITE_URL must be an HTTPS origin without credentials, path or query"
        )
    endpoint = urlunsplit(("https", origin.netloc, "/api/revalidate", "", ""))

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {secret}"},
                json={"band": band},
                allow_redirects=False,
                timeout=30,
            )
        except requests.RequestException:
            # Exception messages may include request headers or untrusted bodies.
            if attempt + 1 == MAX_ATTEMPTS:
                raise RuntimeError(
                    "Website cache revalidation transport failed"
                ) from None
        else:
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    raise RuntimeError(
                        "Website cache revalidation returned invalid JSON"
                    ) from None
                if (
                    not isinstance(payload, dict)
                    or payload.get("revalidated") is not True
                    or payload.get("band") != band
                ):
                    raise RuntimeError(
                        "Website cache revalidation acknowledgement did not match"
                    )
                return
            transient = response.status_code == 429 or 500 <= response.status_code < 600
            if not transient or attempt + 1 == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Website cache revalidation returned HTTP {response.status_code}"
                )
        time.sleep(RETRY_DELAY_SECONDS)


def main() -> int:
    try:
        revalidate_website_cache(
            band=os.environ.get("BAND", ""),
            site_url=os.environ.get("SITE_URL", ""),
            secret=os.environ.get("REVALIDATE_SECRET", ""),
        )
    except RuntimeError as exc:
        print(f"::error::{exc}")
        return 1
    print("Website cache revalidation confirmed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
