from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.supabase_client import SupabaseClient, SupabaseHTTPError


@dataclass
class RunBatchError(Exception):
    status_code: int
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise RunBatchError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional_text(value: str | None, *, field: str, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise RunBatchError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _normalize_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        cleaned = raw.strip().lower()
        if cleaned in {"true", "t", "1", "yes", "y"}:
            return True
        if cleaned in {"false", "f", "0", "no", "n"}:
            return False
    if isinstance(raw, (int, float)):
        return bool(raw)
    return bool(raw)


def _is_duplicate_error(exc: SupabaseHTTPError) -> bool:
    text = str(exc)
    return "duplicate key" in text or "run_batch_items_pkey" in text


def _load_project_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    owner_user_id: str,
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
        raise RunBatchError(status_code=404, detail="project not found")
    return rows[0]


def _load_batch_for_project(
    *,
    supabase: SupabaseClient,
    access_token: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,created_by,batch_kind,notes,created_at",
        "id": f"eq.{batch_id}",
        "project_id": f"eq.{project_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_batches", access_token=access_token, params=params)
    if not rows:
        raise RunBatchError(status_code=404, detail="run batch not found")
    return rows[0]


def _load_run_for_batch_project(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    project_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,project_id,status",
        "id": f"eq.{run_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.nesting_runs", access_token=access_token, params=params)
    if not rows:
        raise RunBatchError(status_code=404, detail="run not found")

    row = rows[0]
    row_project_id = str(row.get("project_id") or "").strip()
    if row_project_id != project_id:
        raise RunBatchError(status_code=403, detail="run does not belong to project")
    return row


def _load_strategy_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    version_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,run_strategy_profile_id,owner_user_id,version_no,lifecycle,is_active",
        "id": f"eq.{version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_strategy_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise RunBatchError(status_code=404, detail="run strategy profile version not found")

    row = rows[0]
    version_owner = str(row.get("owner_user_id") or "").strip()
    if version_owner != owner_user_id:
        raise RunBatchError(status_code=403, detail="run strategy profile version does not belong to owner")

    if "is_active" in row and not _normalize_bool(row.get("is_active")):
        raise RunBatchError(status_code=400, detail="run strategy profile version is inactive")

    return row


def _load_scoring_version_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    version_id: str,
) -> dict[str, Any]:
    params = {
        "select": "id,scoring_profile_id,owner_user_id,version_no,lifecycle,is_active",
        "id": f"eq.{version_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.scoring_profile_versions", access_token=access_token, params=params)
    if not rows:
        raise RunBatchError(status_code=404, detail="scoring profile version not found")

    row = rows[0]
    version_owner = str(row.get("owner_user_id") or "").strip()
    if version_owner != owner_user_id:
        raise RunBatchError(status_code=403, detail="scoring profile version does not belong to owner")

    if "is_active" in row and not _normalize_bool(row.get("is_active")):
        raise RunBatchError(status_code=400, detail="scoring profile version is inactive")

    return row


def validate_run_batch_item_versions(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    strategy_profile_version_id: str | None,
    scoring_profile_version_id: str | None,
) -> dict[str, Any]:
    strategy_profile_version_id_clean: str | None = None
    if strategy_profile_version_id is not None:
        strategy_profile_version_id_clean = _sanitize_required(
            strategy_profile_version_id,
            field="strategy_profile_version_id",
        )

    scoring_profile_version_id_clean: str | None = None
    if scoring_profile_version_id is not None:
        scoring_profile_version_id_clean = _sanitize_required(
            scoring_profile_version_id,
            field="scoring_profile_version_id",
        )

    strategy_version: dict[str, Any] | None = None
    if strategy_profile_version_id_clean is not None:
        strategy_version = _load_strategy_version_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            version_id=strategy_profile_version_id_clean,
        )

    scoring_version: dict[str, Any] | None = None
    if scoring_profile_version_id_clean is not None:
        scoring_version = _load_scoring_version_for_owner(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            version_id=scoring_profile_version_id_clean,
        )

    return {
        "strategy_profile_version_id": strategy_profile_version_id_clean,
        "scoring_profile_version_id": scoring_profile_version_id_clean,
        "strategy_profile_version": strategy_version,
        "scoring_profile_version": scoring_version,
    }


def _load_batch_item(
    *,
    supabase: SupabaseClient,
    access_token: str,
    batch_id: str,
    run_id: str,
) -> dict[str, Any] | None:
    params = {
        "select": "batch_id,run_id,candidate_label,strategy_profile_version_id,scoring_profile_version_id,created_at",
        "batch_id": f"eq.{batch_id}",
        "run_id": f"eq.{run_id}",
        "limit": "1",
    }
    rows = supabase.select_rows(table="app.run_batch_items", access_token=access_token, params=params)
    if not rows:
        return None
    return rows[0]


