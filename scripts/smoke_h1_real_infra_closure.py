#!/usr/bin/env python3
"""H1 real-infra closure smoke: Supabase + RLS + storage + worker."""

from __future__ import annotations

import json
import os
import secrets
import string
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote


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


def _must_env(key: str) -> str:
    value = _resolve_env(key)
    if not value:
        raise RuntimeError(f"missing required env: {key}")
    return value


def _rand_email(prefix: str) -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    return f"{prefix}_{suffix}@example.com"


def _json_body(resp: Any) -> Any:
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return {}


def _assert_http_ok(resp: Any, *, where: str, expected: set[int]) -> None:
    if int(resp.status_code) in expected:
        return
    body = resp.text[:1200] if hasattr(resp, "text") else ""
    raise RuntimeError(f"{where} failed status={resp.status_code} body={body}")


def _db_query(*, project_ref: str, access_token: str, sql: str) -> list[dict[str, Any]]:
    import requests

    resp = requests.post(
        f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"query": sql},
        timeout=45,
    )
    _assert_http_ok(resp, where="management db query", expected={200, 201})
    payload = _json_body(resp)
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _sql_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _uuid_sql_in(values: list[str]) -> str:
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    if not cleaned:
        return "('00000000-0000-0000-0000-000000000000')"
    return "(" + ", ".join(_sql_quote(item) for item in cleaned) + ")"


def _get_service_role_key(*, project_ref: str, access_token: str) -> str:
    env_value = _resolve_env("SUPABASE_SERVICE_ROLE_KEY")
    if env_value:
        return env_value

    import requests

    resp = requests.get(
        f"https://api.supabase.com/v1/projects/{project_ref}/api-keys?reveal=true",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    _assert_http_ok(resp, where="management api-keys", expected={200})
    payload = _json_body(resp)
    if not isinstance(payload, list):
        raise RuntimeError("invalid api-keys payload")
    for row in payload:
        if not isinstance(row, dict):
            continue
        key_name = str(row.get("name", "")).strip().lower().replace(" ", "_")
        if key_name != "service_role":
            continue
        key = str(row.get("api_key", "")).strip()
        if key:
            return key
    raise RuntimeError("service_role key not found")


def _create_admin_user(*, supabase_url: str, service_role_key: str, email: str, password: str) -> str:
    import requests

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{supabase_url}/auth/v1/admin/users",
        headers=headers,
        json={"email": email, "password": password, "email_confirm": True},
        timeout=30,
    )
    _assert_http_ok(resp, where="auth admin create user", expected={200})
    user_id = str(_json_body(resp).get("id", "")).strip()
    if not user_id:
        raise RuntimeError("admin user create returned empty id")
    return user_id


def _delete_admin_user(*, supabase_url: str, service_role_key: str, user_id: str) -> None:
    import requests

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
    try:
        resp = requests.delete(f"{supabase_url}/auth/v1/admin/users/{user_id}", headers=headers, timeout=30)
        if resp.status_code not in {200, 204, 404}:
            print(f"WARN: auth user delete failed id={user_id} status={resp.status_code}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: auth user delete exception id={user_id} error={exc}", file=sys.stderr)


def _auth_sync_diag(*, project_ref: str, access_token: str) -> dict[str, Any]:
    trigger_rows = _db_query(
        project_ref=project_ref,
        access_token=access_token,
        sql=(
            "select t.tgname, n.nspname as fn_schema, p.proname as fn_name "
            "from pg_trigger t "
            "join pg_class c on c.oid = t.tgrelid "
            "join pg_namespace cn on cn.oid = c.relnamespace "
            "join pg_proc p on p.oid = t.tgfoid "
            "join pg_namespace n on n.oid = p.pronamespace "
            "where cn.nspname = 'auth' and c.relname = 'users' and not t.tgisinternal "
            "order by t.tgname;"
        ),
    )
    tables = _db_query(
        project_ref=project_ref,
        access_token=access_token,
        sql=(
            "select format('%s.%s', schemaname, tablename) as table_name "
            "from pg_tables where (schemaname='public' and tablename='users') "
            "or (schemaname='app' and tablename='profiles') "
            "order by table_name;"
        ),
    )
    return {
        "auth_users_triggers": trigger_rows,
        "profile_tables_present": [str(row.get("table_name", "")).strip() for row in tables],
    }


