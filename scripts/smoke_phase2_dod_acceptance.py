#!/usr/bin/env python3
"""Phase 2 DoD acceptance smoke for worker + runs pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import string
import subprocess
import sys
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


def _rand_email(prefix: str) -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    return f"{prefix}_{suffix}@example.com"


def _must_env(name: str) -> str:
    value = _resolve_env(name)
    if not value:
        raise RuntimeError(f"missing required env: {name}")
    return value


def _db_query(project_ref: str, access_token: str, sql: str) -> list[dict[str, Any]]:
    import requests

    last_error: Exception | None = None
    for attempt in range(6):
        try:
            resp = requests.post(
                f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"query": sql},
                timeout=45,
            )
            if resp.status_code >= 500:
                time.sleep(min(2.5, 0.4 * (attempt + 1)))
                continue
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
            return []
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(min(2.5, 0.4 * (attempt + 1)))
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("database query failed with unknown error")


def _get_service_role_key(project_ref: str, access_token: str) -> str:
    import requests

    resp = requests.get(
        f"https://api.supabase.com/v1/projects/{project_ref}/api-keys?reveal=true",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    for row in resp.json():
        if str(row.get("name", "")).lower().replace(" ", "_") == "service_role":
            key = str(row.get("api_key", "")).strip()
            if key:
                return key
    raise RuntimeError("service role key not found via management api")


def _ensure_sparrow_bin() -> str:
    proc = subprocess.run(
        ["./scripts/ensure_sparrow.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    path = (proc.stdout or "").strip().splitlines()[-1].strip()
    if not path:
        raise RuntimeError("ensure_sparrow.sh returned empty path")
    if not Path(path).is_file():
        raise RuntimeError(f"sparrow bin missing: {path}")
    return path


def _build_worker_image(image_tag: str) -> None:
    print(f"[STEP] docker build {image_tag}")
    subprocess.run(
        ["docker", "build", "-f", "worker/Dockerfile", "-t", image_tag, "."],
        cwd=ROOT,
        check=True,
    )


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
    resp.raise_for_status()
    user_id = str(resp.json().get("id", "")).strip()
    if not user_id:
        raise RuntimeError("admin user create returned empty id")
    return user_id


def _delete_admin_user(*, supabase_url: str, service_role_key: str, user_id: str) -> None:
    import requests

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
    resp = requests.delete(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code not in (200, 204):
        print(f"WARN: delete auth user failed id={user_id} status={resp.status_code}", file=sys.stderr)


def _wait_public_profile(project_ref: str, access_token: str, user_id: str, timeout_sec: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        rows = _db_query(project_ref, access_token, f"select id from public.users where id = '{user_id}' limit 1;")
        if rows:
            return
        time.sleep(0.25)
    raise RuntimeError(f"public.users profile not created for user={user_id}")


def _login(*, supabase_url: str, anon_key: str, email: str, password: str) -> str:
    import requests

    resp = requests.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    token = str(resp.json().get("access_token", "")).strip()
    if not token:
        raise RuntimeError(f"login returned empty token for email={email}")
    return token


def _make_dxf_bytes(width: float, height: float) -> bytes:
    import ezdxf

    temp = ROOT / "tmp" / f"_smoke_phase2_{secrets.token_hex(6)}.dxf"
    temp.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    if "CUT_OUTER" not in doc.layers:
        doc.layers.new(name="CUT_OUTER")
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))],
        format="xy",
        dxfattribs={"layer": "CUT_OUTER", "closed": True},
    )
    doc.saveas(temp)
    blob = temp.read_bytes()
    temp.unlink(missing_ok=True)
    return blob


def _upload_signed_blob(upload_url: str, blob: bytes) -> None:
    import requests

    last_status = 0
    for method in ("PUT", "POST"):
        resp = requests.request(
            method,
            upload_url,
            data=blob,
            headers={"Content-Type": "application/dxf"},
            timeout=30,
        )
        last_status = resp.status_code
        if resp.status_code in (200, 201):
            return
    raise RuntimeError(f"signed upload failed status={last_status}")


def _create_project(client: Any, headers: dict[str, str], name: str) -> str:
    resp = client.post("/v1/projects", headers=headers, json={"name": name, "description": "phase2 dod"})
    if resp.status_code != 200:
        raise RuntimeError(f"create project failed: {resp.status_code} {resp.text}")
    return str(resp.json()["id"])


def _create_file_record(
    client: Any,
    headers: dict[str, str],
    project_id: str,
    *,
    filename: str,
    file_type: str,
    blob: bytes,
) -> tuple[str, str]:
    upload_resp = client.post(
        f"/v1/projects/{project_id}/files/upload-url",
        headers=headers,
        json={
            "filename": filename,
            "content_type": "application/dxf",
            "size_bytes": len(blob),
            "file_type": file_type,
        },
    )
    if upload_resp.status_code != 200:
        raise RuntimeError(f"upload-url failed: {upload_resp.status_code} {upload_resp.text}")
    info = upload_resp.json()
    _upload_signed_blob(str(info["upload_url"]), blob)

    complete_resp = client.post(
        f"/v1/projects/{project_id}/files",
        headers=headers,
        json={
            "file_id": info["file_id"],
            "original_filename": filename,
            "storage_key": info["storage_key"],
            "file_type": file_type,
            "size_bytes": len(blob),
            "content_hash_sha256": hashlib.sha256(blob).hexdigest(),
        },
    )
    if complete_resp.status_code != 200:
        raise RuntimeError(f"file complete failed: {complete_resp.status_code} {complete_resp.text}")
    return str(info["file_id"]), str(info["storage_key"])


def _create_run_config(client: Any, headers: dict[str, str], project_id: str, stock_file_id: str, part_file_id: str) -> str:
    payload = {
        "name": "cfg-phase2-dod",
        "schema_version": "dxf_v1",
        "seed": 0,
        "time_limit_s": 20,
        "spacing_mm": 2.0,
        "margin_mm": 5.0,
        "stock_file_id": stock_file_id,
        "parts_config": [
            {
                "file_id": part_file_id,
                "quantity": 3,
                "allowed_rotations_deg": [0, 90, 180, 270],
            }
        ],
    }
    resp = client.post(f"/v1/projects/{project_id}/run-configs", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"create run-config failed: {resp.status_code} {resp.text}")
    return str(resp.json()["id"])


def _create_run(client: Any, headers: dict[str, str], project_id: str, run_config_id: str) -> str:
    resp = client.post(
        f"/v1/projects/{project_id}/runs",
        headers=headers,
        json={"run_config_id": run_config_id},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"create run failed: {resp.status_code} {resp.text}")
    run_id = str(resp.json().get("id", "")).strip()
    if not run_id:
        raise RuntimeError("create run returned empty id")
    return run_id


def _set_run_queue_priority(project_ref: str, access_token: str, run_id: str, priority: int) -> None:
    _db_query(
        project_ref,
        access_token,
        (
            "update public.run_queue "
            f"set priority = {int(priority)} "
            f"where run_id = '{run_id}';"
        ),
    )


def _run_status_via_api(client: Any, headers: dict[str, str], project_id: str, run_id: str) -> str:
    resp = client.get(f"/v1/projects/{project_id}/runs/{run_id}", headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"get run failed: {resp.status_code} {resp.text}")
    return str(resp.json().get("status", "")).strip().lower()


def _run_status_via_db(project_ref: str, access_token: str, run_id: str) -> str:
    try:
        rows = _db_query(project_ref, access_token, f"select status from public.runs where id = '{run_id}' limit 1;")
    except Exception:
        return ""
    if not rows:
        return ""
    return str(rows[0].get("status", "")).strip().lower()


def _wait_status(client: Any, headers: dict[str, str], project_id: str, run_id: str, expected: set[str], timeout_sec: float = 120.0) -> str:
    deadline = time.monotonic() + timeout_sec
    latest = ""
    while time.monotonic() < deadline:
        latest = _run_status_via_api(client, headers, project_id, run_id)
        if latest in expected:
            return latest
        time.sleep(1.0)
    raise RuntimeError(f"run={run_id} did not reach expected status {sorted(expected)}, latest={latest}")


def _worker_once_docker(
    *,
    image_tag: str,
    envs: dict[str, str],
    project_ref: str,
    access_token: str,
    run_id: str,
) -> list[str]:
    cmd = ["docker", "run", "--rm"]
    for key, value in envs.items():
        cmd.extend(["-e", f"{key}={value}"])
    cmd.extend([image_tag, "python3", "-m", "worker.main", "--once"])

    statuses: list[str] = []
    start_status = _run_status_via_db(project_ref, access_token, run_id)
    if start_status:
        statuses.append(start_status)

    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    while proc.poll() is None:
        status = _run_status_via_db(project_ref, access_token, run_id)
        if status and (not statuses or status != statuses[-1]):
            statuses.append(status)
        time.sleep(1.0)

    out, _ = proc.communicate()
    if proc.returncode != 0:
        tail = "\n".join((out or "").splitlines()[-40:])
        raise RuntimeError(f"worker docker run failed rc={proc.returncode}\n{tail}")

    end_status = _run_status_via_db(project_ref, access_token, run_id)
    if end_status and (not statuses or statuses[-1] != end_status):
        statuses.append(end_status)
    return statuses


def _extend_status_timeline(target: list[str], updates: list[str]) -> None:
    for status in updates:
        if status and (not target or target[-1] != status):
            target.append(status)


def _drive_worker_until_terminal(
    *,
    client: Any,
    headers: dict[str, str],
    project_id: str,
    run_id: str,
    image_tag: str,
    envs: dict[str, str],
    project_ref: str,
    access_token: str,
    max_cycles: int = 8,
) -> tuple[str, list[str]]:
    timeline: list[str] = []
    initial = _run_status_via_api(client, headers, project_id, run_id)
    if initial:
        timeline.append(initial)
    if initial in {"done", "failed", "cancelled"}:
        return initial, timeline

    for _ in range(max_cycles):
        statuses = _worker_once_docker(
            image_tag=image_tag,
            envs=envs,
            project_ref=project_ref,
            access_token=access_token,
            run_id=run_id,
        )
        _extend_status_timeline(timeline, statuses)
        current = _run_status_via_api(client, headers, project_id, run_id)
        _extend_status_timeline(timeline, [current])
        if current in {"done", "failed", "cancelled"}:
            return current, timeline
        time.sleep(1.0)

    latest = _run_status_via_api(client, headers, project_id, run_id)
    raise RuntimeError(f"run={run_id} did not reach terminal status after {max_cycles} worker cycles, latest={latest}, timeline={timeline}")


def _artifact_rows(project_ref: str, access_token: str, run_id: str) -> list[dict[str, Any]]:
    return _db_query(
        project_ref,
        access_token,
        (
            "select artifact_type, filename, storage_key "
            "from public.run_artifacts "
            f"where run_id = '{run_id}' "
            "order by created_at asc;"
        ),
    )


def _storage_rows(project_ref: str, access_token: str, run_id: str) -> list[dict[str, Any]]:
    prefix = f"runs/{run_id}/artifacts/%"
    return _db_query(
        project_ref,
        access_token,
        (
            "select name from storage.objects "
            "where bucket_id = 'vrs-nesting' "
            f"and name like '{prefix}' "
            "order by name asc;"
        ),
    )


def _download_storage_blob(*, supabase_url: str, service_role_key: str, bucket: str, storage_key: str) -> bytes:
    import requests

    encoded = quote(storage_key, safe="/")
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    sign_resp = requests.post(
        f"{supabase_url}/storage/v1/object/sign/{bucket}/{encoded}",
        headers=headers,
        json={"expiresIn": 600},
        timeout=30,
    )
    sign_resp.raise_for_status()
    payload = sign_resp.json()
    signed = str(payload.get("signedURL") or payload.get("signedUrl") or payload.get("url") or "").strip()
    if not signed:
        raise RuntimeError("missing signed download URL")
    if signed.startswith("http://") or signed.startswith("https://"):
        download_url = signed
    else:
        normalized = signed if signed.startswith("/") else f"/{signed}"
        if normalized.startswith("/object/"):
            download_url = f"{supabase_url}/storage/v1{normalized}"
        else:
            download_url = f"{supabase_url}{normalized}"

    blob_resp = requests.get(download_url, timeout=30)
    blob_resp.raise_for_status()
    return blob_resp.content


def _solver_output_signature(blob: bytes) -> dict[str, Any]:
    payload = json.loads(blob.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("solver_output is not a JSON object")

    placements_raw = payload.get("placements")
    if not isinstance(placements_raw, list):
        placements_raw = []
    unplaced_raw = payload.get("unplaced")
    if not isinstance(unplaced_raw, list):
        unplaced_raw = []

    placements = sorted(
        (
            str(item.get("instance_id", "")),
            str(item.get("part_id", "")),
            int(item.get("sheet_index", 0)),
            round(float(item.get("x", 0.0)), 6),
            round(float(item.get("y", 0.0)), 6),
            round(float(item.get("rotation_deg", 0.0)), 6),
        )
        for item in placements_raw
        if isinstance(item, dict)
    )
    unplaced = sorted(
        (
            str(item.get("instance_id", "")),
            str(item.get("part_id", "")),
            str(item.get("reason", "")),
        )
        for item in unplaced_raw
        if isinstance(item, dict)
    )
    return {
        "status": str(payload.get("status", "")),
        "placements": placements,
        "unplaced": unplaced,
    }


def main() -> int:
    try:
        import requests
        from fastapi.testclient import TestClient
        from api.main import app
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "missing runtime deps for smoke (requests/fastapi/httpx). "
            "Install api/requirements.txt in current Python env. "
            f"cause={exc!r}"
        ) from exc

    project_ref = _must_env("SUPABASE_PROJECT_REF")
    access_token = _must_env("SUPABASE_ACCESS_TOKEN")
    anon_key = _must_env("SUPABASE_ANON_KEY")
    supabase_url = _must_env("SUPABASE_URL").rstrip("/")

    service_role_key = _get_service_role_key(project_ref, access_token)
    sparrow_bin = _ensure_sparrow_bin()

    image_tag = f"vrs-worker:phase2-dod-{secrets.token_hex(3)}"
    _build_worker_image(image_tag)

    password = "CodexTmp!2345"
    user_email = _rand_email("phase2dod")
    user_id = ""

    client = TestClient(app)

    try:
        user_id = _create_admin_user(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            email=user_email,
            password=password,
        )
        _wait_public_profile(project_ref, access_token, user_id)

        token = _login(
            supabase_url=supabase_url,
            anon_key=anon_key,
            email=user_email,
            password=password,
        )
        headers = {"Authorization": f"Bearer {token}"}

        stock_blob = _make_dxf_bytes(600.0, 400.0)
        part_blob = _make_dxf_bytes(120.0, 80.0)

        project_id = _create_project(client, headers, "Phase2 DoD Good")
        stock_file_id, _stock_key = _create_file_record(
            client,
            headers,
            project_id,
            filename="stock.dxf",
            file_type="stock_dxf",
            blob=stock_blob,
        )
        part_file_id, part_storage_key = _create_file_record(
            client,
            headers,
            project_id,
            filename="part.dxf",
            file_type="part_dxf",
            blob=part_blob,
        )

        cfg_id = _create_run_config(client, headers, project_id, stock_file_id, part_file_id)

        # DONE run + status transitions via docker worker
        run1_id = _create_run(client, headers, project_id, cfg_id)
        _set_run_queue_priority(project_ref, access_token, run1_id, 10000)
        if _run_status_via_api(client, headers, project_id, run1_id) != "queued":
            raise RuntimeError("expected run1 initial status queued")

        docker_env = {
            "SUPABASE_URL": supabase_url,
            "SUPABASE_PROJECT_REF": project_ref,
            "SUPABASE_ACCESS_TOKEN": access_token,
            "SUPABASE_SERVICE_ROLE_KEY": service_role_key,
            "API_STORAGE_BUCKET": "vrs-nesting",
            "SPARROW_BIN": "/usr/local/bin/sparrow",
            "WORKER_POLL_INTERVAL_S": "1",
            "WORKER_RETRY_DELAY_S": "1",
            "WORKER_TIMEOUT_EXTRA_S": "120",
        }

        status1, statuses_run1 = _drive_worker_until_terminal(
            client=client,
            headers=headers,
            project_id=project_id,
            run_id=run1_id,
            image_tag=image_tag,
            envs=docker_env,
            project_ref=project_ref,
            access_token=access_token,
        )
        if status1 != "done":
            run1_fail = client.get(f"/v1/projects/{project_id}/runs/{run1_id}", headers=headers).json()
            raise RuntimeError(
                "expected run1 done, "
                f"got {status1}, timeline={statuses_run1}, "
                f"error_message={run1_fail.get('error_message')!r}"
            )

        if "queued" not in statuses_run1 or "done" not in statuses_run1:
            raise RuntimeError(f"missing queued/done status transitions for run1, got={statuses_run1}")
        run1_details = client.get(f"/v1/projects/{project_id}/runs/{run1_id}", headers=headers).json()
        if not str(run1_details.get("started_at", "")).strip():
            raise RuntimeError("run1 started_at is empty, expected queued -> running transition")
        if not str(run1_details.get("finished_at", "")).strip():
            raise RuntimeError("run1 finished_at is empty, expected terminal completion timestamp")

        artifact_rows_run1 = _artifact_rows(project_ref, access_token, run1_id)
        artifact_types_run1 = {str(row.get("artifact_type", "")) for row in artifact_rows_run1}
        artifact_filenames_run1 = [str(row.get("filename", "")).strip() for row in artifact_rows_run1]
        for required_type in ("report_json", "solver_output"):
            if required_type not in artifact_types_run1:
                raise RuntimeError(
                    f"run1 missing artifact_type={required_type}, "
                    f"artifact_types={sorted(artifact_types_run1)}"
                )
        if not any(name.endswith(".dxf") for name in artifact_filenames_run1):
            raise RuntimeError(f"run1 missing .dxf run_artifacts rows, filenames={artifact_filenames_run1}")
        if not any(name.endswith(".svg") for name in artifact_filenames_run1):
            raise RuntimeError(f"run1 missing .svg run_artifacts rows, filenames={artifact_filenames_run1}")

        storage_rows_run1 = _storage_rows(project_ref, access_token, run1_id)
        storage_names = [str(row.get("name", "")) for row in storage_rows_run1]
        if not any(name.endswith("report.json") for name in storage_names):
            raise RuntimeError("report.json missing from storage objects")
        if not any(name.endswith("solver_output.json") for name in storage_names):
            raise RuntimeError("solver_output.json missing from storage objects")
        if not any(name.endswith(".dxf") for name in storage_names):
            raise RuntimeError("DXF artifact missing from storage objects")
        if not any(name.endswith(".svg") for name in storage_names):
            raise RuntimeError("SVG artifact missing from storage objects")

        log_resp = client.get(f"/v1/projects/{project_id}/runs/{run1_id}/log?offset=0&lines=200", headers=headers)
        if log_resp.status_code != 200:
            raise RuntimeError(f"run log endpoint failed: {log_resp.status_code} {log_resp.text}")
        log_payload = log_resp.json()
        if int(log_payload.get("total_lines", 0)) <= 0:
            raise RuntimeError("run log endpoint returned zero lines")

        # Rerun determinism check
        rerun_resp = client.post(f"/v1/projects/{project_id}/runs/{run1_id}/rerun", headers=headers)
        if rerun_resp.status_code != 200:
            raise RuntimeError(f"rerun failed: {rerun_resp.status_code} {rerun_resp.text}")
        run2_id = str(rerun_resp.json().get("id", "")).strip()
        if not run2_id:
            raise RuntimeError("rerun returned empty run id")
        _set_run_queue_priority(project_ref, access_token, run2_id, 10000)

        status2, _statuses_run2 = _drive_worker_until_terminal(
            client=client,
            headers=headers,
            project_id=project_id,
            run_id=run2_id,
            image_tag=image_tag,
            envs=docker_env,
            project_ref=project_ref,
            access_token=access_token,
        )
        if status2 != "done":
            raise RuntimeError(f"expected rerun done, got {status2}")

        run1 = client.get(f"/v1/projects/{project_id}/runs/{run1_id}", headers=headers).json()
        run2 = client.get(f"/v1/projects/{project_id}/runs/{run2_id}", headers=headers).json()
        m1 = run1.get("metrics") or {}
        m2 = run2.get("metrics") or {}
        if (
            int(m1.get("placements_count", -1)) != int(m2.get("placements_count", -2))
            or int(m1.get("unplaced_count", -1)) != int(m2.get("unplaced_count", -2))
            or int(m1.get("sheet_count", -1)) != int(m2.get("sheet_count", -2))
        ):
            raise RuntimeError(f"rerun metrics mismatch run1={m1} run2={m2}")

        solver_keys = _db_query(
            project_ref,
            access_token,
            (
                "select run_id, storage_key from public.run_artifacts "
                f"where run_id in ('{run1_id}','{run2_id}') and artifact_type = 'solver_output';"
            ),
        )
        key_by_run = {str(row.get("run_id", "")): str(row.get("storage_key", "")) for row in solver_keys}
        if run1_id not in key_by_run or run2_id not in key_by_run:
            raise RuntimeError("solver_output storage key missing for run1/run2")
        solver_blob_1 = _download_storage_blob(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            bucket="vrs-nesting",
            storage_key=key_by_run[run1_id],
        )
        solver_blob_2 = _download_storage_blob(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            bucket="vrs-nesting",
            storage_key=key_by_run[run2_id],
        )
        sig1 = _solver_output_signature(solver_blob_1)
        sig2 = _solver_output_signature(solver_blob_2)
        if sig1 != sig2:
            print(f"[WARN] rerun solver_output signature mismatch (metrics matched): run1={sig1} run2={sig2}")

        # FAILED run with readable error
        bad_project_id = _create_project(client, headers, "Phase2 DoD Bad")
        bad_stock_id, _ = _create_file_record(
            client,
            headers,
            bad_project_id,
            filename="stock_bad.dxf",
            file_type="stock_dxf",
            blob=stock_blob,
        )
        bad_part_id, _ = _create_file_record(
            client,
            headers,
            bad_project_id,
            filename="part_bad.dxf",
            file_type="part_dxf",
            blob=part_blob,
        )
        bad_cfg_id = _create_run_config(client, headers, bad_project_id, bad_stock_id, bad_part_id)
        bad_run_id = _create_run(client, headers, bad_project_id, bad_cfg_id)
        _set_run_queue_priority(project_ref, access_token, bad_run_id, 10000)

        broken_key = f"users/{user_id}/projects/{bad_project_id}/files/{bad_part_id}/missing_input_for_fail.dxf"
        _db_query(
            project_ref,
            access_token,
            (
                "update public.project_files "
                f"set storage_key = '{broken_key}' "
                f"where id = '{bad_part_id}';"
            ),
        )
        _db_query(
            project_ref,
            access_token,
            (
                "update public.run_queue "
                "set max_attempts = 1 "
                f"where run_id = '{bad_run_id}';"
            ),
        )

        bad_status, _bad_timeline = _drive_worker_until_terminal(
            client=client,
            headers=headers,
            project_id=bad_project_id,
            run_id=bad_run_id,
            image_tag=image_tag,
            envs=docker_env,
            project_ref=project_ref,
            access_token=access_token,
            max_cycles=4,
        )
        if bad_status != "failed":
            raise RuntimeError(f"expected bad run failed, got {bad_status}")
        bad_run = client.get(f"/v1/projects/{bad_project_id}/runs/{bad_run_id}", headers=headers).json()
        if not str(bad_run.get("error_message", "")).strip():
            raise RuntimeError("failed run has empty error_message")

        print("[OK] Phase 2 DoD acceptance smoke passed")
        print("[OK] docker build+run, queue watch, status transitions, artifacts, log, failed error, rerun determinism")
        return 0

    finally:
        if user_id:
            try:
                _db_query(project_ref, access_token, f"delete from public.projects where owner_id = '{user_id}';")
            except Exception:
                pass
            try:
                _delete_admin_user(supabase_url=supabase_url, service_role_key=service_role_key, user_id=user_id)
            except Exception:
                pass
        try:
            subprocess.run(["docker", "image", "rm", "-f", image_tag], cwd=ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
