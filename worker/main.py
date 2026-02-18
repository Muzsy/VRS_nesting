#!/usr/bin/env python3
"""Phase 2 worker loop: queue claim, run processing, artifact upload."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class WorkerError(RuntimeError):
    pass


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


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True)
class WorkerSettings:
    supabase_url: str
    supabase_project_ref: str
    supabase_access_token: str
    supabase_service_role_key: str
    storage_bucket: str
    worker_id: str
    poll_interval_s: float
    retry_delay_s: int
    run_timeout_extra_s: int
    run_root: Path
    temp_root: Path
    sparrow_bin: str
    once: bool


class WorkerSettingsError(WorkerError):
    pass


def load_settings(*, once: bool, poll_interval_s: float | None = None) -> WorkerSettings:
    supabase_url = _resolve_env("SUPABASE_URL")
    project_ref = _resolve_env("SUPABASE_PROJECT_REF")
    access_token = _resolve_env("SUPABASE_ACCESS_TOKEN")
    service_role_key = _resolve_env("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        raise WorkerSettingsError("missing SUPABASE_URL")
    if not project_ref:
        raise WorkerSettingsError("missing SUPABASE_PROJECT_REF")
    if not access_token:
        raise WorkerSettingsError("missing SUPABASE_ACCESS_TOKEN")
    if not service_role_key:
        raise WorkerSettingsError("missing SUPABASE_SERVICE_ROLE_KEY")

    poll_raw = _resolve_env("WORKER_POLL_INTERVAL_S", "5")
    poll_value = poll_interval_s if poll_interval_s is not None else float(poll_raw)
    if poll_value <= 0:
        raise WorkerSettingsError("WORKER_POLL_INTERVAL_S must be > 0")

    retry_delay_s = int(_resolve_env("WORKER_RETRY_DELAY_S", "30"))
    timeout_extra_s = int(_resolve_env("WORKER_TIMEOUT_EXTRA_S", "120"))

    worker_id = _resolve_env("WORKER_ID", f"worker-{os.getpid()}")
    run_root = Path(_resolve_env("WORKER_RUN_ROOT", "runs")).resolve()
    temp_root = Path(_resolve_env("WORKER_TEMP_ROOT", "/tmp/vrs_worker")).resolve()

    return WorkerSettings(
        supabase_url=supabase_url.rstrip("/"),
        supabase_project_ref=project_ref,
        supabase_access_token=access_token,
        supabase_service_role_key=service_role_key,
        storage_bucket=_resolve_env("API_STORAGE_BUCKET", "vrs-nesting"),
        worker_id=worker_id,
        poll_interval_s=poll_value,
        retry_delay_s=retry_delay_s,
        run_timeout_extra_s=timeout_extra_s,
        run_root=run_root,
        temp_root=temp_root,
        sparrow_bin=_resolve_env("SPARROW_BIN", ""),
        once=once,
    )


class WorkerSupabaseClient:
    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings

    def _management_query(self, sql: str) -> list[dict[str, Any]]:
        url = f"https://api.supabase.com/v1/projects/{self._settings.supabase_project_ref}/database/query"
        payload = json.dumps({"query": sql}, ensure_ascii=True).encode("utf-8")
        req = Request(
            url=url,
            method="POST",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._settings.supabase_access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "vrs-worker/phase2-p2",
            },
        )
        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise WorkerError(f"management query failed: {exc.code} {err}") from exc
        except URLError as exc:
            raise WorkerError(f"management query network error: {exc}") from exc

        parsed = json.loads(body or "[]")
        if not isinstance(parsed, list):
            raise WorkerError("management query response is not list")
        out: list[dict[str, Any]] = []
        for row in parsed:
            if isinstance(row, dict):
                out.append(row)
        return out

    def claim_next_queue_item(self, worker_id: str) -> dict[str, Any] | None:
        sql = f"""
with candidate as (
  select q.id
  from public.run_queue q
  join public.runs r on r.id = q.run_id
  where q.visible_after <= now()
    and (q.locked_by is null or q.locked_at < now() - interval '10 minutes')
    and r.status in ('queued','running')
  order by q.priority desc, q.created_at asc
  for update skip locked
  limit 1
)
update public.run_queue q
set locked_by = {_sql_literal(worker_id)},
    locked_at = now(),
    attempts = q.attempts + 1
