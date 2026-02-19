from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from api.supabase_client import SupabaseClient, SupabaseHTTPError


logger = logging.getLogger("vrs_api.rate_limit")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _retry_after_seconds(*, now: datetime, oldest_seen: datetime | None, window_seconds: int) -> int:
    if oldest_seen is None:
        return max(1, window_seconds)
    elapsed = (now - oldest_seen).total_seconds()
    remaining = int(window_seconds - elapsed)
    return max(1, remaining)


def enforce_user_rate_limit(
    *,
    supabase: SupabaseClient,
    access_token: str,
    user_id: str,
    table: str,
    timestamp_field: str,
    limit: int,
    window_seconds: int,
    route_key: str,
    filters: dict[str, str] | None = None,
) -> None:
    if limit <= 0:
        return

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)
    params = {
        "select": f"id,{timestamp_field}",
        "order": f"{timestamp_field}.asc",
        "limit": str(limit + 1),
        timestamp_field: f"gte.{cutoff.isoformat()}",
    }
    if filters:
        params.update(filters)

    try:
        rows = supabase.select_rows(table=table, access_token=access_token, params=params)
    except SupabaseHTTPError as exc:
        logger.error("rate_limit_backend_error route=%s user_id=%s table=%s error=%s", route_key, user_id, table, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "rate_limit_backend_unavailable",
                "message": "rate limit check backend unavailable",
                "route": route_key,
            },
        ) from exc

    if len(rows) < limit:
        return

    oldest_seen = _parse_timestamp(rows[0].get(timestamp_field)) if rows else None
    retry_after = _retry_after_seconds(now=now, oldest_seen=oldest_seen, window_seconds=window_seconds)
    logger.warning(
        "rate_limit_hit route=%s user_id=%s table=%s count=%s limit=%s window_s=%s retry_after=%s",
        route_key,
        user_id,
        table,
        len(rows),
        limit,
        window_seconds,
        retry_after,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "rate_limited",
            "message": f"rate limit exceeded for {route_key}",
            "route": route_key,
            "limit": limit,
            "window_seconds": window_seconds,
        },
        headers={"Retry-After": str(retry_after)},
    )