def create_run_batch(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_kind: str,
    notes: str | None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_kind_clean = _sanitize_required(batch_kind, field="batch_kind")
    notes_clean = _sanitize_optional_text(notes, field="notes", max_len=2000)

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )

    payload = {
        "project_id": project_id_clean,
        "created_by": owner_user_id,
        "batch_kind": batch_kind_clean,
        "notes": notes_clean,
        "created_at": _now_iso(),
    }
    batch = supabase.insert_row(table="app.run_batches", access_token=access_token, payload=payload)
    return {
        "project": project,
        "batch": batch,
    }


def list_run_batches(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )

    params = {
        "select": "id,project_id,created_by,batch_kind,notes,created_at",
        "project_id": f"eq.{project_id_clean}",
        "order": "created_at.desc,id.desc",
    }
    rows = supabase.select_rows(table="app.run_batches", access_token=access_token, params=params)

    return {
        "project": project,
        "items": rows,
        "total": len(rows),
    }


def get_run_batch(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )

    return {
        "project": project,
        "batch": batch,
    }


def delete_run_batch(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )

    supabase.delete_rows(
        table="app.run_batches",
        access_token=access_token,
        filters={
            "id": f"eq.{batch_id_clean}",
            "project_id": f"eq.{project_id_clean}",
        },
    )

    return {
        "project": project,
        "batch": batch,
    }


def attach_run_batch_item(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
    run_id: str,
    candidate_label: str | None,
    strategy_profile_version_id: str | None,
    scoring_profile_version_id: str | None,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")
    run_id_clean = _sanitize_required(run_id, field="run_id")
    candidate_label_clean = _sanitize_optional_text(candidate_label, field="candidate_label", max_len=120)

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )
    run = _load_run_for_batch_project(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id_clean,
        project_id=project_id_clean,
    )

    version_context = validate_run_batch_item_versions(
        supabase=supabase,
        access_token=access_token,
        owner_user_id=owner_user_id,
        strategy_profile_version_id=strategy_profile_version_id,
        scoring_profile_version_id=scoring_profile_version_id,
    )
    strategy_profile_version_id_clean = version_context["strategy_profile_version_id"]
    scoring_profile_version_id_clean = version_context["scoring_profile_version_id"]
    strategy_version = version_context["strategy_profile_version"]
    scoring_version = version_context["scoring_profile_version"]

    existing = _load_batch_item(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
        run_id=run_id_clean,
    )
    if existing is not None:
        raise RunBatchError(status_code=409, detail="run already attached to batch")

    payload = {
        "batch_id": batch_id_clean,
        "run_id": run_id_clean,
        "candidate_label": candidate_label_clean,
        "strategy_profile_version_id": strategy_profile_version_id_clean,
        "scoring_profile_version_id": scoring_profile_version_id_clean,
        "created_at": _now_iso(),
    }

    try:
        item = supabase.insert_row(table="app.run_batch_items", access_token=access_token, payload=payload)
    except SupabaseHTTPError as exc:
        if _is_duplicate_error(exc):
            raise RunBatchError(status_code=409, detail="run already attached to batch") from exc
        raise

    return {
        "project": project,
        "batch": batch,
        "run": run,
        "item": item,
        "strategy_profile_version": strategy_version,
        "scoring_profile_version": scoring_version,
    }


def list_run_batch_items(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )

    params = {
        "select": "batch_id,run_id,candidate_label,strategy_profile_version_id,scoring_profile_version_id,created_at",
        "batch_id": f"eq.{batch_id_clean}",
        "order": "created_at.asc,run_id.asc",
    }
    rows = supabase.select_rows(table="app.run_batch_items", access_token=access_token, params=params)

    return {
        "project": project,
        "batch": batch,
        "items": rows,
        "total": len(rows),
    }


def remove_run_batch_item(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
    run_id: str,
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_required(batch_id, field="batch_id")
    run_id_clean = _sanitize_required(run_id, field="run_id")

    project = _load_project_for_owner(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        owner_user_id=owner_user_id,
    )
    batch = _load_batch_for_project(
        supabase=supabase,
        access_token=access_token,
        project_id=project_id_clean,
        batch_id=batch_id_clean,
    )

    existing_item = _load_batch_item(
        supabase=supabase,
        access_token=access_token,
        batch_id=batch_id_clean,
        run_id=run_id_clean,
    )
    if existing_item is None:
        raise RunBatchError(status_code=404, detail="run batch item not found")

    supabase.delete_rows(
        table="app.run_batch_items",
        access_token=access_token,
        filters={
            "batch_id": f"eq.{batch_id_clean}",
            "run_id": f"eq.{run_id_clean}",
        },
    )

    return {
        "project": project,
        "batch": batch,
        "item": existing_item,
    }
