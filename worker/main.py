#!/usr/bin/env python3
"""Phase 2 worker loop: queue claim, run processing, artifact upload."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
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

from worker.engine_adapter_input import (
    EngineAdapterInputError,
    build_solver_input_from_snapshot,
    solver_input_sha256,
    solver_runtime_params,
)
from worker.queue_lease import claim_next_queue_lease, heartbeat_queue_lease
from worker.raw_output_artifacts import persist_raw_output_artifacts
from worker.result_normalizer import normalize_solver_output_projection


class WorkerError(RuntimeError):
    pass


class WorkerSettingsError(WorkerError):
    pass


class WorkerCancelledError(WorkerError):
    pass


class WorkerTimeoutError(WorkerError):
    pass


class WorkerLeaseLostError(WorkerError):
    pass


logger = logging.getLogger("vrs_worker")


def _configure_logging() -> None:
    if logger.handlers:
        return
    level_name = _resolve_env("WORKER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s",
    )


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


def _sql_float_literal(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{float(value):.5f}"


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
    alert_backlog_seconds: int
    run_timeout_extra_s: int
    run_log_sync_interval_s: float
    queue_heartbeat_s: float
    queue_lease_ttl_s: int
    stale_temp_cleanup_max_age_s: float
    run_root: Path
    temp_root: Path
    run_artifacts_bucket: str
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
    alert_backlog_seconds = int(_resolve_env("WORKER_ALERT_BACKLOG_SECONDS", "300"))
    timeout_extra_s = int(_resolve_env("WORKER_TIMEOUT_EXTRA_S", "120"))
    log_sync_interval_s = float(_resolve_env("WORKER_RUN_LOG_SYNC_INTERVAL_S", "2"))
    queue_heartbeat_s = float(_resolve_env("WORKER_QUEUE_HEARTBEAT_S", "60"))
    queue_lease_ttl_s = int(_resolve_env("WORKER_QUEUE_LEASE_TTL_S", "600"))
    stale_temp_cleanup_max_age_s = float(_resolve_env("WORKER_STALE_TEMP_MAX_AGE_S", "3600"))
    if log_sync_interval_s <= 0:
        raise WorkerSettingsError("WORKER_RUN_LOG_SYNC_INTERVAL_S must be > 0")
    if queue_heartbeat_s <= 0:
        raise WorkerSettingsError("WORKER_QUEUE_HEARTBEAT_S must be > 0")
    if queue_lease_ttl_s <= 0:
        raise WorkerSettingsError("WORKER_QUEUE_LEASE_TTL_S must be > 0")
    if queue_heartbeat_s >= float(queue_lease_ttl_s):
        raise WorkerSettingsError("WORKER_QUEUE_HEARTBEAT_S must be < WORKER_QUEUE_LEASE_TTL_S")
    if stale_temp_cleanup_max_age_s <= 0:
        raise WorkerSettingsError("WORKER_STALE_TEMP_MAX_AGE_S must be > 0")

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
        alert_backlog_seconds=alert_backlog_seconds,
        run_timeout_extra_s=timeout_extra_s,
        run_log_sync_interval_s=log_sync_interval_s,
        queue_heartbeat_s=queue_heartbeat_s,
        queue_lease_ttl_s=queue_lease_ttl_s,
        stale_temp_cleanup_max_age_s=stale_temp_cleanup_max_age_s,
        run_root=run_root,
        temp_root=temp_root,
        run_artifacts_bucket=_resolve_env("RUN_ARTIFACTS_BUCKET", "run-artifacts"),
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
        claim = claim_next_queue_lease(
            query=self._management_query,
            worker_id=worker_id,
            lease_ttl_seconds=self._settings.queue_lease_ttl_s,
            max_attempts=3,
        )
        if claim is None:
            return None
        return claim.as_worker_item()

    def heartbeat_queue_item(self, *, queue_id: str, worker_id: str, lease_token: str) -> bool:
        heartbeat = heartbeat_queue_lease(
            query=self._management_query,
            run_id=queue_id,
            worker_id=worker_id,
            lease_token=lease_token,
            lease_ttl_seconds=self._settings.queue_lease_ttl_s,
        )
        return heartbeat is not None

    def fetch_backlog_metrics(self) -> tuple[int, float]:
        sql = """
