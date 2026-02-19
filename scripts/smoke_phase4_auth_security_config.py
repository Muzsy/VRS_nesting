#!/usr/bin/env python3
"""Phase 4 auth security config guard (read-only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def _resolve_env(key: str) -> str:
    process_value = os.environ.get(key, "").strip()
    if process_value:
        return process_value
    for dotfile in (ROOT / ".env.local", ROOT / ".env"):
        value = _load_dotenv(dotfile).get(key, "").strip()
        if value:
            return value
    return ""


def main() -> int:
    try:
        import requests
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"missing dependency: requests ({exc!r})") from exc

    project_ref = _resolve_env("SUPABASE_PROJECT_REF")
    access_token = _resolve_env("SUPABASE_ACCESS_TOKEN")
    if not project_ref or not access_token:
        raise RuntimeError("missing SUPABASE_PROJECT_REF or SUPABASE_ACCESS_TOKEN")

    resp = requests.get(
        f"https://api.supabase.com/v1/projects/{project_ref}/config/auth",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    cfg = resp.json()

    jwt_exp = int(cfg.get("jwt_exp", 0))
    if jwt_exp <= 0 or jwt_exp > 3600:
        raise RuntimeError(f"invalid jwt_exp={jwt_exp}; expected 1..3600")

    refresh_rotation = bool(cfg.get("refresh_token_rotation_enabled"))
    if not refresh_rotation:
        raise RuntimeError("refresh_token_rotation_enabled is false")

    password_min_length = int(cfg.get("password_min_length", 0))
    if password_min_length < 6:
        raise RuntimeError(f"password_min_length too low: {password_min_length}")

    print("[OK] auth security config guard passed")
    print(f" jwt_exp={jwt_exp}")
    print(f" refresh_token_rotation_enabled={refresh_rotation}")
    print(f" password_min_length={password_min_length}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