from candidate c
where q.id = c.id
returning q.id, q.run_id, q.attempts, q.max_attempts;
"""
        rows = self._management_query(sql)
        return rows[0] if rows else None

    def fetch_run_context(self, run_id: str) -> dict[str, Any]:
        sql = f"""
select
  r.id as run_id,
  r.project_id,
  r.run_config_id,
  coalesce(rc.seed, 0) as seed,
  coalesce(rc.time_limit_s, 60) as time_limit_s,
  coalesce(rc.spacing_mm, 2.0) as spacing_mm,
  coalesce(rc.margin_mm, 5.0) as margin_mm,
  rc.stock_file_id,
  rc.parts_config
from public.runs r
left join public.run_configs rc on rc.id = r.run_config_id
where r.id = {_sql_literal(run_id)}
limit 1;
"""
        rows = self._management_query(sql)
        if not rows:
            raise WorkerError(f"run not found: {run_id}")
        return rows[0]

    def fetch_project_file(self, file_id: str) -> dict[str, Any]:
        sql = f"""
select id, original_filename, storage_key, file_type
from public.project_files
where id = {_sql_literal(file_id)}
limit 1;
"""
        rows = self._management_query(sql)
        if not rows:
            raise WorkerError(f"project file not found: {file_id}")
        return rows[0]

    def mark_run_running(self, run_id: str) -> None:
        sql = f"""
update public.runs
set status = 'running', started_at = now(), error_message = null
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def mark_run_done(
        self,
        *,
        run_id: str,
        run_dir_key: str,
        worker_run_id: str,
        solver_exit_code: int,
        placements_count: int,
        unplaced_count: int,
        sheet_count: int,
    ) -> None:
        sql = f"""
update public.runs
set status = 'done',
    finished_at = now(),
    duration_sec = extract(epoch from now() - coalesce(started_at, queued_at)),
    run_dir_key = {_sql_literal(run_dir_key)},
    worker_run_id = {_sql_literal(worker_run_id)},
    solver_exit_code = {solver_exit_code},
    placements_count = {placements_count},
    unplaced_count = {unplaced_count},
    sheet_count = {sheet_count},
    error_message = null
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def mark_run_failed(self, *, run_id: str, message: str) -> None:
        sql = f"""
update public.runs
set status = 'failed',
    finished_at = now(),
    duration_sec = extract(epoch from now() - coalesce(started_at, queued_at)),
    error_message = {_sql_literal(message[:2000])}
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def mark_run_queued_for_retry(self, *, run_id: str, message: str) -> None:
        sql = f"""
update public.runs
set status = 'queued',
    started_at = null,
    error_message = {_sql_literal(message[:2000])}
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def complete_queue_item(self, *, queue_id: str) -> None:
        sql = f"delete from public.run_queue where id = {_sql_literal(queue_id)};"
        self._management_query(sql)

    def requeue_item(self, *, queue_id: str, retry_delay_s: int) -> None:
        sql = f"""
update public.run_queue
set locked_by = null,
    locked_at = null,
    visible_after = now() + interval '{int(retry_delay_s)} seconds'
where id = {_sql_literal(queue_id)};
"""
        self._management_query(sql)

    def insert_run_artifact(
        self,
        *,
        run_id: str,
        artifact_type: str,
        filename: str,
        storage_key: str,
        size_bytes: int,
        sheet_index: int | None,
    ) -> None:
        sheet_value = "null" if sheet_index is None else str(sheet_index)
        sql = f"""
