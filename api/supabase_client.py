from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class SupabaseHTTPError(RuntimeError):
    pass


class SupabaseClient:
    def __init__(self, *, base_url: str, anon_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._anon_key = anon_key

    @property
    def base_url(self) -> str:
        return self._base_url

    def _build_url(self, path: str, *, params: dict[str, str] | None = None) -> str:
        cleaned = path if path.startswith("/") else f"/{path}"
        url = f"{self._base_url}{cleaned}"
        if params:
            query = urlencode(params, doseq=True, safe=",:*()")
            url = f"{url}?{query}"
        return url

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | list[Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        url = self._build_url(path, params=params)
        headers = {
            "apikey": self._anon_key,
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        data: bytes | None = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if prefer:
            headers["Prefer"] = prefer

        req = Request(url=url, method=method.upper(), headers=headers, data=data)

        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                if not body.strip():
                    return None
                return json.loads(body)
        except HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise SupabaseHTTPError(f"{method} {path} -> {exc.code}: {err_body}") from exc
        except URLError as exc:
            raise SupabaseHTTPError(f"{method} {path} network error: {exc}") from exc

    def _request_bytes(self, method: str, absolute_url: str) -> bytes:
        req = Request(url=absolute_url, method=method.upper())
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.read()
        except HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise SupabaseHTTPError(f"{method} {absolute_url} -> {exc.code}: {err_body}") from exc
        except URLError as exc:
            raise SupabaseHTTPError(f"{method} {absolute_url} network error: {exc}") from exc

    def _storage_signed_absolute_url(self, signed_path: str) -> str:
        if signed_path.startswith("http://") or signed_path.startswith("https://"):
            return signed_path

        normalized = signed_path if signed_path.startswith("/") else f"/{signed_path}"
        if normalized.startswith("/storage/v1/"):
            return f"{self._base_url}{normalized}"
        if normalized.startswith("/object/"):
            return f"{self._base_url}/storage/v1{normalized}"
        return f"{self._base_url}{normalized}"

    def get_auth_user(self, access_token: str) -> dict[str, Any]:
        payload = self._request_json("GET", "/auth/v1/user", token=access_token)
        if not isinstance(payload, dict):
            raise SupabaseHTTPError("auth user response is not object")
        return payload

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        payload = self._request_json("GET", f"/rest/v1/{table}", token=access_token, params=params)
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise SupabaseHTTPError(f"select_rows expected list response for table={table}")
        return [item for item in payload if isinstance(item, dict)]

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request_json(
            "POST",
            f"/rest/v1/{table}",
            token=access_token,
            payload=payload,
            prefer="return=representation",
        )
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows[0]
        raise SupabaseHTTPError(f"insert_row expected non-empty representation for table={table}")

    def update_rows(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        rows = self._request_json(
            "PATCH",
            f"/rest/v1/{table}",
            token=access_token,
            params=filters,
            payload=payload,
            prefer="return=representation",
        )
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise SupabaseHTTPError(f"update_rows expected list representation for table={table}")
        return [item for item in rows if isinstance(item, dict)]

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self._request_json(
            "DELETE",
            f"/rest/v1/{table}",
            token=access_token,
            params=filters,
            prefer="return=minimal",
        )

    def create_signed_upload_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int = 300,
    ) -> dict[str, Any]:
        encoded_key = quote(object_key, safe="/")
        payload = self._request_json(
            "POST",
            f"/storage/v1/object/upload/sign/{bucket}/{encoded_key}",
            token=access_token,
            payload={"expiresIn": expires_in},
        )
        if not isinstance(payload, dict):
            raise SupabaseHTTPError("signed upload response is not object")

        signed_path = str(payload.get("signedURL") or payload.get("signedUrl") or payload.get("url") or "").strip()
        upload_token = str(payload.get("token", "")).strip()

        upload_url = ""
        if signed_path:
            upload_url = self._storage_signed_absolute_url(signed_path)
        elif upload_token:
            upload_url = f"{self._base_url}/storage/v1/object/upload/sign/{bucket}/{encoded_key}?token={upload_token}"

        if not upload_url:
            raise SupabaseHTTPError("signed upload url missing in response")

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return {
            "upload_url": upload_url,
            "expires_at": expires_at.isoformat(),
        }

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int = 900,
    ) -> dict[str, Any]:
        encoded_key = quote(object_key, safe="/")
        payload = self._request_json(
            "POST",
            f"/storage/v1/object/sign/{bucket}/{encoded_key}",
            token=access_token,
            payload={"expiresIn": expires_in},
        )
        if not isinstance(payload, dict):
            raise SupabaseHTTPError("signed download response is not object")

        signed_path = str(payload.get("signedURL") or payload.get("signedUrl") or payload.get("url") or "").strip()
        if not signed_path:
            raise SupabaseHTTPError("signed download url missing in response")

        download_url = self._storage_signed_absolute_url(signed_path)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return {
            "download_url": download_url,
            "expires_at": expires_at.isoformat(),
        }

    def download_signed_object(self, *, signed_url: str) -> bytes:
        return self._request_bytes("GET", signed_url)

    def upload_signed_object(
        self,
        *,
        signed_url: str,
        payload: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        last_error: SupabaseHTTPError | None = None
        for method in ("PUT", "POST"):
            req = Request(url=signed_url, method=method, data=payload)
            req.add_header("Content-Type", content_type)
            try:
                with urlopen(req, timeout=60):
                    return
            except HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="replace")
                last_error = SupabaseHTTPError(f"{method} {signed_url} -> {exc.code}: {err_body}")
                continue
            except URLError as exc:
                last_error = SupabaseHTTPError(f"{method} {signed_url} network error: {exc}")
                continue
        if last_error is not None:
            raise last_error
        raise SupabaseHTTPError("upload_signed_object failed with unknown error")

    def remove_object(self, *, access_token: str, bucket: str, object_key: str) -> None:
        encoded_key = quote(object_key, safe="/")
        self._request_json(
            "DELETE",
            f"/storage/v1/object/{bucket}/{encoded_key}",
            token=access_token,
        )
