from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.services.run_snapshot_builder import RunSnapshotBuilderError, build_run_snapshot_payload
from api.supabase_client import SupabaseClient, SupabaseHTTPError


@dataclass
class RunCreationError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _sanitize_run_purpose(raw: str | None) -> str:
    cleaned = _sanitize_optional(raw) or "nesting"
    if not cleaned:
        raise RunCreationError(status_code=400, detail="invalid run_purpose")
    return cleaned


def _is_duplicate_error(exc: SupabaseHTTPError, *, constraint_hint: str) -> bool:
    text = str(exc)
    return constraint_hint in text or "duplicate key" in text


def _load_project_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,owner_user_id,lifecycle",
        "id": f"eq.{project_id}",
        "owner_user_id": f"eq.{owner_user_id}",
        "lifecycle": "neq.archived",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.projects", access_token=access_token, params=params)
    if not rows:
        raise RunCreationError(status_code=404, detail="project not found")
    return rows[0]


def _load_run_config_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_config_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,created_by",
        "id": f"eq.{run_config_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_configs", access_token=access_token, params=params)
    if not rows:
        raise RunCreationError(status_code=404, detail="run_config not found")

    row = rows[0]
    row_project_id = str(row.get("project_id") or "").strip()
    if row_project_id != project_id:
        raise RunCreationError(status_code=400, detail="run_config does not belong to project")

    created_by = str(row.get("created_by") or "").strip()
    if created_by != owner_user_id:
        raise RunCreationError(status_code=403, detail="run_config does not belong to owner")
    return row


def _fetch_run_row(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    project_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,run_config_id,requested_by,status,queued_at,started_at,finished_at,duration_sec,solver_exit_code,error_message,placements_count,unplaced_count,sheet_count",
        "id": f"eq.{run_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.nesting_runs", access_token=access_token, params=params)
    if not rows:
        raise RunCreationError(status_code=404, detail="run not found")
    return rows[0]


