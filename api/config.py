from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _resolve_env(key: str, default: str = "") -> str:
    process_value = os.environ.get(key)
    if process_value is not None and process_value.strip():
        return process_value.strip()

    root = Path(__file__).resolve().parents[1]
    for candidate in (root / ".env.local", root / ".env"):
        values = _parse_dotenv(candidate)
        value = values.get(key, "").strip()
        if value:
            return value

    return default


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_anon_key: str
    supabase_project_ref: str
    supabase_db_password: str
    database_url: str
    storage_bucket: str
    max_dxf_size_mb: int
    rate_limit_window_s: int
    rate_limit_runs_per_window: int
    rate_limit_bundles_per_window: int
    rate_limit_upload_urls_per_window: int
    signed_url_ttl_s: int
    enable_security_headers: bool
    allowed_origins: tuple[str, ...]

    @property
    def max_dxf_size_bytes(self) -> int:
        return self.max_dxf_size_mb * 1024 * 1024


class SettingsError(RuntimeError):
    pass


def load_settings() -> Settings:
    supabase_url = _resolve_env("SUPABASE_URL")
    supabase_anon_key = _resolve_env("SUPABASE_ANON_KEY")

    if not supabase_url:
        raise SettingsError("missing SUPABASE_URL")
    if not supabase_anon_key:
        raise SettingsError("missing SUPABASE_ANON_KEY")

    origins_raw = _resolve_env("API_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    origins = tuple(origin.strip() for origin in origins_raw.split(",") if origin.strip())
    if not origins:
        origins = ("http://localhost:5173",)

    max_dxf_size_mb_raw = _resolve_env("API_MAX_DXF_SIZE_MB", "50")
    try:
        max_dxf_size_mb = int(max_dxf_size_mb_raw)
    except ValueError as exc:
        raise SettingsError(f"invalid API_MAX_DXF_SIZE_MB: {max_dxf_size_mb_raw!r}") from exc
    if max_dxf_size_mb <= 0:
        raise SettingsError("API_MAX_DXF_SIZE_MB must be positive")

    rate_limit_window_raw = _resolve_env("API_RATE_LIMIT_WINDOW_S", "60")
    try:
        rate_limit_window_s = int(rate_limit_window_raw)
    except ValueError as exc:
        raise SettingsError(f"invalid API_RATE_LIMIT_WINDOW_S: {rate_limit_window_raw!r}") from exc
    if rate_limit_window_s <= 0:
        raise SettingsError("API_RATE_LIMIT_WINDOW_S must be positive")

    runs_limit_raw = _resolve_env("API_RATE_LIMIT_RUNS_PER_WINDOW", "10")
    bundles_limit_raw = _resolve_env("API_RATE_LIMIT_BUNDLES_PER_WINDOW", "4")
    upload_limit_raw = _resolve_env("API_RATE_LIMIT_UPLOAD_URLS_PER_WINDOW", "10")
    try:
        runs_limit = int(runs_limit_raw)
        bundles_limit = int(bundles_limit_raw)
        upload_limit = int(upload_limit_raw)
    except ValueError as exc:
        raise SettingsError("rate limit env vars must be integers") from exc
    if runs_limit < 0 or bundles_limit < 0 or upload_limit < 0:
        raise SettingsError("rate limit values cannot be negative")

    signed_url_ttl_raw = _resolve_env("API_SIGNED_URL_TTL_S", "300")
    try:
        signed_url_ttl_s = int(signed_url_ttl_raw)
    except ValueError as exc:
        raise SettingsError(f"invalid API_SIGNED_URL_TTL_S: {signed_url_ttl_raw!r}") from exc
    if signed_url_ttl_s <= 0:
        raise SettingsError("API_SIGNED_URL_TTL_S must be positive")

    security_headers_raw = _resolve_env("API_ENABLE_SECURITY_HEADERS", "1").strip().lower()
    enable_security_headers = security_headers_raw not in {"0", "false", "no", "off"}
    storage_bucket = _resolve_env("API_STORAGE_BUCKET", "source-files").strip()
    if not storage_bucket:
        raise SettingsError("API_STORAGE_BUCKET cannot be empty")

    return Settings(
        supabase_url=supabase_url.rstrip("/"),
        supabase_anon_key=supabase_anon_key,
        supabase_project_ref=_resolve_env("SUPABASE_PROJECT_REF"),
        supabase_db_password=_resolve_env("SUPABASE_DB_PASSWORD"),
        database_url=_resolve_env("DATABASE_URL"),
        storage_bucket=storage_bucket,
        max_dxf_size_mb=max_dxf_size_mb,
        rate_limit_window_s=rate_limit_window_s,
        rate_limit_runs_per_window=runs_limit,
        rate_limit_bundles_per_window=bundles_limit,
        rate_limit_upload_urls_per_window=upload_limit,
        signed_url_ttl_s=signed_url_ttl_s,
        enable_security_headers=enable_security_headers,
        allowed_origins=origins,
    )
