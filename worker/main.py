#!/usr/bin/env python3
"""Phase 2 worker loop: queue claim, run processing, artifact upload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


class WorkerError(RuntimeError):
    pass


class WorkerSettingsError(WorkerError):
    pass


class WorkerCancelledError(WorkerError):
    pass


class WorkerTimeoutError(WorkerError):
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
    run_log_sync_interval_s: float
    run_root: Path
    temp_root: Path
    sparrow_bin: str
    once: bool


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
    log_sync_interval_s = float(_resolve_env("WORKER_RUN_LOG_SYNC_INTERVAL_S", "2"))
    if log_sync_interval_s <= 0:
        raise WorkerSettingsError("WORKER_RUN_LOG_SYNC_INTERVAL_S must be > 0")

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
        run_log_sync_interval_s=log_sync_interval_s,
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
        body = ""
        for attempt in range(6):
            req = Request(
                url=url,
                method="POST",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._settings.supabase_access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "vrs-worker/phase2",
                },
            )
            try:
                with urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                break
            except HTTPError as exc:
                err = exc.read().decode("utf-8", errors="replace")
                if exc.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(min(5.0, 0.4 * (attempt + 1)))
                    continue
                raise WorkerError(f"management query failed: {exc.code} {err}") from exc
            except URLError as exc:
                if attempt < 5:
                    time.sleep(min(5.0, 0.4 * (attempt + 1)))
                    continue
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

    def fetch_run_status(self, run_id: str) -> str:
        sql = f"""
select status
from public.runs
where id = {_sql_literal(run_id)}
limit 1;
"""
        rows = self._management_query(sql)
        if not rows:
            return ""
        return str(rows[0].get("status", "")).strip().lower()

    def mark_run_running(self, run_id: str) -> None:
        sql = f"""
update public.runs
set status = 'running',
    started_at = now(),
    finished_at = null,
    duration_sec = null,
    solver_exit_code = null,
    error_message = null
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
    finished_at = null,
    duration_sec = null,
    error_message = {_sql_literal(message[:2000])}
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def mark_run_cancelled(self, *, run_id: str, message: str) -> None:
        sql = f"""
update public.runs
set status = 'cancelled',
    finished_at = coalesce(finished_at, now()),
    duration_sec = extract(epoch from coalesce(finished_at, now()) - coalesce(started_at, queued_at)),
    error_message = {_sql_literal(message[:2000])}
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def set_run_input_snapshot_hash(self, *, run_id: str, snapshot_hash: str) -> None:
        sql = f"""