def _fetch_snapshot_for_run(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,run_id,status,snapshot_hash_sha256,snapshot_version,project_manifest_jsonb,technology_manifest_jsonb,parts_manifest_jsonb,sheets_manifest_jsonb,geometry_manifest_jsonb,solver_config_jsonb,manufacturing_manifest_jsonb,includes_manufacturing,includes_postprocess",
        "run_id": f"eq.{run_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.nesting_run_snapshots", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _fetch_existing_run_by_idempotency(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,project_id,run_config_id,requested_by,status,queued_at,started_at,finished_at,duration_sec,solver_exit_code,error_message,placements_count,unplaced_count,sheet_count,idempotency_key",
        "project_id": f"eq.{project_id}",
        "idempotency_key": f"eq.{idempotency_key}",
        "order": "created_at.desc",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.nesting_runs", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _fetch_existing_snapshot_by_hash(
    *,
    supabase: SupabaseClient,
    access_token: str,
    snapshot_hash_sha256: str,
) -> dict[str, Any] | None:
    params = {
        "select": "id,run_id,status,snapshot_hash_sha256,snapshot_version",
        "snapshot_hash_sha256": f"eq.{snapshot_hash_sha256}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.nesting_run_snapshots", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def _insert_run(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    owner_user_id: str,
    run_purpose: str,
    idempotency_key: str | None,
    snapshot_hash_sha256: str,
    run_config_id: str | None,
    run_strategy_profile_version_id: str | None,
    quality_profile: str | None,
    engine_backend_hint: str | None,
    has_nesting_engine_runtime_policy: bool,
    sa_eval_budget_sec: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_id": project_id,
        "requested_by": owner_user_id,
        "run_config_id": run_config_id,
        "status": "queued",
        "run_purpose": run_purpose,
        "request_payload_jsonb": {
            "source": "h1_e4_t2_run_creation",
            "snapshot_hash_sha256": snapshot_hash_sha256,
            "run_config_id": run_config_id,
            "run_strategy_profile_version_id": run_strategy_profile_version_id,
            "quality_profile": quality_profile,
            "engine_backend_hint": engine_backend_hint,
            "has_nesting_engine_runtime_policy": has_nesting_engine_runtime_policy,
            "sa_eval_budget_sec": sa_eval_budget_sec,
        },
        "queued_at": _now_iso(),
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    return supabase.insert_row(table="app.nesting_runs", access_token=access_token, payload=payload)


def _insert_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    owner_user_id: str,
    snapshot_payload: dict[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": "ready",
        "snapshot_version": snapshot_payload["snapshot_version"],
        "snapshot_hash_sha256": snapshot_payload["snapshot_hash_sha256"],
        "project_manifest_jsonb": snapshot_payload["project_manifest_jsonb"],
        "technology_manifest_jsonb": snapshot_payload["technology_manifest_jsonb"],
        "parts_manifest_jsonb": snapshot_payload["parts_manifest_jsonb"],
        "sheets_manifest_jsonb": snapshot_payload["sheets_manifest_jsonb"],
        "geometry_manifest_jsonb": snapshot_payload["geometry_manifest_jsonb"],
        "solver_config_jsonb": snapshot_payload["solver_config_jsonb"],
        "manufacturing_manifest_jsonb": snapshot_payload["manufacturing_manifest_jsonb"],
        "includes_manufacturing": bool(snapshot_payload.get("includes_manufacturing", False)),
        "includes_postprocess": bool(snapshot_payload.get("includes_postprocess", False)),
        "created_by": owner_user_id,
    }
    return supabase.insert_row(table="app.nesting_run_snapshots", access_token=access_token, payload=payload)


def _insert_queue(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    snapshot_id: str,
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "queue_state": "pending",
        "attempt_no": 0,
        "priority": 100,
        "retry_count": 0,
        "available_at": _now_iso(),
    }
    return supabase.insert_row(table="app.run_queue", access_token=access_token, payload=payload)


def _delete_run_best_effort(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    project_id: str,
) -> None:
    try:
        supabase.delete_rows(
            table="app.nesting_runs",
            access_token=access_token,
            filters={
                "id": f"eq.{run_id}",
                "project_id": f"eq.{project_id}",
            },
        )
    except SupabaseHTTPError:
        return


def create_queued_run_from_project_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_purpose: str | None = None,
    idempotency_key: str | None = None,
    run_config_id: str | None = None,
    run_strategy_profile_version_id: str | None = None,
    quality_profile: str | None = None,
    engine_backend_hint: str | None = None,
    nesting_engine_runtime_policy: dict[str, Any] | None = None,
    time_limit_s: int | None = None,
    sa_eval_budget_sec: int | None = None,
) -> dict[str, Any]:
    project_row = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id,
    )

    run_purpose_clean = _sanitize_run_purpose(run_purpose)
    idempotency_key_clean = _sanitize_optional(idempotency_key)
    run_config_id_clean = _sanitize_optional(run_config_id)
    run_strategy_profile_version_id_clean = _sanitize_optional(run_strategy_profile_version_id)
    quality_profile_clean = _sanitize_optional(quality_profile)
    engine_backend_hint_clean = _sanitize_optional(engine_backend_hint)

    runtime_policy_clean: dict[str, Any] | None
    if nesting_engine_runtime_policy is None:
        runtime_policy_clean = None
    else:
        if not isinstance(nesting_engine_runtime_policy, dict):
            raise RunCreationError(status_code=400, detail="invalid nesting_engine_runtime_policy")
        runtime_policy_clean = dict(nesting_engine_runtime_policy)

    if run_config_id_clean is not None:
        _load_run_config_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            project_id=project_id,
            run_config_id=run_config_id_clean,
        )

    try:
        snapshot_payload = build_run_snapshot_payload(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            project_id=project_id,
            quality_profile=quality_profile_clean,
            engine_backend_hint=engine_backend_hint_clean,
            nesting_engine_runtime_policy=runtime_policy_clean,
            time_limit_s=time_limit_s,
            sa_eval_budget_sec=sa_eval_budget_sec,
        )
    except RunSnapshotBuilderError as exc:
        raise RunCreationError(status_code=exc.status_code, detail=exc.detail) from exc

    snapshot_hash = str(snapshot_payload.get("snapshot_hash_sha256") or "").strip()
    if not snapshot_hash:
        raise RunCreationError(status_code=500, detail="snapshot builder returned empty snapshot hash")

    if idempotency_key_clean is not None:
        existing_by_key = _fetch_existing_run_by_idempotency(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
            idempotency_key=idempotency_key_clean,
        )
        if existing_by_key is not None:
            existing_run_id = str(existing_by_key.get("id") or "").strip()
            if not existing_run_id:
                raise RunCreationError(status_code=500, detail="existing idempotent run has empty id")
            existing_snapshot = _fetch_snapshot_for_run(
                supabase=supabase,
                access_token=access_token,
                run_id=existing_run_id,
            )
            if existing_snapshot is None:
                raise RunCreationError(status_code=409, detail="idempotency key already used by a run without snapshot")
            existing_hash = str(existing_snapshot.get("snapshot_hash_sha256") or "").strip()
            if existing_hash and existing_hash != snapshot_hash:
                raise RunCreationError(
                    status_code=409,
                    detail="idempotency key already used for a different snapshot",
                )
            queue_rows = supabase.select_rows(
                table="app.run_queue",
                access_token=access_token,
                params={
                    "select": "run_id,snapshot_id,queue_state,attempt_no,priority,retry_count,available_at",
                    "run_id": f"eq.{existing_run_id}",
                    "limit": "1",
                },
            )
            queue_row = queue_rows[0] if queue_rows else None
            return {
                "run": existing_by_key,
                "snapshot": existing_snapshot,
                "queue": queue_row,
                "was_deduplicated": True,
                "dedup_reason": "idempotency_key",
                "project": project_row,
            }

    existing_by_hash = _fetch_existing_snapshot_by_hash(
        supabase=supabase,
        access_token=access_token,
        snapshot_hash_sha256=snapshot_hash,
    )
    if existing_by_hash is not None:
        existing_run_id = str(existing_by_hash.get("run_id") or "").strip()
        if not existing_run_id:
            raise RunCreationError(status_code=500, detail="existing snapshot has empty run_id")
        existing_run = _fetch_run_row(
            supabase=supabase,
            access_token=access_token,
            run_id=existing_run_id,
            project_id=project_id,
        )
        queue_rows = supabase.select_rows(
            table="app.run_queue",
            access_token=access_token,
            params={
                "select": "run_id,snapshot_id,queue_state,attempt_no,priority,retry_count,available_at",
                "run_id": f"eq.{existing_run_id}",
                "limit": "1",
            },
        )
        queue_row = queue_rows[0] if queue_rows else None
        return {
            "run": existing_run,
            "snapshot": existing_by_hash,
            "queue": queue_row,
            "was_deduplicated": True,
            "dedup_reason": "snapshot_hash",
            "project": project_row,
        }

    run_row: dict[str, Any] | None = None
    try:
        run_row = _insert_run(
            supabase=supabase,
            access_token=access_token,
            project_id=project_id,
            owner_user_id=owner_user_id,
            run_purpose=run_purpose_clean,
            idempotency_key=idempotency_key_clean,
            snapshot_hash_sha256=snapshot_hash,
            run_config_id=run_config_id_clean,
            run_strategy_profile_version_id=run_strategy_profile_version_id_clean,
            quality_profile=quality_profile_clean,
            engine_backend_hint=engine_backend_hint_clean,
            has_nesting_engine_runtime_policy=runtime_policy_clean is not None,
            sa_eval_budget_sec=sa_eval_budget_sec,
        )
    except SupabaseHTTPError as exc:
        if idempotency_key_clean is not None and _is_duplicate_error(exc, constraint_hint="uq_nesting_runs_project_idempotency_key"):
            existing = _fetch_existing_run_by_idempotency(
                supabase=supabase,
                access_token=access_token,
                project_id=project_id,
                idempotency_key=idempotency_key_clean,
            )
            if existing is not None:
                existing_run_id = str(existing.get("id") or "").strip()
                existing_snapshot = _fetch_snapshot_for_run(
                    supabase=supabase,
                    access_token=access_token,
                    run_id=existing_run_id,
                )
                queue_rows = supabase.select_rows(
                    table="app.run_queue",
                    access_token=access_token,
                    params={
                        "select": "run_id,snapshot_id,queue_state,attempt_no,priority,retry_count,available_at",
                        "run_id": f"eq.{existing_run_id}",
                        "limit": "1",
                    },
                )
                queue_row = queue_rows[0] if queue_rows else None
                return {
                    "run": existing,
                    "snapshot": existing_snapshot,
                    "queue": queue_row,
                    "was_deduplicated": True,
                    "dedup_reason": "idempotency_key_race",
                    "project": project_row,
                }
        raise

    run_id = str(run_row.get("id") or "").strip()
    if not run_id:
        raise RunCreationError(status_code=500, detail="run insert returned empty id")

    try:
        snapshot_row = _insert_snapshot(
            supabase=supabase,
            access_token=access_token,
            run_id=run_id,
            owner_user_id=owner_user_id,
            snapshot_payload=snapshot_payload,
        )
    except SupabaseHTTPError as exc:
        if _is_duplicate_error(exc, constraint_hint="uq_nesting_run_snapshots_snapshot_hash_sha256"):
            _delete_run_best_effort(
                supabase=supabase,
                access_token=access_token,
                run_id=run_id,
                project_id=project_id,
            )
            existing_snapshot = _fetch_existing_snapshot_by_hash(
                supabase=supabase,
                access_token=access_token,
                snapshot_hash_sha256=snapshot_hash,
            )
            if existing_snapshot is not None:
                existing_run_id = str(existing_snapshot.get("run_id") or "").strip()
                existing_run = _fetch_run_row(
                    supabase=supabase,
                    access_token=access_token,
                    run_id=existing_run_id,
                    project_id=project_id,
                )
                queue_rows = supabase.select_rows(
                    table="app.run_queue",
                    access_token=access_token,
                    params={
                        "select": "run_id,snapshot_id,queue_state,attempt_no,priority,retry_count,available_at",
                        "run_id": f"eq.{existing_run_id}",
                        "limit": "1",
                    },
                )
                queue_row = queue_rows[0] if queue_rows else None
                return {
                    "run": existing_run,
                    "snapshot": existing_snapshot,
                    "queue": queue_row,
                    "was_deduplicated": True,
                    "dedup_reason": "snapshot_hash_race",
                    "project": project_row,
                }
        _delete_run_best_effort(
            supabase=supabase,
            access_token=access_token,
            run_id=run_id,
            project_id=project_id,
        )
        raise

    snapshot_id = str(snapshot_row.get("id") or "").strip()
    if not snapshot_id:
        _delete_run_best_effort(
            supabase=supabase,
            access_token=access_token,
            run_id=run_id,
            project_id=project_id,
        )
        raise RunCreationError(status_code=500, detail="snapshot insert returned empty id")

    try:
        queue_row = _insert_queue(
            supabase=supabase,
            access_token=access_token,
            run_id=run_id,
            snapshot_id=snapshot_id,
        )
    except SupabaseHTTPError:
        _delete_run_best_effort(
            supabase=supabase,
            access_token=access_token,
            run_id=run_id,
            project_id=project_id,
        )
        raise

    return {
        "run": run_row,
        "snapshot": snapshot_row,
        "queue": queue_row,
        "was_deduplicated": False,
        "dedup_reason": None,
        "project": project_row,
    }
