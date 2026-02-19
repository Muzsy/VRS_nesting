#!/usr/bin/env python3
"""Phase 4 cleanup lifecycle smoke test.

Calls Supabase RPC cleanup functions via Management API to verify that the
lifecycle rules (7d/30d/24h) are properly deployable and callable.

When SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars are not set,
the script exits with 0 (SKIP) — suitable for CI without live Supabase.

Functions tested (from api/sql/phase4_cleanup_edge_functions.sql):
  - list_cleanup_candidates  : returns eligible rows for 7d/30d/24h cleanup
  - try_acquire_cleanup_lock : acquires a distributed cleanup lock
  - release_cleanup_lock     : releases a distributed cleanup lock
"""
import json
import os
import sys
import urllib.error
import urllib.request


def rpc_call(base_url: str, service_role_key: str, fn_name: str, body: dict) -> tuple[int, object]:
    url = f"{base_url.rstrip('/')}/rest/v1/rpc/{fn_name}"
    data = json.dumps(body).encode()
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = raw.decode(errors="replace")
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        return exc.code, exc.reason


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_role_key:
        print("[SKIP] cleanup smoke: SUPABASE env vars not set")
        sys.exit(0)

    print(f"[INFO] Supabase URL: {supabase_url}")
    print("[INFO] Running cleanup lifecycle smoke...")

    errors: list[str] = []

    # Step 1: list_cleanup_candidates — discover rows eligible for lifecycle cleanup
    fn = "list_cleanup_candidates"
    status, payload = rpc_call(supabase_url, service_role_key, fn, {"p_limit": 50})
    print(f"[{fn}] status={status} candidates={len(payload) if isinstance(payload, list) else payload}")
    if status not in (200, 204):
        errors.append(f"{fn} returned HTTP {status}: {payload}")

    # Step 2: try_acquire_cleanup_lock — verify lock mechanism is deployable
    fn = "try_acquire_cleanup_lock"
    status, payload = rpc_call(
        supabase_url,
        service_role_key,
        fn,
        {"p_lock_name": "smoke-test-lock", "p_owner": "smoke", "p_ttl_seconds": 30},
    )
    acquired = payload if isinstance(payload, bool) else bool(payload)
    print(f"[{fn}] status={status} acquired={acquired}")
    if status not in (200, 204):
        errors.append(f"{fn} returned HTTP {status}: {payload}")

    # Step 3: release_cleanup_lock — always release after acquiring
    fn = "release_cleanup_lock"
    status, payload = rpc_call(supabase_url, service_role_key, fn, {"p_lock_name": "smoke-test-lock"})
    print(f"[{fn}] status={status}")
    if status not in (200, 204):
        errors.append(f"{fn} returned HTTP {status}: {payload}")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(1)

    print("[PASS] cleanup lifecycle smoke passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
