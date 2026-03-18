from __future__ import annotations

import logging
from typing import NoReturn

from fastapi import HTTPException, status

from api.supabase_client import SupabaseHTTPError


logger = logging.getLogger("vrs_api.supabase")


def raise_supabase_http_error(
    *,
    operation: str,
    exc: SupabaseHTTPError,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> NoReturn:
    logger.warning("supabase_http_error operation=%s error=%s", operation, exc)
    raise HTTPException(status_code=status_code, detail=f"{operation} failed") from exc
