#!/usr/bin/env python3
"""Scheduled health ping for uptime monitoring."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    health_url = os.environ.get("API_HEALTH_URL", "").strip()
    if not health_url:
        print("SKIP: API_HEALTH_URL is not set")
        return 0

    req = Request(health_url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as resp:
            status_code = int(resp.status)
            body = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"health check failed: status={exc.code} body={body[:400]}") from exc
    except URLError as exc:
        raise RuntimeError(f"health check network error: {exc}") from exc

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"health check unexpected status={status_code}")

    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"health response is not valid JSON: {body[:200]}") from exc

    status_text = str(payload.get("status", "")).strip().lower()
    if status_text != "ok":
        raise RuntimeError(f"health status is not ok: {payload}")

    print("[OK] health ping succeeded")
    print(f" url={health_url}")
    print(f" payload={payload}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
