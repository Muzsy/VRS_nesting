#!/usr/bin/env python3
"""Phase 1 P1.5-P1.9 smoke: auth config + projects/files/validation API flow."""

from __future__ import annotations

import os
import secrets
import string
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
    value = os.environ.get(key, "").strip()
    if value:
        return value
    for dotfile in (ROOT / ".env.local", ROOT / ".env"):
        value = _load_dotenv(dotfile).get(key, "").strip()
        if value:
            return value
    return ""


def _rand_email(prefix: str) -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    return f"{prefix}_{suffix}@example.com"


def main() -> int:
    try:
        import requests
        from fastapi.testclient import TestClient
        import ezdxf

        from api.main import app
        from api.services.dxf_validation import validate_dxf_file_async
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "missing runtime deps for smoke (requests/fastapi/httpx). "
            "Run from a venv where api/requirements.txt is installed. "
            f"cause={exc!r}"
        ) from exc

    project_ref = _resolve_env("SUPABASE_PROJECT_REF")
    access_token = _resolve_env("SUPABASE_ACCESS_TOKEN")
    anon_key = _resolve_env("SUPABASE_ANON_KEY")
    supabase_url = _resolve_env("SUPABASE_URL").rstrip("/")

    if not project_ref or not access_token or not anon_key or not supabase_url:
        raise RuntimeError("missing SUPABASE_PROJECT_REF/SUPABASE_ACCESS_TOKEN/SUPABASE_ANON_KEY/SUPABASE_URL")

    mgmt_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # P1.6/a-b-c: enforce + verify auth config for email/password + verification + JWT lifecycle
    auth_cfg_url = f"https://api.supabase.com/v1/projects/{project_ref}/config/auth"
    patch_payload = {
        "external_email_enabled": True,
        "mailer_autoconfirm": False,
        "jwt_exp": 3600,
        "refresh_token_rotation_enabled": True,
    }
    patch_resp = requests.patch(auth_cfg_url, headers=mgmt_headers, json=patch_payload, timeout=30)
    patch_resp.raise_for_status()

    cfg_resp = requests.get(auth_cfg_url, headers=mgmt_headers, timeout=30)
    cfg_resp.raise_for_status()
    cfg = cfg_resp.json()

    if cfg.get("external_email_enabled") is not True:
        raise RuntimeError("external_email_enabled is not true")
    if cfg.get("mailer_autoconfirm") is not False:
        raise RuntimeError("mailer_autoconfirm is not false")
    if int(cfg.get("jwt_exp", 0)) != 3600:
        raise RuntimeError("jwt_exp is not 3600")
    if cfg.get("refresh_token_rotation_enabled") is not True:
        raise RuntimeError("refresh_token_rotation_enabled is not true")

    keys_resp = requests.get(
        f"https://api.supabase.com/v1/projects/{project_ref}/api-keys?reveal=true",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    keys_resp.raise_for_status()
    service_role_key = ""
    for row in keys_resp.json():
        name = str(row.get("name", "")).lower().replace(" ", "_")
        if name == "service_role":
            service_role_key = str(row.get("api_key", ""))
            break
    if not service_role_key:
        raise RuntimeError("service role key not found via management api")

    admin_headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }

    # Temporary users for cross-user access tests.
    u1_email = _rand_email("vrsu1")
    u2_email = _rand_email("vrsu2")
    password = "CodexTmp!2345"

    auth_user_ids: list[str] = []

    def _create_admin_user(email: str) -> str:
        resp = requests.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=admin_headers,
            json={"email": email, "password": password, "email_confirm": True},
            timeout=30,
        )
        resp.raise_for_status()
        user_id = str(resp.json()["id"])
        auth_user_ids.append(user_id)
        return user_id

    def _delete_admin_user(user_id: str) -> None:
        resp = requests.delete(
            f"{supabase_url}/auth/v1/admin/users/{user_id}",
            headers=admin_headers,
            timeout=30,
        )
        if resp.status_code not in (200, 204):
            print(f"WARN: failed to delete auth user {user_id}: {resp.status_code}", file=sys.stderr)

    def _db_query(sql: str) -> list[dict[str, object]]:
        resp = requests.post(
            f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
            headers=mgmt_headers,
            json={"query": sql},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list):
            return payload
        return []

    def _wait_public_user_profile(user_id: str, timeout_sec: float = 8.0) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            rows = _db_query(f"select id from public.users where id = '{user_id}' limit 1;")
            if rows:
                return
            time.sleep(0.3)
        raise RuntimeError(f"public.users profile row not provisioned for auth user {user_id}")

    def _login(email: str) -> str:
        resp = requests.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        token = str(payload.get("access_token", "")).strip()
        if not token:
            raise RuntimeError(f"missing access_token for {email}")
        return token

    def _upload_signed_blob(upload_url: str, blob: bytes) -> None:
        last_status = 0
        last_text = ""
        for method in ("PUT", "POST"):
            resp = requests.request(
                method,
                upload_url,
                data=blob,
                headers={"Content-Type": "application/dxf"},
                timeout=30,
            )
            last_status = resp.status_code
            last_text = resp.text[:300]
            if resp.status_code in (200, 201):
                return
        raise RuntimeError(f"signed upload failed status={last_status} body={last_text}")

    def _make_valid_dxf_bytes() -> bytes:
        with tempfile.TemporaryDirectory(prefix="vrs_valid_dxf_") as tmp_dir:
            tmp_path = Path(tmp_dir) / "part.dxf"
            doc = ezdxf.new("R2010")
            msp = doc.modelspace()
            msp.add_line((0.0, 0.0), (10.0, 0.0))
            doc.saveas(tmp_path)
            return tmp_path.read_bytes()

    try:
        # P1.6/a: email/password auth flow with temporary admin-created users.
        u1_id = _create_admin_user(u1_email)
        u2_id = _create_admin_user(u2_email)
        _wait_public_user_profile(u1_id)
        _wait_public_user_profile(u2_id)

        t1 = _login(u1_email)
        t2 = _login(u2_email)

        client = TestClient(app)

        # P1.6/d + Phase 1 DoD auth protection.
        if client.get("/v1/projects").status_code != 401:
            raise RuntimeError("expected 401 without bearer token on protected endpoint")

        h1 = {"Authorization": f"Bearer {t1}"}
        h2 = {"Authorization": f"Bearer {t2}"}

        # P1.7/a-e project CRUD.
        create_resp = client.post("/v1/projects", headers=h1, json={"name": "P1", "description": "d"})
        if create_resp.status_code != 200:
            raise RuntimeError(f"POST /projects failed: {create_resp.status_code} {create_resp.text}")
        project_id = str(create_resp.json()["id"])

        if client.get("/v1/projects", headers=h1).status_code != 200:
            raise RuntimeError("GET /projects failed")
        if client.get(f"/v1/projects/{project_id}", headers=h1).status_code != 200:
            raise RuntimeError("GET /projects/:id failed")
        if client.patch(f"/v1/projects/{project_id}", headers=h1, json={"description": "updated"}).status_code != 200:
            raise RuntimeError("PATCH /projects/:id failed")
        if client.delete(f"/v1/projects/{project_id}", headers=h1).status_code != 204:
            raise RuntimeError("DELETE /projects/:id failed")

        # P1.7/f: authz failures handled (404 via RLS-hiding is accepted).
        cross_project_status = client.get(f"/v1/projects/{project_id}", headers=h2).status_code
        if cross_project_status not in (403, 404):
            raise RuntimeError(f"unexpected cross-user project status: {cross_project_status}")

        # New active project for file flow.
        files_project_resp = client.post("/v1/projects", headers=h1, json={"name": "Files", "description": ""})
        if files_project_resp.status_code != 200:
            raise RuntimeError("failed to create files project")
        files_project_id = str(files_project_resp.json()["id"])

        # P1.8/a-b upload url + direct upload contract (backend side: signed URL + key).
        upload_resp = client.post(
            f"/v1/projects/{files_project_id}/files/upload-url",
            headers=h1,
            json={
                "filename": "part.dxf",
                "content_type": "application/dxf",
                "size_bytes": 1024,
                "file_type": "part_dxf",
            },
        )
        if upload_resp.status_code != 200:
            raise RuntimeError(f"upload-url failed: {upload_resp.status_code} {upload_resp.text}")
        upload_info = upload_resp.json()

        expected_key_prefix = f"users/{u1_id}/projects/{files_project_id}/files/{upload_info['file_id']}/"
        if not str(upload_info.get("storage_key", "")).startswith(expected_key_prefix):
            raise RuntimeError("upload-url storage_key does not follow required structure")
        _upload_signed_blob(str(upload_info["upload_url"]), _make_valid_dxf_bytes())

        # P1.9/e size limit enforcement.
        oversized_resp = client.post(
            f"/v1/projects/{files_project_id}/files/upload-url",
            headers=h1,
            json={
                "filename": "huge.dxf",
                "content_type": "application/dxf",
                "size_bytes": 60 * 1024 * 1024,
                "file_type": "part_dxf",
            },
        )
        if oversized_resp.status_code != 400:
            raise RuntimeError("expected 400 on oversized upload-url")

        # P1.8/c + P1.7/f explicit 403 branch for mismatched storage key.
        wrong_key_resp = client.post(
            f"/v1/projects/{files_project_id}/files",
            headers=h1,
            json={
                "file_id": upload_info["file_id"],
                "original_filename": "part.dxf",
                "storage_key": f"users/{u2_id}/projects/{files_project_id}/files/{upload_info['file_id']}/part.dxf",
                "file_type": "part_dxf",
                "size_bytes": 1024,
                "content_hash_sha256": None,
            },
        )
        if wrong_key_resp.status_code != 403:
            raise RuntimeError(f"expected 403 for mismatched storage_key, got {wrong_key_resp.status_code}")

        complete_resp = client.post(
            f"/v1/projects/{files_project_id}/files",
            headers=h1,
            json={
                "file_id": upload_info["file_id"],
                "original_filename": "part.dxf",
                "storage_key": upload_info["storage_key"],
                "file_type": "part_dxf",
                "size_bytes": 1024,
                "content_hash_sha256": None,
            },
        )
        if complete_resp.status_code != 200:
            raise RuntimeError(f"POST /files complete failed: {complete_resp.status_code} {complete_resp.text}")

        invalid_upload_resp = client.post(
            f"/v1/projects/{files_project_id}/files/upload-url",
            headers=h1,
            json={
                "filename": "bad.dxf",
                "content_type": "application/dxf",
                "size_bytes": 512,
                "file_type": "part_dxf",
            },
        )
        if invalid_upload_resp.status_code != 200:
            raise RuntimeError("failed to create invalid upload-url")
        invalid_info = invalid_upload_resp.json()
        _upload_signed_blob(str(invalid_info["upload_url"]), b"not-a-valid-dxf")
        invalid_complete_resp = client.post(
            f"/v1/projects/{files_project_id}/files",
            headers=h1,
            json={
                "file_id": invalid_info["file_id"],
                "original_filename": "bad.dxf",
                "storage_key": invalid_info["storage_key"],
                "file_type": "part_dxf",
                "size_bytes": 512,
                "content_hash_sha256": None,
            },
        )
        if invalid_complete_resp.status_code != 200:
            raise RuntimeError("failed to insert invalid file metadata")

        # P1.8/d + P1.9/b-c-d: list exposes validation_status + validation_error for UI consumption.
        status_value = ""
        validation_error = ""
        invalid_status = ""
        invalid_validation_error = ""
        file_row_id = str(complete_resp.json().get("id", ""))
        invalid_file_row_id = str(invalid_complete_resp.json().get("id", ""))
        for _ in range(8):
            list_resp = client.get(f"/v1/projects/{files_project_id}/files", headers=h1)
            if list_resp.status_code != 200:
                raise RuntimeError("GET /files failed")
            rows = list_resp.json().get("items", [])
            target = next((row for row in rows if str(row.get("id", "")) == file_row_id), None)
            invalid_target = next((row for row in rows if str(row.get("id", "")) == invalid_file_row_id), None)
            if target:
                status_value = str(target.get("validation_status") or "")
                validation_error = str(target.get("validation_error") or "")
            if invalid_target:
                invalid_status = str(invalid_target.get("validation_status") or "")
                invalid_validation_error = str(invalid_target.get("validation_error") or "")
            if status_value in {"ok", "error"} and invalid_status in {"ok", "error"}:
                break
            time.sleep(0.5)

        if status_value != "ok":
            raise RuntimeError(f"expected API async validation_status=ok for valid dxf, got {status_value!r}")
        if invalid_status != "error":
            raise RuntimeError(f"expected API async validation_status=error for invalid dxf, got {invalid_status!r}")
        if status_value not in {"ok", "error", "pending"}:
            raise RuntimeError(f"unexpected validation status: {status_value!r}")
        if status_value == "error" and not validation_error:
            raise RuntimeError("valid dxf unexpectedly error without validation_error")
        if invalid_status == "error" and not invalid_validation_error:
            raise RuntimeError("invalid dxf status error but validation_error missing")

        # P1.9/a-b-c service-level validation checks with deterministic fake Supabase client.
        class _FakeSupabase:
            def __init__(self, blob: bytes) -> None:
                self._blob = blob
                self.updates: list[dict[str, object]] = []

            def create_signed_download_url(self, **_: object) -> dict[str, str]:
                return {"download_url": "http://fake/signed"}

            def download_signed_object(self, *, signed_url: str) -> bytes:
                _ = signed_url
                return self._blob

            def update_rows(self, **kwargs: object) -> list[dict[str, object]]:
                self.updates.append(dict(kwargs))
                return []

        fake_ok = _FakeSupabase(_make_valid_dxf_bytes())
        validate_dxf_file_async(
            supabase=fake_ok,  # type: ignore[arg-type]
            access_token="token",
            bucket="vrs-nesting",
            project_file_id="ok-file",
            storage_key="users/u/projects/p/files/f/ok.dxf",
        )
        if not fake_ok.updates:
            raise RuntimeError("missing update call for valid dxf")
        ok_payload = fake_ok.updates[-1].get("payload", {})
        if not isinstance(ok_payload, dict) or ok_payload.get("validation_status") != "ok":
            raise RuntimeError("valid dxf did not set validation_status=ok")

        fake_bad = _FakeSupabase(b"not-a-valid-dxf")
        validate_dxf_file_async(
            supabase=fake_bad,  # type: ignore[arg-type]
            access_token="token",
            bucket="vrs-nesting",
            project_file_id="bad-file",
            storage_key="users/u/projects/p/files/f/bad.dxf",
        )
        if not fake_bad.updates:
            raise RuntimeError("missing update call for invalid dxf")
        bad_payload = fake_bad.updates[-1].get("payload", {})
        if not isinstance(bad_payload, dict) or bad_payload.get("validation_status") != "error":
            raise RuntimeError("invalid dxf did not set validation_status=error")
        if not str(bad_payload.get("validation_error", "")).strip():
            raise RuntimeError("invalid dxf did not set validation_error")

        # P1.8/e delete metadata + storage object path.
        delete_file_resp = client.delete(f"/v1/projects/{files_project_id}/files/{file_row_id}", headers=h1)
        if delete_file_resp.status_code != 204:
            raise RuntimeError("DELETE /files/:id failed")
        delete_invalid_file_resp = client.delete(f"/v1/projects/{files_project_id}/files/{invalid_file_row_id}", headers=h1)
        if delete_invalid_file_resp.status_code != 204:
            raise RuntimeError("DELETE invalid /files/:id failed")

        cross_files_status = client.get(f"/v1/projects/{files_project_id}/files", headers=h2).status_code
        if cross_files_status not in (403, 404):
            raise RuntimeError(f"unexpected cross-user files status: {cross_files_status}")

        print("[OK] Phase 1 P1.5-P1.9 API/auth/projects/files/validation smoke passed")
        print(" auth_config: external_email_enabled=true, mailer_autoconfirm=false, jwt_exp=3600, refresh_rotation=true")
        print(" endpoints: projects CRUD + files upload-url/complete/list/delete + 401/403/404 checks")
        print(f" validation_status_observed: api_valid={status_value}, api_invalid={invalid_status}, service_ok=ok, service_bad=error")
        return 0
    finally:
        for user_id in auth_user_ids:
            try:
                _db_query(f"delete from public.projects where owner_id = '{user_id}';")
                _db_query(f"delete from public.users where id = '{user_id}';")
            except Exception as exc:  # noqa: BLE001
                print(f"WARN: cleanup public user failed {user_id}: {exc}", file=sys.stderr)

        for user_id in auth_user_ids:
            try:
                _delete_admin_user(user_id)
            except Exception as exc:  # noqa: BLE001
                print(f"WARN: cleanup auth user failed {user_id}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