def _assert_required_migrations_applied(*, project_ref: str, access_token: str) -> None:
    required_versions = [
        "20260318103000",  # h1_e3_t3 security/schema bridge
        "20260321120000",  # h1_e7 closure lifecycle + storage policy extension
    ]
    missing: list[str] = []
    for version in required_versions:
        rows = _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "select version "
                "from supabase_migrations.schema_migrations "
                f"where version = {_sql_quote(version)} "
                "limit 1;"
            ),
        )
        if not rows:
            missing.append(version)
    if missing:
        raise RuntimeError(
            "target Supabase project is behind required migrations for H1 real-closure smoke. "
            f"missing_versions={missing}"
        )


def _wait_profile_row(*, project_ref: str, access_token: str, user_id: str, timeout_s: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_s
    sql = f"select id from app.profiles where id = {_sql_quote(user_id)} limit 1;"
    while time.monotonic() < deadline:
        rows = _db_query(project_ref=project_ref, access_token=access_token, sql=sql)
        if rows:
            return
        time.sleep(0.25)
    raise RuntimeError(f"profile row not created in app.profiles for user={user_id}")


def _login(*, supabase_url: str, anon_key: str, email: str, password: str) -> str:
    import requests

    resp = requests.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    _assert_http_ok(resp, where=f"auth login {email}", expected={200})
    token = str(_json_body(resp).get("access_token", "")).strip()
    if not token:
        raise RuntimeError(f"login returned empty token for email={email}")
    return token


def _split_relation(value: str, *, default_schema: str = "public") -> tuple[str, str]:
    raw = str(value or "").strip()
    if not raw:
        raise RuntimeError("empty relation name")
    if "." in raw:
        schema, relation = raw.split(".", 1)
        schema = schema.strip()
        relation = relation.strip()
        if not schema or not relation:
            raise RuntimeError(f"invalid relation name: {raw}")
        return schema, relation
    return default_schema, raw


def _postgrest_headers(
    *,
    anon_key: str,
    access_token: str,
    prefer: str | None = None,
    profile_schema: str | None = None,
) -> dict[str, str]:
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    if profile_schema:
        headers["Accept-Profile"] = profile_schema
        headers["Content-Profile"] = profile_schema
    return headers


def _postgrest_insert(
    *,
    supabase_url: str,
    anon_key: str,
    access_token: str,
    table: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    import requests

    schema, relation = _split_relation(table, default_schema="public")
    resp = requests.post(
        f"{supabase_url}/rest/v1/{relation}",
        headers=_postgrest_headers(
            anon_key=anon_key,
            access_token=access_token,
            prefer="return=representation",
            profile_schema=schema,
        ),
        data=json.dumps(payload, ensure_ascii=True),
        timeout=30,
    )
    _assert_http_ok(resp, where=f"postgrest insert {table}", expected={201})
    body = _json_body(resp)
    if not isinstance(body, list) or not body or not isinstance(body[0], dict):
        raise RuntimeError(f"postgrest insert {table} returned invalid payload")
    return body[0]


def _postgrest_select(
    *,
    supabase_url: str,
    anon_key: str,
    access_token: str,
    table: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    import requests

    schema, relation = _split_relation(table, default_schema="public")
    resp = requests.get(
        f"{supabase_url}/rest/v1/{relation}",
        headers=_postgrest_headers(anon_key=anon_key, access_token=access_token, profile_schema=schema),
        params=params,
        timeout=30,
    )
    _assert_http_ok(resp, where=f"postgrest select {table}", expected={200})
    body = _json_body(resp)
    if not isinstance(body, list):
        return []
    return [row for row in body if isinstance(row, dict)]


def _postgrest_storage_sign_status(
    *,
    supabase_url: str,
    anon_key: str,
    access_token: str,
    bucket: str,
    object_key: str,
) -> int:
    import requests

    encoded_key = quote(object_key, safe="/")
    resp = requests.post(
        f"{supabase_url}/storage/v1/object/sign/{bucket}/{encoded_key}",
        headers=_postgrest_headers(anon_key=anon_key, access_token=access_token),
        data=json.dumps({"expiresIn": 60}, ensure_ascii=True),
        timeout=30,
    )
    return int(resp.status_code)


def _make_part_dxf_bytes(*, width_mm: float, height_mm: float) -> bytes:
    import ezdxf

    with tempfile.TemporaryDirectory(prefix="h1_real_closure_dxf_") as tmp:
        path = Path(tmp) / "part.dxf"
        doc = ezdxf.new("R2010")
        if "CUT_OUTER" not in doc.layers:
            doc.layers.new(name="CUT_OUTER")
        model = doc.modelspace()
        model.add_lwpolyline(
            [(0.0, 0.0), (width_mm, 0.0), (width_mm, height_mm), (0.0, height_mm)],
            format="xy",
            dxfattribs={"layer": "CUT_OUTER", "closed": True},
        )
        doc.saveas(path)
        return path.read_bytes()


def _upload_signed_blob(*, upload_url: str, payload: bytes) -> None:
    import requests

    last_status = 0
    last_body = ""
    for method in ("PUT", "POST"):
        resp = requests.request(
            method=method,
            url=upload_url,
            data=payload,
            headers={"Content-Type": "application/dxf"},
            timeout=30,
        )
        last_status = int(resp.status_code)
        last_body = resp.text[:400]
        if last_status in {200, 201}:
            return
    raise RuntimeError(f"signed upload failed status={last_status} body={last_body}")


def _ensure_solver_bin() -> str:
    explicit = _resolve_env("VRS_SOLVER_BIN")
    if explicit and Path(explicit).is_file():
        return str(Path(explicit).resolve())

    default_path = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
    if default_path.is_file():
        return str(default_path.resolve())

    proc = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(ROOT / "rust" / "vrs_solver" / "Cargo.toml")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"cargo build vrs_solver failed: {proc.stderr[-1200:]}")
    if not default_path.is_file():
        raise RuntimeError(f"vrs_solver binary missing after build: {default_path}")
    return str(default_path.resolve())


def _worker_once(
    *,
    supabase_url: str,
    project_ref: str,
    access_token: str,
    service_role_key: str,
    solver_bin: str,
) -> tuple[int, str]:
    env = dict(os.environ)
    env.update(
        {
            "SUPABASE_URL": supabase_url,
            "SUPABASE_PROJECT_REF": project_ref,
            "SUPABASE_ACCESS_TOKEN": access_token,
            "SUPABASE_SERVICE_ROLE_KEY": service_role_key,
            "VRS_SOLVER_BIN": solver_bin,
            "API_STORAGE_BUCKET": "source-files",
            "RUN_ARTIFACTS_BUCKET": "run-artifacts",
            "WORKER_POLL_INTERVAL_S": "1",
            "WORKER_RETRY_DELAY_S": "2",
            "WORKER_TIMEOUT_EXTRA_S": "120",
        }
    )
    proc = subprocess.run(
        [sys.executable, "-m", "worker.main", "--once"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    return int(proc.returncode), combined


def _cleanup(
    *,
    project_ref: str,
    access_token: str,
    supabase_url: str,
    service_role_key: str,
    owner_user_ids: list[str],
    project_ids: list[str],
    run_ids: list[str],
    auth_user_ids: list[str],
) -> None:
    try:
        owner_in = _uuid_sql_in(owner_user_ids)
        project_in = _uuid_sql_in(project_ids)
        run_in = _uuid_sql_in(run_ids)

        # Run-scoped cleanup first.
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.run_artifacts where run_id in {run_in};")
        _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "delete from app.run_layout_placements "
                f"where sheet_id in (select id from app.run_layout_sheets where run_id in {run_in});"
            ),
        )
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.run_layout_sheets where run_id in {run_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.run_layout_unplaced where run_id in {run_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.run_metrics where run_id in {run_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.run_logs where run_id in {run_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.run_queue where run_id in {run_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.nesting_run_snapshots where run_id in {run_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.nesting_runs where id in {run_in};")

        # Project-scoped cleanup.
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.project_part_requirements where project_id in {project_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.project_sheet_inputs where project_id in {project_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.project_technology_setups where project_id in {project_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.project_settings where project_id in {project_in};")

        # Part/sheet domain cleanup before geometry revisions to avoid FK/check conflicts.
        _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "delete from app.part_revisions "
                f"where part_definition_id in (select id from app.part_definitions where owner_user_id in {owner_in});"
            ),
        )
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.part_definitions where owner_user_id in {owner_in};")
        _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "delete from app.sheet_revisions "
                f"where sheet_definition_id in (select id from app.sheet_definitions where owner_user_id in {owner_in});"
            ),
        )
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.sheet_definitions where owner_user_id in {owner_in};")

        _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "delete from app.geometry_derivatives "
                f"where geometry_revision_id in (select id from app.geometry_revisions where project_id in {project_in});"
            ),
        )
        _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "delete from app.geometry_validation_reports "
                f"where geometry_revision_id in (select id from app.geometry_revisions where project_id in {project_in});"
            ),
        )
        _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "delete from app.geometry_review_actions "
                f"where geometry_revision_id in (select id from app.geometry_revisions where project_id in {project_in});"
            ),
        )
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.geometry_revisions where project_id in {project_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.file_objects where project_id in {project_in};")
        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.projects where id in {project_in};")

        _db_query(project_ref=project_ref, access_token=access_token, sql=f"delete from app.user_run_quota_monthly_usage where user_id in {owner_in};")
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: cleanup SQL failed: {exc}", file=sys.stderr)

    for user_id in auth_user_ids:
        _delete_admin_user(supabase_url=supabase_url, service_role_key=service_role_key, user_id=user_id)


def main() -> int:
    try:
        import requests  # noqa: F401
        from fastapi.testclient import TestClient
        from api.main import app
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "missing runtime deps (requests/fastapi/httpx). "
            f"cause={exc!r}"
        ) from exc

    project_ref = _must_env("SUPABASE_PROJECT_REF")
    access_token = _must_env("SUPABASE_ACCESS_TOKEN")
    anon_key = _must_env("SUPABASE_ANON_KEY")
    supabase_url = _must_env("SUPABASE_URL").rstrip("/")
    service_role_key = _get_service_role_key(project_ref=project_ref, access_token=access_token)

    _assert_required_migrations_applied(project_ref=project_ref, access_token=access_token)

    created_auth_user_ids: list[str] = []
    created_owner_user_ids: list[str] = []
    created_project_ids: list[str] = []
    created_run_ids: list[str] = []

    password = "CodexTmp!2345"
    user1_email = _rand_email("h1realu1")
    user2_email = _rand_email("h1realu2")

    client = TestClient(app)

    try:
        try:
            user1_id = _create_admin_user(
                supabase_url=supabase_url,
                service_role_key=service_role_key,
                email=user1_email,
                password=password,
            )
            user2_id = _create_admin_user(
                supabase_url=supabase_url,
                service_role_key=service_role_key,
                email=user2_email,
                password=password,
            )
        except Exception as exc:  # noqa: BLE001
            diag = _auth_sync_diag(project_ref=project_ref, access_token=access_token)
            raise RuntimeError(
                "cannot create temporary auth users for closure smoke; "
                "check auth.users profile-sync trigger wiring and profile table state. "
                f"diag={json.dumps(diag, ensure_ascii=False, sort_keys=True)}"
            ) from exc
        created_auth_user_ids.extend([user1_id, user2_id])
        created_owner_user_ids.extend([user1_id, user2_id])

        _wait_profile_row(project_ref=project_ref, access_token=access_token, user_id=user1_id)
        _wait_profile_row(project_ref=project_ref, access_token=access_token, user_id=user2_id)

        token1 = _login(supabase_url=supabase_url, anon_key=anon_key, email=user1_email, password=password)
        token2 = _login(supabase_url=supabase_url, anon_key=anon_key, email=user2_email, password=password)
        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        create_project_resp = client.post("/v1/projects", headers=h1, json={"name": "H1 Real Infra Closure", "description": "closure smoke"})
        _assert_http_ok(create_project_resp, where="POST /v1/projects", expected={200})
        project_id = str(_json_body(create_project_resp).get("id", "")).strip()
        if not project_id:
            raise RuntimeError("project create returned empty id")
        created_project_ids.append(project_id)

        # User-JWT insert to keep RLS evidence on technology setup creation.
        tech_row = _postgrest_insert(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            table="app.project_technology_setups",
            payload={
                "project_id": project_id,
                "display_name": "H1 real closure tech",
                "lifecycle": "approved",
                "is_default": True,
                "machine_code": "M-REAL",
                "material_code": "STEEL-S235",
                "thickness_mm": 2.0,
                "kerf_mm": 0.2,
                "spacing_mm": 1.0,
                "margin_mm": 0.0,
                "rotation_step_deg": 90,
                "allow_free_rotation": False,
                "notes": "smoke_h1_real_infra_closure",
            },
        )
        if str(tech_row.get("lifecycle", "")).strip().lower() != "approved":
            raise RuntimeError("technology setup insert did not persist approved lifecycle")

        part_blob = _make_part_dxf_bytes(width_mm=0.12, height_mm=0.08)

        upload_url_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=h1,
            json={
                "filename": "part_source.dxf",
                "content_type": "application/dxf",
                "size_bytes": len(part_blob),
                "file_kind": "source_dxf",
            },
        )
        _assert_http_ok(upload_url_resp, where="POST /files/upload-url", expected={200})
        upload_info = _json_body(upload_url_resp)
        file_id = str(upload_info.get("file_id", "")).strip()
        storage_path = str(upload_info.get("storage_path", "")).strip()
        upload_url = str(upload_info.get("upload_url", "")).strip()
        if not file_id or not storage_path or not upload_url:
            raise RuntimeError("upload-url payload missing required fields")
        _upload_signed_blob(upload_url=upload_url, payload=part_blob)

        complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=h1,
            json={
                "file_id": file_id,
                "storage_path": storage_path,
                "file_kind": "source_dxf",
            },
        )
        _assert_http_ok(complete_resp, where="POST /files complete", expected={200})

        geometry_revision_id = ""
        deadline = time.monotonic() + 45.0
        while time.monotonic() < deadline:
            revisions = _postgrest_select(
                supabase_url=supabase_url,
                anon_key=anon_key,
                access_token=token1,
                table="app.geometry_revisions",
                params={
                    "select": "id,status",
                    "project_id": f"eq.{project_id}",
                    "source_file_object_id": f"eq.{file_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            if not revisions:
                time.sleep(0.5)
                continue
            row = revisions[0]
            geometry_revision_id = str(row.get("id", "")).strip()
            status_raw = str(row.get("status", "")).strip().lower()
            if status_raw == "validated":
                break
            if status_raw == "rejected":
                raise RuntimeError("geometry revision rejected during import")
            time.sleep(0.5)
        if not geometry_revision_id:
            raise RuntimeError("geometry revision not found for uploaded source_dxf")

        derivative_deadline = time.monotonic() + 30.0
        while time.monotonic() < derivative_deadline:
            derivatives = _postgrest_select(
                supabase_url=supabase_url,
                anon_key=anon_key,
                access_token=token1,
                table="app.geometry_derivatives",
                params={
                    "select": "id,derivative_kind",
                    "geometry_revision_id": f"eq.{geometry_revision_id}",
                },
            )
            kinds = {str(row.get("derivative_kind", "")).strip().lower() for row in derivatives}
            if {"nesting_canonical", "viewer_outline"}.issubset(kinds):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("required geometry derivatives not ready (nesting_canonical + viewer_outline)")

        part_resp = client.post(
            f"/v1/projects/{project_id}/parts",
            headers=h1,
            json={
                "code": "H1-REAL-PART-001",
                "name": "H1 Real Part 001",
                "geometry_revision_id": geometry_revision_id,
            },
        )
        _assert_http_ok(part_resp, where="POST /parts", expected={201})
        part_revision_id = str(_json_body(part_resp).get("part_revision_id", "")).strip()
        if not part_revision_id:
            raise RuntimeError("part creation returned empty part_revision_id")

        sheet_resp = client.post(
            "/v1/sheets",
            headers=h1,
            json={
                "code": "H1-REAL-SHEET-001",
                "name": "H1 Real Sheet 001",
                "width_mm": 500.0,
                "height_mm": 300.0,
            },
        )
        _assert_http_ok(sheet_resp, where="POST /sheets", expected={201})
        sheet_revision_id = str(_json_body(sheet_resp).get("sheet_revision_id", "")).strip()
        if not sheet_revision_id:
            raise RuntimeError("sheet creation returned empty sheet_revision_id")

        req_resp = client.post(
            f"/v1/projects/{project_id}/part-requirements",
            headers=h1,
            json={
                "part_revision_id": part_revision_id,
                "required_qty": 2,
                "placement_priority": 10,
                "placement_policy": "normal",
                "is_active": True,
            },
        )
        _assert_http_ok(req_resp, where="POST /part-requirements", expected={201})

        sheet_input_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            headers=h1,
            json={
                "sheet_revision_id": sheet_revision_id,
                "required_qty": 1,
                "is_active": True,
                "is_default": True,
                "placement_priority": 5,
            },
        )
        _assert_http_ok(sheet_input_resp, where="POST /sheet-inputs", expected={201})

        run_resp = client.post(
            f"/v1/projects/{project_id}/runs",
            headers=h1,
            json={},
        )
        _assert_http_ok(run_resp, where="POST /runs", expected={200})
        run_payload = _json_body(run_resp)
        run_id = str(run_payload.get("id", "")).strip()
        if not run_id:
            raise RuntimeError("run creation returned empty id")
        created_run_ids.append(run_id)
        if str(run_payload.get("status", "")).strip().lower() != "queued":
            raise RuntimeError("new run status must be queued")

        snapshot_rows = _postgrest_select(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            table="app.nesting_run_snapshots",
            params={
                "select": "run_id,status",
                "run_id": f"eq.{run_id}",
                "limit": "1",
            },
        )
        if not snapshot_rows:
            raise RuntimeError("missing app.nesting_run_snapshots row")
        snapshot_status = str(snapshot_rows[0].get("status", "")).strip().lower()
        if snapshot_status != "ready":
            raise RuntimeError(f"snapshot status must be ready, got={snapshot_status}")

        solver_bin = _ensure_solver_bin()

        timeline: list[str] = []
        initial_status = str(_json_body(client.get(f"/v1/projects/{project_id}/runs/{run_id}", headers=h1)).get("status", "")).strip().lower()
        if initial_status:
            timeline.append(initial_status)

        terminal = {"done", "failed", "cancelled"}
        worker_logs: list[str] = []
        final_status = initial_status

        for _ in range(8):
            rc, worker_log = _worker_once(
                supabase_url=supabase_url,
                project_ref=project_ref,
                access_token=access_token,
                service_role_key=service_role_key,
                solver_bin=solver_bin,
            )
            worker_logs.append(worker_log[-1200:])
            if rc != 0:
                raise RuntimeError(f"worker --once failed rc={rc}\n{worker_log[-1200:]}")

            for _ in range(30):
                status_resp = client.get(f"/v1/projects/{project_id}/runs/{run_id}", headers=h1)
                _assert_http_ok(status_resp, where="GET /runs/{run_id}", expected={200})
                status_value = str(_json_body(status_resp).get("status", "")).strip().lower()
                if status_value and (not timeline or timeline[-1] != status_value):
                    timeline.append(status_value)
                final_status = status_value
                if final_status in terminal:
                    break
                time.sleep(0.2)
            if final_status in terminal:
                break

        if final_status != "done":
            raise RuntimeError(
                "run did not reach done state "
                f"(final={final_status}, timeline={timeline}, worker_tail={worker_logs[-1] if worker_logs else ''})"
            )

        run_details_resp = client.get(f"/v1/projects/{project_id}/runs/{run_id}", headers=h1)
        _assert_http_ok(run_details_resp, where="GET /runs/{run_id} final", expected={200})
        run_details = _json_body(run_details_resp)
        if not str(run_details.get("started_at", "")).strip() or not str(run_details.get("finished_at", "")).strip():
            raise RuntimeError("run started_at/finished_at must be populated in terminal state")
        if "queued" not in timeline:
            raise RuntimeError(f"queued status missing from timeline: {timeline}")
        if timeline[-1] != "done":
            raise RuntimeError(f"timeline terminal status mismatch: {timeline}")

        layout_sheets = _postgrest_select(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            table="app.run_layout_sheets",
            params={"select": "id", "run_id": f"eq.{run_id}"},
        )
        unplaced_rows = _postgrest_select(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            table="app.run_layout_unplaced",
            params={"select": "part_revision_id", "run_id": f"eq.{run_id}"},
        )
        if not layout_sheets and not unplaced_rows:
            raise RuntimeError("projection tables empty: neither run_layout_sheets nor run_layout_unplaced has rows")

        metrics_rows = _postgrest_select(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            table="app.run_metrics",
            params={"select": "run_id", "run_id": f"eq.{run_id}", "limit": "1"},
        )
        if not metrics_rows:
            raise RuntimeError("app.run_metrics row missing for run")

        artifact_rows = _postgrest_select(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            table="app.run_artifacts",
            params={
                "select": "id,artifact_kind,storage_bucket,storage_path",
                "run_id": f"eq.{run_id}",
                "order": "created_at.asc",
            },
        )
        if not artifact_rows:
            raise RuntimeError("app.run_artifacts empty for done run")

        kinds = {str(row.get("artifact_kind", "")).strip() for row in artifact_rows}
        for required_kind in ("solver_output", "log"):
            if required_kind not in kinds:
                raise RuntimeError(f"missing artifact_kind={required_kind}, got={sorted(kinds)}")
        for row in artifact_rows:
            if str(row.get("storage_bucket", "")).strip() != "run-artifacts":
                raise RuntimeError("run artifact storage_bucket must be run-artifacts")

        has_sheet_svg = "sheet_svg" in kinds
        has_sheet_dxf = "sheet_dxf" in kinds

        artifacts_api_resp = client.get(f"/v1/projects/{project_id}/runs/{run_id}/artifacts", headers=h1)
        _assert_http_ok(artifacts_api_resp, where="GET /runs/{run_id}/artifacts", expected={200})
        artifact_items = _json_body(artifacts_api_resp).get("items", [])
        if not isinstance(artifact_items, list) or not artifact_items:
            raise RuntimeError("artifact list endpoint returned empty items")

        api_types = {str(item.get("artifact_type", "")).strip() for item in artifact_items if isinstance(item, dict)}
        if "solver_output" not in api_types:
            raise RuntimeError(f"artifact API types missing solver_output: {sorted(api_types)}")
        if not ({"run_log", "solver_stdout", "solver_stderr", "runner_meta"} & api_types):
            raise RuntimeError(f"artifact API log family missing: {sorted(api_types)}")

        viewer_resp = client.get(f"/v1/projects/{project_id}/runs/{run_id}/viewer-data", headers=h1)
        _assert_http_ok(viewer_resp, where="GET /viewer-data", expected={200})
        viewer_json = _json_body(viewer_resp)
        if int(viewer_json.get("sheet_count", 0)) < 0:
            raise RuntimeError("viewer-data sheet_count must be >= 0")

        log_resp = client.get(f"/v1/projects/{project_id}/runs/{run_id}/log?offset=0&lines=200", headers=h1)
        _assert_http_ok(log_resp, where="GET /log", expected={200})
        log_json = _json_body(log_resp)
        if int(log_json.get("total_lines", 0)) <= 0:
            raise RuntimeError("run log endpoint returned no lines")

        artifact_id = ""
        artifact_storage_key = ""
        for row in artifact_rows:
            if str(row.get("artifact_kind", "")).strip() == "solver_output":
                artifact_id = str(row.get("id", "")).strip()
                artifact_storage_key = str(row.get("storage_path", "")).strip()
                break
        if not artifact_id or not artifact_storage_key:
            raise RuntimeError("cannot select solver_output artifact for cross-tenant checks")

        # API cross-tenant negatives.
        for path in (
            f"/v1/projects/{project_id}/runs/{run_id}",
            f"/v1/projects/{project_id}/runs/{run_id}/artifacts",
            f"/v1/projects/{project_id}/runs/{run_id}/log?offset=0&lines=20",
            f"/v1/projects/{project_id}/runs/{run_id}/viewer-data",
            f"/v1/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/url",
        ):
            resp = client.get(path, headers=h2)
            if resp.status_code not in {403, 404}:
                raise RuntimeError(f"cross-tenant API access should fail for {path}, got={resp.status_code}")

        # Storage-level cross-tenant negative on run-artifacts object.
        owner_sign_status = _postgrest_storage_sign_status(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token1,
            bucket="run-artifacts",
            object_key=artifact_storage_key,
        )
        if owner_sign_status != 200:
            raise RuntimeError(f"owner storage sign should pass for run-artifacts, got={owner_sign_status}")

        other_sign_status = _postgrest_storage_sign_status(
            supabase_url=supabase_url,
            anon_key=anon_key,
            access_token=token2,
            bucket="run-artifacts",
            object_key=artifact_storage_key,
        )
        if other_sign_status < 400:
            raise RuntimeError(f"cross-tenant storage sign should fail, got={other_sign_status}")

        # Bucket and policy presence checks (geometry-artifacts stays advisory for E2 flow).
        bucket_rows = _db_query(
            project_ref=project_ref,
            access_token=access_token,
            sql=(
                "select id, public from storage.buckets "
                "where id in ('source-files','run-artifacts','geometry-artifacts') "
                "order by id;"
            ),
        )
        bucket_by_id = {str(row.get("id", "")).strip(): row for row in bucket_rows}
        for bucket_id in ("run-artifacts", "geometry-artifacts"):
            row = bucket_by_id.get(bucket_id)
            if row is None:
                raise RuntimeError(f"missing storage bucket: {bucket_id}")
            if str(row.get("public", "")).strip().lower() not in {"false", "f"}:
                raise RuntimeError(f"bucket must be private: {bucket_id}")

        for bucket_id in ("run-artifacts", "geometry-artifacts"):
            policy_rows = _db_query(
                project_ref=project_ref,
                access_token=access_token,
                sql=(
                    "select count(*)::int as cnt "
                    "from pg_policies "
                    "where schemaname='storage' and tablename='objects' "
                    f"and (coalesce(qual,'') || ' ' || coalesce(with_check,'')) ilike '%{bucket_id}%';"
                ),
            )
            count = int(policy_rows[0].get("cnt", 0) if policy_rows else 0)
            if count <= 0:
                raise RuntimeError(f"storage policy expression missing bucket reference: {bucket_id}")

        summary = {
            "project_id": project_id,
            "run_id": run_id,
            "timeline": timeline,
            "artifact_kinds": sorted(kinds),
            "artifact_api_types": sorted(api_types),
            "layout_sheets_count": len(layout_sheets),
            "layout_unplaced_count": len(unplaced_rows),
            "sheet_svg_present": has_sheet_svg,
            "sheet_dxf_present": has_sheet_dxf,
            "owner_storage_sign_status": owner_sign_status,
            "other_storage_sign_status": other_sign_status,
            "bucket_ids": sorted(bucket_by_id.keys()),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        print("PASS: H1 real infra closure smoke")
        return 0
    finally:
        _cleanup(
            project_ref=project_ref,
            access_token=access_token,
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            owner_user_ids=created_owner_user_ids,
            project_ids=created_project_ids,
            run_ids=created_run_ids,
            auth_user_ids=created_auth_user_ids,
        )


if __name__ == "__main__":
    raise SystemExit(main())