select
  count(*)::int as pending_count,
  coalesce(extract(epoch from (now() - min(q.created_at))), 0)::double precision as oldest_age_s
from app.run_queue q
join app.nesting_runs r on r.id = q.run_id
where q.available_at <= now()
  and (
    q.queue_state = 'pending'
    or (
      q.queue_state = 'leased'
      and (
        (q.lease_expires_at is not null and q.lease_expires_at <= now())
        or (
          q.lease_expires_at is null
          and q.leased_at is not null
          and q.leased_at < now() - interval '{int(self._settings.queue_lease_ttl_s)} seconds'
        )
      )
    )
  )
  and r.status::text in ('queued','running');
"""
        rows = self._management_query(sql)
        if not rows:
            return (0, 0.0)
        row = rows[0]
        return (int(row.get("pending_count") or 0), float(row.get("oldest_age_s") or 0.0))

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
from app.nesting_runs r
left join app.run_configs rc on rc.id = r.run_config_id
where r.id = {_sql_literal(run_id)}
limit 1;
"""
        rows = self._management_query(sql)
        if not rows:
            raise WorkerError(f"run not found: {run_id}")
        return rows[0]

    def fetch_run_snapshot(self, run_id: str) -> dict[str, Any]:
        sql = f"""
select
  s.run_id,
  s.status as snapshot_status,
  s.snapshot_version,
  s.snapshot_hash_sha256,
  s.project_manifest_jsonb,
  s.technology_manifest_jsonb,
  s.parts_manifest_jsonb,
  s.sheets_manifest_jsonb,
  s.geometry_manifest_jsonb,
  s.solver_config_jsonb,
  s.manufacturing_manifest_jsonb
from app.nesting_run_snapshots s
where s.run_id = {_sql_literal(run_id)}
limit 1;
"""
        rows = self._management_query(sql)
        if not rows:
            raise WorkerError(f"run snapshot not found: {run_id}")
        snapshot = rows[0]
        snapshot_status = str(snapshot.get("snapshot_status") or "").strip().lower()
        if snapshot_status != "ready":
            raise WorkerError(f"run snapshot is not ready: {run_id}")
        return snapshot

    def fetch_project_file(self, file_id: str) -> dict[str, Any]:
        sql = f"""
select
  id,
  file_name as original_filename,
  storage_path as storage_key,
  file_kind::text as file_type,
  storage_bucket
from app.file_objects
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
from app.nesting_runs
where id = {_sql_literal(run_id)}
limit 1;
"""
        rows = self._management_query(sql)
        if not rows:
            return ""
        return str(rows[0].get("status", "")).strip().lower()

    def mark_run_running(self, run_id: str) -> None:
        sql = f"""
update app.nesting_runs
set status = 'running'::app.run_request_status,
    started_at = now(),
    finished_at = null,
    duration_sec = null,
    solver_exit_code = null,
    error_message = null,
    updated_at = now()
where id = {_sql_literal(run_id)};

update app.run_queue
set attempt_status = 'running'::app.run_attempt_status,
    started_at = coalesce(started_at, now()),
    updated_at = now()
where run_id = {_sql_literal(run_id)}
  and queue_state = 'leased';
"""
        self._management_query(sql)

    def complete_run_done_and_dequeue(
        self,
        *,
        run_id: str,
        solver_exit_code: int,
        placements_count: int,
        unplaced_count: int,
        sheet_count: int,
    ) -> None:
        sql = f"""
with updated as (
  update app.nesting_runs
  set status = 'done'::app.run_request_status,
      finished_at = now(),
      duration_sec = extract(epoch from now() - coalesce(started_at, queued_at)),
      solver_exit_code = {solver_exit_code},
      placements_count = {placements_count},
      unplaced_count = {unplaced_count},
      sheet_count = {sheet_count},
      error_message = null,
      updated_at = now()
  where id = {_sql_literal(run_id)}
  returning id
)
delete from app.run_queue q
using updated u
where q.run_id = u.id;
"""
        self._management_query(sql)

    def complete_run_failed_and_dequeue(self, *, run_id: str, message: str) -> None:
        sql = f"""
with updated as (
  update app.nesting_runs
  set status = 'failed'::app.run_request_status,
      finished_at = now(),
      duration_sec = extract(epoch from now() - coalesce(started_at, queued_at)),
      error_message = {_sql_literal(message[:2000])},
      updated_at = now()
  where id = {_sql_literal(run_id)}
  returning id
)
delete from app.run_queue q
using updated u
where q.run_id = u.id;
"""
        self._management_query(sql)

    def requeue_run_with_delay(self, *, run_id: str, message: str, retry_delay_s: int) -> None:
        sql = f"""
with updated as (
  update app.nesting_runs
  set status = 'queued'::app.run_request_status,
      started_at = null,
      finished_at = null,
      duration_sec = null,
      error_message = {_sql_literal(message[:2000])},
      updated_at = now()
  where id = {_sql_literal(run_id)}
  returning id
)
update app.run_queue q
set leased_by = null,
    lease_token = null,
    leased_at = null,
    lease_expires_at = null,
    heartbeat_at = null,
    attempt_status = 'failed'::app.run_attempt_status,
    queue_state = 'pending',
    available_at = now() + interval '{int(retry_delay_s)} seconds',
    updated_at = now()
from updated u
where q.run_id = u.id;
"""
        self._management_query(sql)

    def complete_run_cancelled_and_dequeue(self, *, run_id: str, message: str) -> None:
        sql = f"""
with updated as (
  update app.nesting_runs
  set status = 'cancelled'::app.run_request_status,
      finished_at = coalesce(finished_at, now()),
      duration_sec = extract(epoch from coalesce(finished_at, now()) - coalesce(started_at, queued_at)),
      error_message = {_sql_literal(message[:2000])},
      updated_at = now()
  where id = {_sql_literal(run_id)}
  returning id
)
delete from app.run_queue q
using updated u
where q.run_id = u.id;
"""
        self._management_query(sql)

    def set_run_input_snapshot_hash(self, *, run_id: str, snapshot_hash: str) -> None:
        sql = f"""
update app.nesting_runs
set request_payload_jsonb = coalesce(request_payload_jsonb, '{{}}'::jsonb)
    || jsonb_build_object('input_snapshot_hash', {_sql_literal(snapshot_hash)}),
    updated_at = now()
where id = {_sql_literal(run_id)};
"""
        self._management_query(sql)

    def register_run_artifact_raw(
        self,
        *,
        run_id: str,
        artifact_kind: str,
        storage_bucket: str,
        storage_path: str,
        metadata_json: dict[str, Any],
    ) -> None:
        metadata_literal = _sql_literal(json.dumps(metadata_json, ensure_ascii=True, sort_keys=True))
        sql = f"""
insert into app.run_artifacts(
  run_id,
  artifact_kind,
  storage_bucket,
  storage_path,
  metadata_jsonb
)
values (
  {_sql_literal(run_id)},
  {_sql_literal(artifact_kind)}::app.artifact_kind,
  {_sql_literal(storage_bucket)},
  {_sql_literal(storage_path)},
  jsonb_strip_nulls({metadata_literal}::jsonb)
)
on conflict (run_id, storage_path)
do update
set artifact_kind = excluded.artifact_kind,
    storage_bucket = excluded.storage_bucket,
    metadata_jsonb = excluded.metadata_jsonb;
"""
        self._management_query(sql)

    def replace_run_projection(
        self,
        *,
        run_id: str,
        sheets: list[dict[str, Any]],
        placements: list[dict[str, Any]],
        unplaced: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> None:
        sheets_json = _sql_literal(json.dumps(sheets, ensure_ascii=True, sort_keys=True))
        placements_json = _sql_literal(json.dumps(placements, ensure_ascii=True, sort_keys=True))
        unplaced_json = _sql_literal(json.dumps(unplaced, ensure_ascii=True, sort_keys=True))
        metrics_json = _sql_literal(json.dumps(metrics.get("metrics_jsonb") or {}, ensure_ascii=True, sort_keys=True))

        placed_count = int(metrics.get("placed_count") or 0)
        unplaced_count = int(metrics.get("unplaced_count") or 0)
        used_sheet_count = int(metrics.get("used_sheet_count") or 0)
        utilization_ratio = metrics.get("utilization_ratio")
        remnant_value = metrics.get("remnant_value")

        sql = f"""
with
deleted_placements as (
  delete from app.run_layout_placements
  where run_id = {_sql_literal(run_id)}::uuid
),
deleted_sheets as (
  delete from app.run_layout_sheets
  where run_id = {_sql_literal(run_id)}::uuid
),
deleted_unplaced as (
  delete from app.run_layout_unplaced
  where run_id = {_sql_literal(run_id)}::uuid
),
sheet_rows as (
  select *
  from jsonb_to_recordset({sheets_json}::jsonb)
    as s(
      sheet_index integer,
      sheet_revision_id uuid,
      width_mm numeric,
      height_mm numeric,
      utilization_ratio numeric,
      metadata_jsonb jsonb
    )
),
inserted_sheets as (
  insert into app.run_layout_sheets(
    run_id,
    sheet_index,
    sheet_revision_id,
    width_mm,
    height_mm,
    utilization_ratio,
    metadata_jsonb
  )
  select
    {_sql_literal(run_id)}::uuid,
    s.sheet_index,
    s.sheet_revision_id,
    s.width_mm,
    s.height_mm,
    s.utilization_ratio,
    coalesce(s.metadata_jsonb, '{{}}'::jsonb)
  from sheet_rows s
  order by s.sheet_index
  returning id, sheet_index
),
placement_rows as (
  select *
  from jsonb_to_recordset({placements_json}::jsonb)
    as p(
      sheet_index integer,
      placement_index integer,
      part_revision_id uuid,
      quantity integer,
      transform_jsonb jsonb,
      bbox_jsonb jsonb,
      metadata_jsonb jsonb
    )
),
inserted_placements as (
  insert into app.run_layout_placements(
    run_id,
    sheet_id,
    placement_index,
    part_revision_id,
    quantity,
    transform_jsonb,
    bbox_jsonb,
    metadata_jsonb
  )
  select
    {_sql_literal(run_id)}::uuid,
    s.id,
    p.placement_index,
    p.part_revision_id,
    coalesce(p.quantity, 1),
    coalesce(p.transform_jsonb, '{{}}'::jsonb),
    coalesce(p.bbox_jsonb, '{{}}'::jsonb),
    coalesce(p.metadata_jsonb, '{{}}'::jsonb)
  from placement_rows p
  join inserted_sheets s
    on s.sheet_index = p.sheet_index
),
unplaced_rows as (
  select *
  from jsonb_to_recordset({unplaced_json}::jsonb)
    as u(
      part_revision_id uuid,
      remaining_qty integer,
      reason text,
      metadata_jsonb jsonb
    )
),
inserted_unplaced as (
  insert into app.run_layout_unplaced(
    run_id,
    part_revision_id,
    remaining_qty,
    reason,
    metadata_jsonb
  )
  select
    {_sql_literal(run_id)}::uuid,
    u.part_revision_id,
    u.remaining_qty,
    u.reason,
    coalesce(u.metadata_jsonb, '{{}}'::jsonb)
  from unplaced_rows u
)
insert into app.run_metrics(
  run_id,
  placed_count,
  unplaced_count,
  used_sheet_count,
  utilization_ratio,
  remnant_value,
  metrics_jsonb
)
values (
  {_sql_literal(run_id)}::uuid,
  {placed_count},
  {unplaced_count},
  {used_sheet_count},
  {_sql_float_literal(utilization_ratio if isinstance(utilization_ratio, (int, float)) else None)},
  {_sql_float_literal(remnant_value if isinstance(remnant_value, (int, float)) else None)},
  jsonb_strip_nulls({metrics_json}::jsonb)
)
on conflict (run_id)
do update
set placed_count = excluded.placed_count,
    unplaced_count = excluded.unplaced_count,
    used_sheet_count = excluded.used_sheet_count,
    utilization_ratio = excluded.utilization_ratio,
    remnant_value = excluded.remnant_value,
    metrics_jsonb = excluded.metrics_jsonb,
    created_at = now();
"""
        self._management_query(sql)

    def insert_run_artifact(
        self,
        *,
        run_id: str,
        storage_bucket: str,
        artifact_type: str,
        filename: str,
        storage_key: str,
        size_bytes: int,
        sheet_index: int | None,
    ) -> None:
        metadata_json = json.dumps(
            {
                "legacy_artifact_type": artifact_type,
                "filename": filename,
                "size_bytes": int(size_bytes),
                "sheet_index": sheet_index,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        sql = f"""
delete from app.run_artifacts
where run_id = {_sql_literal(run_id)}
  and storage_path = {_sql_literal(storage_key)};

insert into app.run_artifacts(
  run_id,
  artifact_kind,
  storage_bucket,
  storage_path,
  metadata_jsonb
)
values (
  {_sql_literal(run_id)},
  app.legacy_artifact_type_to_kind({_sql_literal(artifact_type)}),
  {_sql_literal(storage_bucket)},
  {_sql_literal(storage_key)},
  jsonb_strip_nulls({_sql_literal(metadata_json)}::jsonb)
);
"""
        self._management_query(sql)

    def replace_run_log_artifact(self, *, run_id: str, storage_bucket: str, storage_key: str, size_bytes: int) -> None:
        self.insert_run_artifact(
            run_id=run_id,
            storage_bucket=storage_bucket,
            artifact_type="run_log",
            filename="run.log",
            storage_key=storage_key,
            size_bytes=int(size_bytes),
            sheet_index=None,
        )

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
    solver_output_json = run_dir / "solver_output.json"
    if solver_output_json.is_file():
        payload = _read_json_object(solver_output_json)
        placements_raw = payload.get("placements")
        unplaced_raw = payload.get("unplaced")
        placements = [item for item in placements_raw if isinstance(item, dict)] if isinstance(placements_raw, list) else []
        unplaced = [item for item in unplaced_raw if isinstance(item, dict)] if isinstance(unplaced_raw, list) else []
        sheet_indexes = [int(item["sheet_index"]) for item in placements if isinstance(item.get("sheet_index"), int)]
        sheet_count = (max(sheet_indexes) + 1) if sheet_indexes else 0
        return len(placements), len(unplaced), sheet_count

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
        raise WorkerError("runner returned empty stdout; run_dir path missing")
    return Path(lines[-1]).resolve()


def _discover_cli_run_dir(run_root: Path) -> Path | None:
    if not run_root.is_dir():
        return None
    dirs = [path for path in run_root.iterdir() if path.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda path: path.name)
    return dirs[-1]


@dataclass(frozen=True)
class SolverRunnerInvocation:
    cmd: list[str]
    run_dir: Path
    timeout_s: int


def _build_solver_runner_invocation(
    *,
    settings: WorkerSettings,
    run_id: str,
    run_root: Path,
    solver_input_path: Path,
    solver_input_payload: dict[str, Any],
) -> SolverRunnerInvocation:
    seed, time_limit_s = solver_runtime_params(solver_input_payload)
    run_dir = (run_root / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3",
        "-m",
        "vrs_nesting.runner.vrs_solver_runner",
        "--input",
        str(solver_input_path),
        "--seed",
        str(seed),
        "--time-limit",
        str(time_limit_s),
        "--run-dir",
        str(run_dir),
    ]
    timeout_s = max(int(time_limit_s) + int(settings.run_timeout_extra_s), 30)
    return SolverRunnerInvocation(cmd=cmd, run_dir=run_dir, timeout_s=timeout_s)


def _validate_solver_output_contract(run_dir: Path) -> None:
    output_path = run_dir / "solver_output.json"
    payload = _read_json_object(output_path)
    if payload.get("contract_version") != "v1":
        raise WorkerError(f"invalid solver output contract_version in {output_path}")
    placements = payload.get("placements")
    unplaced = payload.get("unplaced")
    if not isinstance(placements, list) or not isinstance(unplaced, list):
        raise WorkerError(f"invalid solver output structure in {output_path}")


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
    client.replace_run_log_artifact(
        run_id=run_id,
        storage_bucket=settings.storage_bucket,
        storage_key=storage_key,
        size_bytes=len(payload),
    )
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
            storage_bucket=settings.storage_bucket,
            artifact_type=artifact_type,
            filename=rel_text,
            storage_key=storage_key,
            size_bytes=artifact_path.stat().st_size,
            sheet_index=sheet_index,
        )


def _process_queue_item(client: WorkerSupabaseClient, settings: WorkerSettings, item: dict[str, Any]) -> None:
    queue_id = str(item.get("id", "")).strip()
    run_id = str(item.get("run_id", "")).strip()
    lease_token = str(item.get("lease_token", "")).strip()
    attempts = int(item.get("attempts") or 0)
    max_attempts = int(item.get("max_attempts") or 3)
    if not queue_id or not run_id:
        raise WorkerError("queue claim returned missing id/run_id")
    if not lease_token:
        raise WorkerError("queue claim returned missing lease_token")

    client.mark_run_running(run_id)

    job_temp_dir = Path(tempfile.mkdtemp(prefix=f"{run_id}_", dir=settings.temp_root))
    run_root = job_temp_dir / "runs"
    input_dir = job_temp_dir / "input"
    run_root.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)

    try:
        snapshot_row = client.fetch_run_snapshot(run_id)
        project_manifest = snapshot_row.get("project_manifest_jsonb")
        if not isinstance(project_manifest, dict):
            raise WorkerError(f"run {run_id}: snapshot missing project_manifest_jsonb")
        project_id = str(project_manifest.get("project_id") or "").strip()
        if not project_id:
            raise WorkerError(f"run {run_id}: snapshot missing project_id")
        try:
            solver_input_payload = build_solver_input_from_snapshot(snapshot_row)
        except EngineAdapterInputError as exc:
            raise WorkerError(f"run {run_id}: snapshot->solver_input mapping failed: {exc}") from exc

        solver_input_hash = solver_input_sha256(solver_input_payload)
        solver_input_blob = (json.dumps(solver_input_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        solver_input_snapshot_path = input_dir / "solver_input_snapshot_v1.json"
        solver_input_snapshot_path.write_text(
            json.dumps(solver_input_payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        client.upload_object(
            bucket=settings.storage_bucket,
            object_key=f"runs/{run_id}/inputs/solver_input_snapshot.json",
            payload=solver_input_blob,
        )
        client.set_run_input_snapshot_hash(run_id=run_id, snapshot_hash=solver_input_hash)

        solver_input_runtime_path = input_dir / "solver_input.json"
        solver_input_runtime_path.write_bytes(solver_input_blob)
        invocation = _build_solver_runner_invocation(
            settings=settings,
            run_id=run_id,
            run_root=run_root,
            solver_input_path=solver_input_runtime_path,
            solver_input_payload=solver_input_payload,
        )
        cmd = invocation.cmd
        timeout_s = invocation.timeout_s

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        discovered_run_dir: Path | None = invocation.run_dir
        next_heartbeat_at = 0.0
        cancel_requested = False
        timeout_hit = False
        lease_lost = False
        deadline = time.monotonic() + timeout_s

        try:
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

                if now >= next_heartbeat_at:
                    next_heartbeat_at = now + settings.queue_heartbeat_s
                    try:
                        heartbeat_ok = client.heartbeat_queue_item(
                            queue_id=queue_id,
                            worker_id=settings.worker_id,
                            lease_token=lease_token,
                        )
                        if not heartbeat_ok:
                            lease_lost = True
                            logger.warning(
                                "event=queue_lease_lost worker_id=%s run_id=%s queue_id=%s",
                                settings.worker_id,
                                run_id,
                                queue_id,
                            )
                            proc.terminate()
                            try:
                                proc.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                            break
                    except WorkerError as exc:
                        logger.warning(
                            "event=queue_heartbeat_failed worker_id=%s run_id=%s queue_id=%s error=%s",
                            settings.worker_id,
                            run_id,
                            queue_id,
                            exc,
                        )

                if discovered_run_dir is None:
                    discovered_run_dir = _discover_cli_run_dir(run_root)

                time.sleep(1.0)

            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
        finally:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass

        run_dir: Path | None = discovered_run_dir
        if proc.returncode == 0:
            stdout_run_dir = _find_run_dir_from_stdout(stdout)
            if run_dir is None:
                run_dir = stdout_run_dir
            elif run_dir != stdout_run_dir:
                logger.warning(
                    "event=runner_run_dir_mismatch expected=%s reported=%s",
                    run_dir,
                    stdout_run_dir,
                )
                run_dir = stdout_run_dir

        if run_dir is not None:
            try:
                persisted = persist_raw_output_artifacts(
                    run_dir=run_dir,
                    project_id=project_id,
                    run_id=run_id,
                    storage_bucket=settings.run_artifacts_bucket,
                    upload_object=client.upload_object,
                    register_artifact=client.register_run_artifact_raw,
                )
                logger.info(
                    "event=raw_artifacts_persisted run_id=%s project_id=%s count=%s",
                    run_id,
                    project_id,
                    len(persisted),
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "event=raw_artifacts_persist_failed run_id=%s project_id=%s error=%s",
                    run_id,
                    project_id,
                    exc,
                )

        if cancel_requested:
            raise WorkerCancelledError(f"run {run_id}: cancelled by user")
        if timeout_hit:
            raise WorkerTimeoutError(f"run {run_id}: timeout exceeded ({timeout_s}s)")
        if lease_lost:
            raise WorkerLeaseLostError(f"run {run_id}: queue lease lost during processing")
        if proc.returncode != 0:
            stderr_text = (stderr or "").strip()
            raise WorkerError(f"run {run_id}: solver runner failed (exit={proc.returncode}): {stderr_text[:2000]}")
        if run_dir is None:
            raise WorkerError(f"run {run_id}: cannot locate run_dir")

        _validate_solver_output_contract(run_dir)
        projection = normalize_solver_output_projection(
            run_id=run_id,
            snapshot_row=snapshot_row,
            run_dir=run_dir,
        )
        client.replace_run_projection(
            run_id=run_id,
            sheets=projection.sheets,
            placements=projection.placements,
            unplaced=projection.unplaced,
            metrics=projection.metrics,
        )
        client.complete_run_done_and_dequeue(
            run_id=run_id,
            solver_exit_code=0,
            placements_count=projection.summary.placed_count,
            unplaced_count=projection.summary.unplaced_count,
            sheet_count=projection.summary.used_sheet_count,
        )

    except WorkerCancelledError as exc:
        try:
            client.complete_run_cancelled_and_dequeue(run_id=run_id, message=str(exc))
        except Exception as inner_exc:  # noqa: BLE001
            logger.error(
                "event=cancel_handler_failed run_id=%s queue_id=%s error=%s original=%s",
                run_id,
                queue_id,
                inner_exc,
                exc,
            )
        raise
    except WorkerLeaseLostError:
        raise
    except Exception as exc:
        try:
            message = str(exc)
            current_status = client.fetch_run_status(run_id)
            if current_status == "cancelled":
                client.complete_run_cancelled_and_dequeue(run_id=run_id, message=message)
            elif attempts >= max_attempts:
                client.complete_run_failed_and_dequeue(run_id=run_id, message=message)
            else:
                client.requeue_run_with_delay(run_id=run_id, message=message, retry_delay_s=settings.retry_delay_s)
        except Exception as inner_exc:  # noqa: BLE001
            logger.error(
                "event=error_handler_failed run_id=%s queue_id=%s error=%s original=%s",
                run_id,
                queue_id,
                inner_exc,
                exc,
            )
        raise
    finally:
        shutil.rmtree(job_temp_dir, ignore_errors=True)


def _cleanup_stale_temp_dirs(temp_root: Path, *, max_age_s: float) -> None:
    cutoff = time.time() - max_age_s
    for entry in temp_root.iterdir():
        if not entry.is_dir():
            continue
        try:
            if entry.stat().st_mtime >= cutoff:
                continue
        except OSError:
            continue
        shutil.rmtree(entry, ignore_errors=True)


def run_worker_loop(settings: WorkerSettings) -> int:
    settings.temp_root.mkdir(parents=True, exist_ok=True)
    settings.run_root.mkdir(parents=True, exist_ok=True)
    _cleanup_stale_temp_dirs(settings.temp_root, max_age_s=settings.stale_temp_cleanup_max_age_s)

    client = WorkerSupabaseClient(settings)
    last_processed_at = time.monotonic()
    last_alert_at = 0.0

    while True:
        item = client.claim_next_queue_item(settings.worker_id)
        if item is None:
            if settings.once:
                return 0
            now = time.monotonic()
            if now - last_processed_at >= float(settings.alert_backlog_seconds) and (
                now - last_alert_at >= float(settings.alert_backlog_seconds)
            ):
                pending_count, oldest_age_s = client.fetch_backlog_metrics()
                if pending_count > 0:
                    logger.error(
                        "event=worker_backlog_alert worker_id=%s threshold_s=%s pending_count=%s oldest_age_s=%.1f",
                        settings.worker_id,
                        settings.alert_backlog_seconds,
                        pending_count,
                        oldest_age_s,
                    )
                    last_alert_at = now
            time.sleep(settings.poll_interval_s)
            continue

        last_processed_at = time.monotonic()
        run_id = str(item.get("run_id", ""))
        queue_id = str(item.get("id", ""))
        try:
            _process_queue_item(client, settings, item)
            logger.info(
                "event=run_processed worker_id=%s run_id=%s queue_id=%s",
                settings.worker_id,
                run_id,
                queue_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "event=run_processing_error worker_id=%s run_id=%s queue_id=%s error=%s",
                settings.worker_id,
                run_id,
                queue_id,
                exc,
            )

        if settings.once:
            return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VRS worker loop")
    parser.add_argument("--once", action="store_true", help="Process at most one queue item then exit")
    parser.add_argument("--poll-interval-s", type=float, default=None, help="Polling interval in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    args = build_parser().parse_args(argv)
    settings = load_settings(once=bool(args.once), poll_interval_s=args.poll_interval_s)
    return run_worker_loop(settings)


if __name__ == "__main__":
    raise SystemExit(main())
