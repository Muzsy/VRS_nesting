#!/usr/bin/env python3
"""Phase 2 worker loop: queue claim, run processing, artifact upload."""

from __future__ import annotations

import argparse
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
from uuid import UUID

from vrs_nesting.config.nesting_quality_profiles import (
    DEFAULT_QUALITY_PROFILE,
    build_nesting_engine_cli_args_from_runtime_policy,
    compact_runtime_policy,
    normalize_quality_profile_name,
    runtime_policy_for_quality_profile,
    validate_runtime_policy,
)
from worker.engine_adapter_input import (
    EngineAdapterInputError,
    build_nesting_engine_input_from_snapshot,
    build_solver_input_from_snapshot,
    nesting_engine_input_sha256,
    nesting_engine_runtime_params,
    solver_input_sha256,
    solver_runtime_params,
)
from worker.queue_lease import claim_next_queue_lease, heartbeat_queue_lease
from worker.raw_output_artifacts import persist_raw_output_artifacts
from worker.result_normalizer import assert_projection_within_sheet_bounds, normalize_solver_output_projection
from worker.sheet_dxf_artifacts import persist_sheet_dxf_artifacts
from worker.sheet_svg_artifacts import persist_sheet_svg_artifacts


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

ENGINE_BACKEND_SPARROW_V1 = "sparrow_v1"
ENGINE_BACKEND_NESTING_V2 = "nesting_engine_v2"
_SUPPORTED_WORKER_ENGINE_BACKENDS = (ENGINE_BACKEND_SPARROW_V1, ENGINE_BACKEND_NESTING_V2)


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


def _resolve_worker_engine_backend(raw: str) -> str:
    cleaned = str(raw or "").strip().lower() or ENGINE_BACKEND_SPARROW_V1
    if cleaned not in _SUPPORTED_WORKER_ENGINE_BACKENDS:
        raise WorkerSettingsError(
            "WORKER_ENGINE_BACKEND must be one of: "
            + ", ".join(_SUPPORTED_WORKER_ENGINE_BACKENDS)
        )
    return cleaned


def _resolve_worker_quality_profile_override(raw: str) -> str | None:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return None
    try:
        return normalize_quality_profile_name(cleaned, default=DEFAULT_QUALITY_PROFILE)
    except ValueError as exc:
        raise WorkerSettingsError(str(exc)) from exc


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_uuid_literal(value: str, *, field: str) -> str:
    try:
        normalized = str(UUID(str(value).strip()))
    except Exception as exc:  # noqa: BLE001
        raise WorkerError(f"invalid {field}") from exc
    return _sql_literal(normalized)


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
    engine_backend: str = ENGINE_BACKEND_SPARROW_V1
    quality_profile_override: str | None = None


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
    engine_backend = _resolve_worker_engine_backend(
        _resolve_env("WORKER_ENGINE_BACKEND", ENGINE_BACKEND_SPARROW_V1)
    )
    quality_profile_override = _resolve_worker_quality_profile_override(
        _resolve_env("WORKER_QUALITY_PROFILE", "")
    )

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
        engine_backend=engine_backend,
        quality_profile_override=quality_profile_override,
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
        lease_ttl_s = int(self._settings.queue_lease_ttl_s)
        sql = f"""
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
          and q.leased_at < now() - make_interval(secs => {lease_ttl_s})
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

    def fetch_viewer_outline_derivatives(self, *, geometry_revision_ids: list[str]) -> dict[str, dict[str, Any]]:
        cleaned_ids: set[str] = set()
        for idx, raw in enumerate(geometry_revision_ids):
            value = str(raw or "").strip()
            if not value:
                raise WorkerError(f"invalid geometry_revision_ids[{idx}]")
            cleaned_ids.add(value)
        if not cleaned_ids:
            return {}

        in_list = ", ".join(_sql_literal(value) for value in sorted(cleaned_ids))
        sql = f"""
select
  gd.geometry_revision_id::text as geometry_revision_id,
  gd.derivative_jsonb
from app.geometry_derivatives gd
where gd.derivative_kind = 'viewer_outline'::app.geometry_derivative_kind
  and gd.geometry_revision_id in ({in_list})
