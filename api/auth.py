from __future__ import annotations

import logging

from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.deps import get_supabase_client
from api.supabase_client import SupabaseClient, SupabaseHTTPError


bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger("vrs_api.auth")


class AuthenticatedUser(BaseModel):
    id: str
    email: str | None = None
    access_token: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="empty bearer token")

    try:
        user_payload = supabase.get_auth_user(token)
    except SupabaseHTTPError as exc:
        logger.warning("auth_invalid_token error=%s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    user_id = str(user_payload.get("id", "")).strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing user id in token payload")

    return AuthenticatedUser(id=user_id, email=user_payload.get("email"), access_token=token)