update public.runs
set input_snapshot_hash = {_sql_literal(snapshot_hash)}
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

    def replace_run_log_artifact(self, *, run_id: str, storage_key: str, size_bytes: int) -> None:
        sql = f"""
delete from public.run_artifacts
where run_id = {_sql_literal(run_id)}
  and artifact_type = 'run_log';

insert into public.run_artifacts(run_id, artifact_type, filename, storage_key, size_bytes, sheet_index)
values (
  {_sql_literal(run_id)},
  'run_log',
  'run.log',
  {_sql_literal(storage_key)},
  {int(size_bytes)},
  null
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

    @staticmethod
    def _is_duplicate_storage_error(error_text: str) -> bool:
        normalized = error_text.lower()
        return (
            "duplicate" in normalized
            or '"statuscode":"409"' in normalized
            or " 409:" in normalized
        )

    def create_signed_upload_url(self, *, bucket: str, object_key: str, expires_in: int = 900) -> str:
        encoded_key = quote(object_key, safe="/")
        payload: dict[str, Any] | None = None
        for attempt in range(2):
            try:
                payload = self._storage_request(
                    "POST",
                    f"/storage/v1/object/upload/sign/{bucket}/{encoded_key}",
                    payload={"expiresIn": expires_in},
                )
                break
            except WorkerError as exc:
                if attempt == 0 and self._is_duplicate_storage_error(str(exc)):
                    self.remove_object(bucket=bucket, object_key=object_key)
                    continue
                raise
        if payload is None:
            raise WorkerError("signed upload url request failed without payload")
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

    def remove_object(self, *, bucket: str, object_key: str) -> None:
        encoded_key = quote(object_key, safe="/")
        try:
            self._storage_request("DELETE", f"/storage/v1/object/{bucket}/{encoded_key}")
        except WorkerError as exc:
            # Deleting an already missing object is fine for idempotent retry handling.
            if " 404 " in str(exc):
                return
            raise

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        last_status: int | None = None
        last_error = ""

        for _attempt in range(2):
            upload_url = self.create_signed_upload_url(bucket=bucket, object_key=object_key)
            for method in ("PUT", "POST"):
                req = Request(url=upload_url, method=method, data=payload)
                req.add_header("Content-Type", "application/octet-stream")
                try:
                    with urlopen(req, timeout=60):
                        return
                except HTTPError as exc:
                    last_status = int(exc.code)
                    last_error = exc.read().decode("utf-8", errors="replace")
                    continue
                except URLError as exc:
                    last_status = None
                    last_error = str(exc)
                    continue

            if last_status == 409 or self._is_duplicate_storage_error(last_error):
                self.remove_object(bucket=bucket, object_key=object_key)
                continue

        raise WorkerError(
            f"upload failed for storage key={object_key} status={last_status} error={last_error[:500]}"
        )


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


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _expand_sheet_sizes(solver_input_payload: dict[str, Any]) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    stocks = solver_input_payload.get("stocks")
    if not isinstance(stocks, list):
        return out

    index = 0
    for stock in stocks:
        if not isinstance(stock, dict):
            continue
        width = float(stock.get("width") or 0.0)
        height = float(stock.get("height") or 0.0)
        qty = int(stock.get("quantity") or 0)
        if width <= 0 or height <= 0 or qty <= 0:
            continue
        for _ in range(qty):
            out[index] = (width, height)
            index += 1
    return out


def _part_sizes(solver_input_payload: dict[str, Any]) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    parts = solver_input_payload.get("parts")
    if not isinstance(parts, list):
        return out
    for part in parts:
        if not isinstance(part, dict):
            continue
        part_id = str(part.get("id", "")).strip()
        if not part_id:
            continue
        width = float(part.get("width") or 0.0)
        height = float(part.get("height") or 0.0)
        if width <= 0 or height <= 0:
            continue
        out[part_id] = (width, height)
    return out


def _fallback_color(part_id: str) -> str:
    digest = hashlib.sha1(part_id.encode("utf-8")).hexdigest()
    return "#" + digest[:6]


def _build_fallback_svg(
    *,
    width: float,
    height: float,
    placements: list[dict[str, Any]],
    part_sizes: dict[str, tuple[float, float]],
) -> str:
    safe_width = max(width, 1.0)
    safe_height = max(height, 1.0)

    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{safe_width:.3f}mm" height="{safe_height:.3f}mm" '
        f'viewBox="0 0 {safe_width:.3f} {safe_height:.3f}">'
    )
    lines.append(
        f'  <rect x="0" y="0" width="{safe_width:.3f}" height="{safe_height:.3f}" '
        'fill="#ffffff" stroke="#111827" stroke-width="1" />'
    )

    for placement in placements:
        part_id = str(placement.get("part_id", "")).strip()
        if not part_id:
            continue
        x = float(placement.get("x") or 0.0)
        y = float(placement.get("y") or 0.0)
        rotation = float(placement.get("rotation_deg") or 0.0)
        part_w, part_h = part_sizes.get(part_id, (10.0, 10.0))
        color = _fallback_color(part_id)
        transform = ""
        if rotation:
            transform = f' transform="rotate({rotation:.3f} {x:.3f} {y:.3f})"'
        label = escape(part_id)
        lines.append(
            f'  <rect x="{x:.3f}" y="{y:.3f}" width="{part_w:.3f}" height="{part_h:.3f}" '
            f'fill="{color}" fill-opacity="0.35" stroke="#0f172a" stroke-width="0.4"{transform} />'
        )
        lines.append(
            f'  <title>{label}</title>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _ensure_sheet_svgs(run_dir: Path) -> list[Path]:
    out_dir = run_dir / "out"
    if not out_dir.is_dir():
        return []

    solver_input_payload = _read_json_object(run_dir / "solver_input.json")
    solver_output_payload = _read_json_object(run_dir / "solver_output.json")

    sheet_sizes = _expand_sheet_sizes(solver_input_payload)
    part_dims = _part_sizes(solver_input_payload)

    grouped_placements: dict[int, list[dict[str, Any]]] = {}
    placements = solver_output_payload.get("placements")
    if isinstance(placements, list):
        for item in placements:
            if not isinstance(item, dict):
                continue
            sheet_index = item.get("sheet_index")
            if not isinstance(sheet_index, int):
                continue
            grouped_placements.setdefault(sheet_index, []).append(item)

    target_sheet_indexes: set[int] = set(grouped_placements.keys())
    for dxf_path in out_dir.glob("sheet_*.dxf"):
        if not dxf_path.is_file():
            continue
        token = dxf_path.stem.split("_", 1)[1] if "_" in dxf_path.stem else ""
        if token.isdigit():
            target_sheet_indexes.add(int(token) - 1)

    generated: list[Path] = []
    for sheet_index in sorted(target_sheet_indexes):
        svg_path = out_dir / f"sheet_{sheet_index + 1:03d}.svg"
        if svg_path.is_file() and svg_path.stat().st_size > 0:
            continue

        placements_for_sheet = grouped_placements.get(sheet_index, [])
        width, height = sheet_sizes.get(sheet_index, (1000.0, 1000.0))
        if sheet_index not in sheet_sizes and placements_for_sheet:
            max_x = 0.0
            max_y = 0.0
            for placement in placements_for_sheet:
                part_id = str(placement.get("part_id", "")).strip()
                part_w, part_h = part_dims.get(part_id, (10.0, 10.0))
                px = float(placement.get("x") or 0.0)
                py = float(placement.get("y") or 0.0)
                max_x = max(max_x, px + part_w)
                max_y = max(max_y, py + part_h)
            width = max(max_x + 10.0, width)
            height = max(max_y + 10.0, height)

        svg_payload = _build_fallback_svg(
            width=width,
            height=height,
            placements=placements_for_sheet,
            part_sizes=part_dims,
        )
        svg_path.write_text(svg_payload, encoding="utf-8")
        generated.append(svg_path)

    return generated


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


def _discover_cli_run_dir(run_root: Path) -> Path | None:
    if not run_root.is_dir():
        return None
    dirs = [path for path in run_root.iterdir() if path.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda path: path.name)
    return dirs[-1]


def _sync_run_log_artifact(
    *,
    client: WorkerSupabaseClient,
    settings: WorkerSettings,
    run_id: str,
    run_log_path: Path,
) -> int:
    if not run_log_path.is_file():
        return 0

    payload = run_log_path.read_bytes()
    storage_key = f"runs/{run_id}/artifacts/run.log"
    client.upload_object(bucket=settings.storage_bucket, object_key=storage_key, payload=payload)
    client.replace_run_log_artifact(run_id=run_id, storage_key=storage_key, size_bytes=len(payload))
    return len(payload)


def _upload_run_artifacts(
    *,
    client: WorkerSupabaseClient,
    settings: WorkerSettings,
    run_id: str,
    run_dir: Path,
) -> None:
    for artifact_path in run_dir.rglob("*"):
        if not artifact_path.is_file():
            continue
        relative = artifact_path.relative_to(run_dir)
        rel_text = relative.as_posix()
        if rel_text == "run.log":
            continue

        storage_key = f"runs/{run_id}/artifacts/{rel_text}"
        payload = artifact_path.read_bytes()
        client.upload_object(bucket=settings.storage_bucket, object_key=storage_key, payload=payload)
        artifact_type, sheet_index = _artifact_type_for_path(relative)
        client.insert_run_artifact(
            run_id=run_id,
            artifact_type=artifact_type,
            filename=rel_text,
            storage_key=storage_key,
            size_bytes=artifact_path.stat().st_size,
            sheet_index=sheet_index,
        )


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

        snapshot_text = json.dumps(project_payload, ensure_ascii=True, sort_keys=True)
        snapshot_hash = hashlib.sha256(snapshot_text.encode("utf-8")).hexdigest()
        snapshot_blob = (snapshot_text + "\n").encode("utf-8")

        project_json_path = input_dir / "project_dxf_v1.json"
        project_json_path.write_text(json.dumps(project_payload, ensure_ascii=True, indent=2), encoding="utf-8")

        client.upload_object(
            bucket=settings.storage_bucket,
            object_key=f"runs/{run_id}/inputs/project_snapshot.json",
            payload=snapshot_blob,
        )
        client.set_run_input_snapshot_hash(run_id=run_id, snapshot_hash=snapshot_hash)

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
        timeout_s = max(timeout_s, 30)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        discovered_run_dir: Path | None = None
        last_log_size = -1
        next_log_sync_at = 0.0
        cancel_requested = False
        timeout_hit = False
        deadline = time.monotonic() + timeout_s

        while proc.poll() is None:
            now = time.monotonic()
            if now >= deadline:
                timeout_hit = True
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break

            run_status = client.fetch_run_status(run_id)
            if run_status == "cancelled":
                cancel_requested = True
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break

            if discovered_run_dir is None:
                discovered_run_dir = _discover_cli_run_dir(run_root)

            if discovered_run_dir is not None and now >= next_log_sync_at:
                next_log_sync_at = now + settings.run_log_sync_interval_s
                run_log_path = discovered_run_dir / "run.log"
                if run_log_path.is_file():
                    current_size = run_log_path.stat().st_size
                    if current_size != last_log_size:
                        try:
                            last_log_size = _sync_run_log_artifact(
                                client=client,
                                settings=settings,
                                run_id=run_id,
                                run_log_path=run_log_path,
                            )
                        except WorkerError:
                            pass

            time.sleep(1.0)

        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

        run_dir: Path | None = discovered_run_dir
        if proc.returncode == 0:
            run_dir = _find_run_dir_from_stdout(stdout)

        if run_dir is not None:
            run_log_path = run_dir / "run.log"
            if run_log_path.is_file():
                _sync_run_log_artifact(
                    client=client,
                    settings=settings,
                    run_id=run_id,
                    run_log_path=run_log_path,
                )

        if cancel_requested:
            raise WorkerCancelledError(f"run {run_id}: cancelled by user")
        if timeout_hit:
            raise WorkerTimeoutError(f"run {run_id}: timeout exceeded ({timeout_s}s)")
        if proc.returncode != 0:
            stderr_text = (stderr or "").strip()
            raise WorkerError(f"run {run_id}: dxf-run failed (exit={proc.returncode}): {stderr_text[:2000]}")
        if run_dir is None:
            raise WorkerError(f"run {run_id}: cannot locate run_dir")

        _ensure_sheet_svgs(run_dir)
        _upload_run_artifacts(client=client, settings=settings, run_id=run_id, run_dir=run_dir)

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

    except WorkerCancelledError as exc:
        client.mark_run_cancelled(run_id=run_id, message=str(exc))
        client.complete_queue_item(queue_id=queue_id)
        raise
    except Exception as exc:
        message = str(exc)
        current_status = client.fetch_run_status(run_id)
        if current_status == "cancelled":
            client.mark_run_cancelled(run_id=run_id, message=message)
            client.complete_queue_item(queue_id=queue_id)
            raise

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