order by gd.geometry_revision_id asc;
"""
        rows = self._management_query(sql)
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            geometry_revision_id = str(row.get("geometry_revision_id") or "").strip()
            derivative_json = row.get("derivative_jsonb")
            if not geometry_revision_id or not isinstance(derivative_json, dict):
                continue
            out[geometry_revision_id] = derivative_json
        return out

    def fetch_nesting_canonical_derivatives(self, *, geometry_revision_ids: list[str]) -> dict[str, dict[str, Any]]:
        cleaned_ids: set[str] = set()
        for idx, raw in enumerate(geometry_revision_ids):
            value = str(raw or "").strip()
            if not value:
                raise WorkerError(f"invalid geometry_revision_ids[{idx}]")
            cleaned_ids.add(value)
        if not cleaned_ids:
            return {}

        in_list = ", ".join(_sql_literal(value) for value in sorted(cleaned_ids))
        sql = f"""
select
  gd.geometry_revision_id::text as geometry_revision_id,
  gd.derivative_jsonb
from app.geometry_derivatives gd
where gd.derivative_kind = 'nesting_canonical'::app.geometry_derivative_kind
  and gd.geometry_revision_id in ({in_list})
order by gd.geometry_revision_id asc;
"""
        rows = self._management_query(sql)
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            geometry_revision_id = str(row.get("geometry_revision_id") or "").strip()
            derivative_json = row.get("derivative_jsonb")
            if not geometry_revision_id or not isinstance(derivative_json, dict):
                continue
            out[geometry_revision_id] = derivative_json
        return out

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
  {_sql_uuid_literal(run_id, field="run_id")}::uuid,
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
        run_id_sql = _sql_uuid_literal(run_id, field="run_id")

        sql = f"""