insert into public.run_artifacts(run_id, artifact_type, filename, storage_key, size_bytes, sheet_index)
values (
  {_sql_literal(run_id)},
  {_sql_literal(artifact_type)},
  {_sql_literal(filename)},
  {_sql_literal(storage_key)},
  {size_bytes},
  {sheet_value}
);
"""
        self._management_query(sql)

    def _storage_request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._settings.supabase_url}{path}"
        data: bytes | None = None
        headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
            "Accept": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = Request(url=url, method=method.upper(), headers=headers, data=data)
        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise WorkerError(f"storage request failed: {method} {path} -> {exc.code}: {err}") from exc
        except URLError as exc:
            raise WorkerError(f"storage request network error: {exc}") from exc

        parsed = json.loads(body or "{}")
        if not isinstance(parsed, dict):
            raise WorkerError("storage response is not object")
        return parsed

    def create_signed_download_url(self, *, bucket: str, object_key: str, expires_in: int = 900) -> str:
        encoded_key = quote(object_key, safe="/")
        payload = self._storage_request(
            "POST",
            f"/storage/v1/object/sign/{bucket}/{encoded_key}",
            payload={"expiresIn": expires_in},
        )
        signed_path = str(payload.get("signedURL") or payload.get("signedUrl") or payload.get("url") or "").strip()
        if not signed_path:
            raise WorkerError("missing signed download URL")
        if signed_path.startswith("http://") or signed_path.startswith("https://"):
            return signed_path
        normalized = signed_path if signed_path.startswith("/") else f"/{signed_path}"
        if normalized.startswith("/object/"):
            return f"{self._settings.supabase_url}/storage/v1{normalized}"
        return f"{self._settings.supabase_url}{normalized}"

    def create_signed_upload_url(self, *, bucket: str, object_key: str, expires_in: int = 900) -> str:
        encoded_key = quote(object_key, safe="/")
        payload = self._storage_request(
            "POST",
            f"/storage/v1/object/upload/sign/{bucket}/{encoded_key}",
            payload={"expiresIn": expires_in},
        )
        signed_path = str(payload.get("signedURL") or payload.get("signedUrl") or payload.get("url") or "").strip()
        upload_token = str(payload.get("token", "")).strip()
        if signed_path:
            if signed_path.startswith("http://") or signed_path.startswith("https://"):
                return signed_path
            normalized = signed_path if signed_path.startswith("/") else f"/{signed_path}"
            if normalized.startswith("/object/"):
                return f"{self._settings.supabase_url}/storage/v1{normalized}"
            return f"{self._settings.supabase_url}{normalized}"
        if upload_token:
            return (
                f"{self._settings.supabase_url}/storage/v1/object/upload/sign/"
                f"{bucket}/{encoded_key}?token={upload_token}"
            )
        raise WorkerError("missing signed upload URL")

    def download_object(self, *, bucket: str, object_key: str) -> bytes:
        signed_url = self.create_signed_download_url(bucket=bucket, object_key=object_key)
        req = Request(url=signed_url, method="GET")
        try:
            with urlopen(req, timeout=60) as resp:
                return resp.read()
        except HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise WorkerError(f"download failed: {exc.code}: {err}") from exc
        except URLError as exc:
            raise WorkerError(f"download network error: {exc}") from exc

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        upload_url = self.create_signed_upload_url(bucket=bucket, object_key=object_key)
        for method in ("PUT", "POST"):
            req = Request(url=upload_url, method=method, data=payload)
            req.add_header("Content-Type", "application/octet-stream")
            try:
                with urlopen(req, timeout=60):
                    return
            except HTTPError:
                continue
            except URLError:
                continue
        raise WorkerError(f"upload failed for storage key: {object_key}")


def _artifact_type_for_path(relative_path: Path) -> tuple[str, int | None]:
    name = relative_path.name
    sheet_index: int | None = None
    if name.startswith("sheet_"):
        token = name.split("_", 1)[1].split(".", 1)[0]
        if token.isdigit():
            sheet_index = int(token)

    if name == "report.json":
        return "report_json", None
    if name == "solver_output.json":
        return "solver_output", None
    if name == "solver_input.json":
        return "solver_input", None
    if name == "sparrow_output.json":
        return "sparrow_output", None
    if name == "run.log":
        return "run_log", None
    if name.endswith(".dxf") and sheet_index is not None:
        return "sheet_dxf", sheet_index
    if name.endswith(".svg") and sheet_index is not None:
        return "sheet_svg", sheet_index
    return "artifact_file", sheet_index


def _parse_parts_config(parts_config_raw: Any) -> list[dict[str, Any]]:
    if parts_config_raw is None:
        return []
    if isinstance(parts_config_raw, str):
        try:
            parsed = json.loads(parts_config_raw)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return []
    if isinstance(parts_config_raw, list):
        return [item for item in parts_config_raw if isinstance(item, dict)]
    return []


def _build_dxf_project_payload(
    *,
    run_id: str,
    context: dict[str, Any],
    stock_file: dict[str, Any],
    part_entries: list[dict[str, Any]],
    local_paths_by_file_id: dict[str, Path],
) -> dict[str, Any]:
    seed = int(context.get("seed") or 0)
    time_limit_s = int(context.get("time_limit_s") or 60)
    spacing_mm = float(context.get("spacing_mm") or 2.0)
    margin_mm = float(context.get("margin_mm") or 5.0)

    stocks_dxf = [
        {
            "id": str(stock_file.get("id", "stock")),
            "path": str(local_paths_by_file_id[str(stock_file["id"])].resolve()),
            "quantity": 1,
        }
    ]

    parts_dxf: list[dict[str, Any]] = []
    for entry in part_entries:
        file_id = str(entry.get("file_id") or entry.get("project_file_id") or entry.get("id") or "").strip()
        if not file_id:
            continue
        local_path = local_paths_by_file_id.get(file_id)
        if local_path is None:
            continue
        quantity = int(entry.get("quantity") or entry.get("qty") or 1)
        rotations = entry.get("allowed_rotations_deg") or entry.get("rotations") or [0, 90, 180, 270]
        if not isinstance(rotations, list):
            rotations = [0, 90, 180, 270]
        parts_dxf.append(
            {
                "id": file_id,
                "path": str(local_path.resolve()),
                "quantity": max(quantity, 1),
                "allowed_rotations_deg": rotations,
            }
        )

    if not parts_dxf:
        raise WorkerError(f"run {run_id}: no part entries resolved from run_config.parts_config")

    return {
        "version": "dxf_v1",
        "name": f"worker_run_{run_id}",
        "seed": seed,
        "time_limit_s": time_limit_s,
        "units": "mm",
        "spacing_mm": spacing_mm,
        "margin_mm": margin_mm,
        "stocks_dxf": stocks_dxf,
        "parts_dxf": parts_dxf,
    }


def _read_run_metrics(run_dir: Path) -> tuple[int, int, int]:
    report_json = run_dir / "report.json"
    if not report_json.is_file():
        return 0, 0, 0
    try:
        payload = json.loads(report_json.read_text(encoding="utf-8"))
    except Exception:
        return 0, 0, 0
    if not isinstance(payload, dict):
        return 0, 0, 0

    metrics = payload.get("metrics", {})
    placements_count = int(metrics.get("placements_count") or 0) if isinstance(metrics, dict) else 0
    unplaced_count = int(metrics.get("unplaced_count") or 0) if isinstance(metrics, dict) else 0

    out_dir = run_dir / "out"
    sheet_count = len(list(out_dir.glob("sheet_*.dxf"))) if out_dir.is_dir() else 0
    return placements_count, unplaced_count, sheet_count


def _find_run_dir_from_stdout(stdout: str) -> Path:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise WorkerError("dxf-run returned empty stdout; run_dir path missing")
    return Path(lines[-1]).resolve()


def _process_queue_item(client: WorkerSupabaseClient, settings: WorkerSettings, item: dict[str, Any]) -> None:
    queue_id = str(item.get("id", "")).strip()
    run_id = str(item.get("run_id", "")).strip()
    attempts = int(item.get("attempts") or 0)
    max_attempts = int(item.get("max_attempts") or 3)
    if not queue_id or not run_id:
        raise WorkerError("queue claim returned missing id/run_id")

    client.mark_run_running(run_id)

    job_temp_dir = Path(tempfile.mkdtemp(prefix=f"{run_id}_", dir=settings.temp_root))
    run_root = job_temp_dir / "runs"
    input_dir = job_temp_dir / "input"
    run_root.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)

    try:
        context = client.fetch_run_context(run_id)
        stock_file_id = str(context.get("stock_file_id") or "").strip()
        if not stock_file_id:
            raise WorkerError(f"run {run_id}: missing stock_file_id in run_config")

        stock_file = client.fetch_project_file(stock_file_id)
        parts_cfg = _parse_parts_config(context.get("parts_config"))

        file_ids = {stock_file_id}
        for entry in parts_cfg:
            file_id = str(entry.get("file_id") or entry.get("project_file_id") or entry.get("id") or "").strip()
            if file_id:
                file_ids.add(file_id)

        local_paths_by_file_id: dict[str, Path] = {}
        for file_id in sorted(file_ids):
            row = client.fetch_project_file(file_id)
            storage_key = str(row.get("storage_key", "")).strip()
            if not storage_key:
                raise WorkerError(f"run {run_id}: missing storage_key for project_file {file_id}")
            filename = Path(str(row.get("original_filename") or file_id)).name
            destination = input_dir / f"{file_id}_{filename}"
            blob = client.download_object(bucket=settings.storage_bucket, object_key=storage_key)
            destination.write_bytes(blob)
            local_paths_by_file_id[file_id] = destination
            if file_id == stock_file_id:
                stock_file = row

        project_payload = _build_dxf_project_payload(
            run_id=run_id,
            context=context,
            stock_file=stock_file,
            part_entries=parts_cfg,
            local_paths_by_file_id=local_paths_by_file_id,
        )
        project_json_path = input_dir / "project_dxf_v1.json"
        project_json_path.write_text(json.dumps(project_payload, ensure_ascii=True, indent=2), encoding="utf-8")

        cmd = [
            "python3",
            "-m",
            "vrs_nesting.cli",
            "dxf-run",
            str(project_json_path),
            "--run-root",
            str(run_root),
        ]
        if settings.sparrow_bin:
            cmd.extend(["--sparrow-bin", settings.sparrow_bin])

        timeout_s = int(context.get("time_limit_s") or 60) + settings.run_timeout_extra_s
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(timeout_s, 30),
        )

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise WorkerError(f"dxf-run failed (exit={proc.returncode}): {stderr[:2000]}")

        run_dir = _find_run_dir_from_stdout(proc.stdout)

        for artifact_path in run_dir.rglob("*"):
            if not artifact_path.is_file():
                continue
            relative = artifact_path.relative_to(run_dir)
            storage_key = f"runs/{run_id}/artifacts/{relative.as_posix()}"
            payload = artifact_path.read_bytes()
            client.upload_object(bucket=settings.storage_bucket, object_key=storage_key, payload=payload)
            artifact_type, sheet_index = _artifact_type_for_path(relative)
            client.insert_run_artifact(
                run_id=run_id,
                artifact_type=artifact_type,
                filename=relative.as_posix(),
                storage_key=storage_key,
                size_bytes=artifact_path.stat().st_size,
                sheet_index=sheet_index,
            )

        placements_count, unplaced_count, sheet_count = _read_run_metrics(run_dir)
        client.mark_run_done(
            run_id=run_id,
            run_dir_key=f"runs/{run_id}/artifacts",
            worker_run_id=run_dir.name,
            solver_exit_code=0,
            placements_count=placements_count,
            unplaced_count=unplaced_count,
            sheet_count=sheet_count,
        )
        client.complete_queue_item(queue_id=queue_id)

    except Exception as exc:
        message = str(exc)
        if attempts >= max_attempts:
            client.mark_run_failed(run_id=run_id, message=message)
            client.complete_queue_item(queue_id=queue_id)
        else:
            client.mark_run_queued_for_retry(run_id=run_id, message=message)
            client.requeue_item(queue_id=queue_id, retry_delay_s=settings.retry_delay_s)
        raise
    finally:
        shutil.rmtree(job_temp_dir, ignore_errors=True)


def run_worker_loop(settings: WorkerSettings) -> int:
    settings.temp_root.mkdir(parents=True, exist_ok=True)
    settings.run_root.mkdir(parents=True, exist_ok=True)

    client = WorkerSupabaseClient(settings)

    while True:
        item = client.claim_next_queue_item(settings.worker_id)
        if item is None:
            if settings.once:
                return 0
            time.sleep(settings.poll_interval_s)
            continue

        try:
            _process_queue_item(client, settings, item)
            print(f"[worker] processed run_id={item.get('run_id')} queue_id={item.get('id')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] run processing error: {exc}")

        if settings.once:
            return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VRS worker loop")
    parser.add_argument("--once", action="store_true", help="Process at most one queue item then exit")
    parser.add_argument("--poll-interval-s", type=float, default=None, help="Polling interval in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(once=bool(args.once), poll_interval_s=args.poll_interval_s)
    return run_worker_loop(settings)


if __name__ == "__main__":
    raise SystemExit(main())