with
deleted_placements as (
  delete from app.run_layout_placements
  where run_id = {run_id_sql}::uuid
),
deleted_sheets as (
  delete from app.run_layout_sheets
  where run_id = {run_id_sql}::uuid
),
deleted_unplaced as (
  delete from app.run_layout_unplaced
  where run_id = {run_id_sql}::uuid
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
    {run_id_sql}::uuid,
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
    {run_id_sql}::uuid,
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
    {run_id_sql}::uuid,
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
  {run_id_sql}::uuid,
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
    if name in {"solver_output.json", "nesting_output.json"}:
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


def _snapshot_source_geometry_revision_ids(snapshot_row: dict[str, Any]) -> list[str]:
    parts_manifest_raw = snapshot_row.get("parts_manifest_jsonb")
    if not isinstance(parts_manifest_raw, list):
        raise WorkerError("snapshot missing parts_manifest_jsonb")

    source_ids: set[str] = set()
    for idx, part in enumerate(parts_manifest_raw):
        if not isinstance(part, dict):
            continue
        source_geometry_revision_id = str(part.get("source_geometry_revision_id") or "").strip()
        if not source_geometry_revision_id:
            raise WorkerError(f"snapshot missing source_geometry_revision_id at parts_manifest_jsonb[{idx}]")
        source_ids.add(source_geometry_revision_id)

    if not source_ids:
        raise WorkerError("snapshot has no source_geometry_revision_id entries")
    return sorted(source_ids)


@dataclass(frozen=True)
class EngineProfileResolution:
    requested_engine_profile: str
    effective_engine_profile: str
    engine_profile_match: bool | None
    profile_resolution_source: str
    runtime_policy_source: str
    profile_effect: str
    nesting_engine_runtime_policy: dict[str, Any]
    nesting_engine_cli_args: list[str]


def _resolve_engine_profile_resolution(
    *,
    snapshot_row: dict[str, Any],
    settings: WorkerSettings,
    engine_backend: str,
) -> EngineProfileResolution:
    solver_config_raw = snapshot_row.get("solver_config_jsonb")
    solver_config = solver_config_raw if isinstance(solver_config_raw, dict) else {}

    snapshot_quality_profile = str(solver_config.get("quality_profile") or "").strip()
    if settings.quality_profile_override:
        requested_profile = normalize_quality_profile_name(
            settings.quality_profile_override,
            default=DEFAULT_QUALITY_PROFILE,
        )
        profile_resolution_source = "runtime_override"
    elif snapshot_quality_profile:
        requested_profile = normalize_quality_profile_name(
            snapshot_quality_profile,
            default=DEFAULT_QUALITY_PROFILE,
        )
        profile_resolution_source = "snapshot_solver_config"
    else:
        requested_profile = DEFAULT_QUALITY_PROFILE
        profile_resolution_source = "default"

    registry_policy = compact_runtime_policy(runtime_policy_for_quality_profile(requested_profile))
    runtime_policy = dict(registry_policy)
    runtime_policy_source = "registry"

    snapshot_runtime_policy_raw = solver_config.get("nesting_engine_runtime_policy")
    if profile_resolution_source != "runtime_override" and isinstance(snapshot_runtime_policy_raw, dict):
        try:
            runtime_policy = compact_runtime_policy(validate_runtime_policy(snapshot_runtime_policy_raw))
            runtime_policy_source = "snapshot_solver_config"
        except ValueError:
            runtime_policy = dict(registry_policy)
            runtime_policy_source = "registry_fallback_invalid_snapshot_policy"

    # Apply per-run sa_eval_budget_sec override from snapshot (set via API request)
    # regardless of profile resolution source.
    snapshot_sa_override = solver_config.get("sa_eval_budget_sec")
    if isinstance(snapshot_sa_override, int) and snapshot_sa_override > 0:
        runtime_policy["sa_eval_budget_sec"] = snapshot_sa_override

    if engine_backend == ENGINE_BACKEND_NESTING_V2:
        nesting_engine_cli_args = build_nesting_engine_cli_args_from_runtime_policy(runtime_policy)
        effective_profile = requested_profile
        profile_match: bool | None = True
        profile_effect = "applied_to_nesting_engine_v2"
    else:
        nesting_engine_cli_args = []
        effective_profile = "sparrow_v1_noop"
        profile_match = False
        profile_effect = "noop_non_nesting_backend"

    return EngineProfileResolution(
        requested_engine_profile=requested_profile,
        effective_engine_profile=effective_profile,
        engine_profile_match=profile_match,
        profile_resolution_source=profile_resolution_source,
        runtime_policy_source=runtime_policy_source,
        profile_effect=profile_effect,
        nesting_engine_runtime_policy=runtime_policy,
        nesting_engine_cli_args=nesting_engine_cli_args,
    )


@dataclass(frozen=True)
class SolverRunnerInvocation:
    cmd: list[str]
    run_dir: Path | None
    timeout_s: int
    solver_runner_module: str


def _build_solver_runner_invocation(
    *,
    settings: WorkerSettings,
    engine_backend: str,
    run_id: str,
    run_root: Path,
    solver_input_path: Path,
    solver_input_payload: dict[str, Any],
    nesting_engine_cli_args: list[str] | None = None,
) -> SolverRunnerInvocation:
    if engine_backend == ENGINE_BACKEND_SPARROW_V1:
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
        return SolverRunnerInvocation(
            cmd=cmd,
            run_dir=run_dir,
            timeout_s=timeout_s,
            solver_runner_module="vrs_nesting.runner.vrs_solver_runner",
        )

    if engine_backend == ENGINE_BACKEND_NESTING_V2:
        seed, time_limit_s = nesting_engine_runtime_params(solver_input_payload)
        extra_cli_args = [str(item) for item in (nesting_engine_cli_args or []) if str(item).strip()]
        cmd = [
            "python3",
            "-m",
            "vrs_nesting.runner.nesting_engine_runner",
            "--input",
            str(solver_input_path),
            "--seed",
            str(seed),
            "--time-limit",
            str(time_limit_s),
            "--run-root",
            str(run_root.resolve()),
            *extra_cli_args,
        ]
        timeout_s = max(int(time_limit_s) + int(settings.run_timeout_extra_s), 30)
        return SolverRunnerInvocation(
            cmd=cmd,
            run_dir=None,
            timeout_s=timeout_s,
            solver_runner_module="vrs_nesting.runner.nesting_engine_runner",
        )

    raise WorkerError(f"unsupported worker engine backend: {engine_backend}")


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
        engine_backend = settings.engine_backend
        profile_resolution = _resolve_engine_profile_resolution(
            snapshot_row=snapshot_row,
            settings=settings,
            engine_backend=engine_backend,
        )
        try:
            if engine_backend == ENGINE_BACKEND_SPARROW_V1:
                solver_input_payload = build_solver_input_from_snapshot(snapshot_row)
                solver_input_hash = solver_input_sha256(solver_input_payload)
                engine_contract_version = str(solver_input_payload.get("contract_version", "v1"))
            elif engine_backend == ENGINE_BACKEND_NESTING_V2:
                solver_input_payload = build_nesting_engine_input_from_snapshot(snapshot_row)
                solver_input_hash = nesting_engine_input_sha256(solver_input_payload)
                engine_contract_version = str(solver_input_payload.get("version", ENGINE_BACKEND_NESTING_V2))
            else:
                raise WorkerError(f"unsupported worker engine backend: {engine_backend}")
        except EngineAdapterInputError as exc:
            raise WorkerError(f"run {run_id}: snapshot->solver_input mapping failed: {exc}") from exc

        solver_input_blob = (json.dumps(solver_input_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        solver_input_snapshot_path = input_dir / "solver_input_snapshot.json"
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

        # --- Canonical solver input artifact registration ---
        # The solver_input_snapshot is the canonical source of truth for the
        # solver input.  Register it as a formal "solver_input" run artifact so
        # that the viewer-data endpoint (and any other consumer) can discover it
        # through the standard run_artifacts table instead of relying on
        # side-channel storage paths.
        solver_input_storage_key = f"runs/{run_id}/inputs/solver_input_snapshot.json"
        client.insert_run_artifact(
            run_id=run_id,
            storage_bucket=settings.storage_bucket,
            artifact_type="solver_input",
            filename="solver_input.json",
            storage_key=solver_input_storage_key,
            size_bytes=len(solver_input_blob),
            sheet_index=None,
        )

        # --- Engine meta artifact ---
        # Persist engine backend / contract / profile metadata as an explicit
        # artifact so that run evidence is self-describing without requiring
        # stderr log parsing.
        invocation = _build_solver_runner_invocation(
            settings=settings,
            engine_backend=engine_backend,
            run_id=run_id,
            run_root=run_root,
            solver_input_path=input_dir / "solver_input.json",
            solver_input_payload=solver_input_payload,
            nesting_engine_cli_args=profile_resolution.nesting_engine_cli_args,
        )
        engine_meta: dict[str, Any] = {
            "engine_backend": engine_backend,
            "engine_contract_version": engine_contract_version,
            "engine_profile": profile_resolution.requested_engine_profile,
            "requested_engine_profile": profile_resolution.requested_engine_profile,
            "effective_engine_profile": profile_resolution.effective_engine_profile,
            "engine_profile_match": profile_resolution.engine_profile_match,
            "profile_resolution_source": profile_resolution.profile_resolution_source,
            "runtime_policy_source": profile_resolution.runtime_policy_source,
            "profile_effect": profile_resolution.profile_effect,
            "nesting_engine_runtime_policy": profile_resolution.nesting_engine_runtime_policy,
            "nesting_engine_cli_args": list(profile_resolution.nesting_engine_cli_args),
            "solver_runner_module": invocation.solver_runner_module,
            "solver_input_hash": solver_input_hash,
        }
        engine_meta_blob = (
            json.dumps(engine_meta, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        engine_meta_storage_key = f"runs/{run_id}/artifacts/engine_meta.json"
        client.upload_object(
            bucket=settings.storage_bucket,
            object_key=engine_meta_storage_key,
            payload=engine_meta_blob,
        )
        client.register_run_artifact_raw(
            run_id=run_id,
            artifact_kind="log",
            storage_bucket=settings.storage_bucket,
            storage_path=engine_meta_storage_key,
            metadata_json={
                "legacy_artifact_type": "engine_meta",
                "filename": "engine_meta.json",
                "size_bytes": len(engine_meta_blob),
            },
        )
        logger.info(
            "event=engine_meta_persisted run_id=%s backend=%s contract=%s",
            run_id,
            engine_meta["engine_backend"],
            engine_meta["engine_contract_version"],
        )

        solver_input_runtime_path = input_dir / "solver_input.json"
        solver_input_runtime_path.write_bytes(solver_input_blob)
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

        projection = normalize_solver_output_projection(
            run_id=run_id,
            snapshot_row=snapshot_row,
            run_dir=run_dir,
        )
        assert_projection_within_sheet_bounds(
            sheets=projection.sheets,
            placements=projection.placements,
        )
        client.replace_run_projection(
            run_id=run_id,
            sheets=projection.sheets,
            placements=projection.placements,
            unplaced=projection.unplaced,
            metrics=projection.metrics,
        )
        source_geometry_revision_ids = _snapshot_source_geometry_revision_ids(snapshot_row)
        viewer_outline_by_geometry_revision = client.fetch_viewer_outline_derivatives(
            geometry_revision_ids=source_geometry_revision_ids
        )
        persisted_sheet_svgs = persist_sheet_svg_artifacts(
            project_id=project_id,
            run_id=run_id,
            storage_bucket=settings.run_artifacts_bucket,
            snapshot_row=snapshot_row,
            projection_sheets=projection.sheets,
            projection_placements=projection.placements,
            viewer_outline_by_geometry_revision=viewer_outline_by_geometry_revision,
            upload_object=client.upload_object,
            register_artifact=client.register_run_artifact_raw,
        )
        logger.info(
            "event=sheet_svg_artifacts_persisted run_id=%s project_id=%s count=%s",
            run_id,
            project_id,
            len(persisted_sheet_svgs),
        )
        nesting_canonical_by_geometry_revision = client.fetch_nesting_canonical_derivatives(
            geometry_revision_ids=source_geometry_revision_ids
        )
        persisted_sheet_dxf = persist_sheet_dxf_artifacts(
            project_id=project_id,
            run_id=run_id,
            storage_bucket=settings.run_artifacts_bucket,
            snapshot_row=snapshot_row,
            projection_sheets=projection.sheets,
            projection_placements=projection.placements,
            nesting_canonical_by_geometry_revision=nesting_canonical_by_geometry_revision,
            upload_object=client.upload_object,
            register_artifact=client.register_run_artifact_raw,
        )
        logger.info(
            "event=sheet_dxf_artifacts_persisted run_id=%s project_id=%s count=%s",
            run_id,
            project_id,
            len(persisted_sheet_dxf),
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


def _worker_ready_file() -> Path:
    return Path(__file__).resolve().parents[1] / ".cache" / "web_platform" / "worker.ready"


def _write_worker_ready(worker_id: str) -> None:
    ready_file = _worker_ready_file()
    ready_file.parent.mkdir(parents=True, exist_ok=True)
    ready_file.write_text(
        json.dumps({"worker_id": worker_id, "ready_at": time.time(), "pid": os.getpid()}) + "\n",
        encoding="utf-8",
    )
    logger.info("event=worker_ready worker_id=%s ready_file=%s", worker_id, ready_file)


def _remove_worker_ready() -> None:
    ready_file = _worker_ready_file()
    try:
        ready_file.unlink(missing_ok=True)
    except OSError:
        pass


def run_worker_loop(settings: WorkerSettings) -> int:
    settings.temp_root.mkdir(parents=True, exist_ok=True)
    settings.run_root.mkdir(parents=True, exist_ok=True)
    _cleanup_stale_temp_dirs(settings.temp_root, max_age_s=settings.stale_temp_cleanup_max_age_s)

    client = WorkerSupabaseClient(settings)
    last_processed_at = time.monotonic()
    last_alert_at = 0.0

    _write_worker_ready(settings.worker_id)

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
    try:
        return run_worker_loop(settings)
    finally:
        _remove_worker_ready()


if __name__ == "__main__":
    raise SystemExit(main())
