from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.services.run_batches import (
    RunBatchError,
    attach_run_batch_item,
    create_run_batch,
    delete_run_batch,
    get_run_batch,
    remove_run_batch_item,
    validate_run_batch_item_versions,
)
from api.services.run_creation import RunCreationError, create_queued_run_from_project_snapshot
from api.supabase_client import SupabaseClient, SupabaseHTTPError

_FAILURE_SEMANTICS = "fail_fast_with_best_effort_rollback"


@dataclass
class RunBatchOrchestratorError(Exception):
    status_code: int
    detail: str


def _sanitize_required(value: str, *, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise RunBatchOrchestratorError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional_text(value: str | None, *, field: str, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise RunBatchOrchestratorError(status_code=400, detail=f"invalid {field}")
    return cleaned


def _sanitize_optional_batch_id(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_candidates(raw_candidates: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    if not raw_candidates:
        raise RunBatchOrchestratorError(status_code=400, detail="candidates must not be empty")

    normalized: list[dict[str, str | None]] = []
    for index, raw in enumerate(raw_candidates):
        if not isinstance(raw, dict):
            raise RunBatchOrchestratorError(status_code=400, detail=f"invalid candidates[{index}]")

        candidate_label = _sanitize_optional_text(
            raw.get("candidate_label"),
            field=f"candidates[{index}].candidate_label",
            max_len=120,
        )
        if candidate_label is None:
            raise RunBatchOrchestratorError(
                status_code=400,
                detail=f"invalid candidates[{index}].candidate_label",
            )

        strategy_profile_version_id = _sanitize_optional_text(
            raw.get("strategy_profile_version_id"),
            field=f"candidates[{index}].strategy_profile_version_id",
            max_len=80,
        )
        if strategy_profile_version_id is None:
            raise RunBatchOrchestratorError(
                status_code=400,
                detail=f"invalid candidates[{index}].strategy_profile_version_id",
            )

        scoring_profile_version_id = _sanitize_optional_text(
            raw.get("scoring_profile_version_id"),
            field=f"candidates[{index}].scoring_profile_version_id",
            max_len=80,
        )
        if scoring_profile_version_id is None:
            raise RunBatchOrchestratorError(
                status_code=400,
                detail=f"invalid candidates[{index}].scoring_profile_version_id",
            )

        run_purpose = _sanitize_optional_text(
            raw.get("run_purpose"),
            field=f"candidates[{index}].run_purpose",
            max_len=120,
        ) or "nesting"
        idempotency_key = _sanitize_optional_text(
            raw.get("idempotency_key"),
            field=f"candidates[{index}].idempotency_key",
            max_len=160,
        )

        normalized.append(
            {
                "candidate_label": candidate_label,
                "strategy_profile_version_id": strategy_profile_version_id,
                "scoring_profile_version_id": scoring_profile_version_id,
                "run_purpose": run_purpose,
                "idempotency_key": idempotency_key,
            }
        )

    return normalized


def _rollback_best_effort(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str,
    batch_was_created: bool,
    attached_run_ids: list[str],
    created_run_ids: list[str],
) -> None:
    if batch_was_created:
        try:
            delete_run_batch(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id,
                batch_id=batch_id,
            )
        except (RunBatchError, SupabaseHTTPError):
            pass
    else:
        for run_id in attached_run_ids:
            try:
                remove_run_batch_item(
                    supabase=supabase,
                    access_token=access_token,
                    owner_user_id=owner_user_id,
                    project_id=project_id,
                    batch_id=batch_id,
                    run_id=run_id,
                )
            except (RunBatchError, SupabaseHTTPError):
                continue

    for run_id in created_run_ids:
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
            continue


def orchestrate_run_batch_candidates(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    batch_id: str | None,
    batch_kind: str,
    notes: str | None,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    project_id_clean = _sanitize_required(project_id, field="project_id")
    batch_id_clean = _sanitize_optional_batch_id(batch_id)
    batch_kind_clean = _sanitize_required(batch_kind, field="batch_kind")
    notes_clean = _sanitize_optional_text(notes, field="notes", max_len=2000)
    parsed_candidates = _parse_candidates(candidates)

    for index, candidate in enumerate(parsed_candidates):
        try:
            validate_run_batch_item_versions(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                strategy_profile_version_id=candidate["strategy_profile_version_id"],
                scoring_profile_version_id=candidate["scoring_profile_version_id"],
            )
        except RunBatchError as exc:
            raise RunBatchOrchestratorError(
                status_code=exc.status_code,
                detail=f"candidate[{index}] invalid profile scope: {exc.detail}",
            ) from exc

    batch_was_created = False
    if batch_id_clean is None:
        batch_context = create_run_batch(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            project_id=project_id_clean,
            batch_kind=batch_kind_clean,
            notes=notes_clean,
        )
        batch_was_created = True
    else:
        batch_context = get_run_batch(
            supabase=supabase,
            access_token=access_token,
            owner_user_id=owner_user_id,
            project_id=project_id_clean,
            batch_id=batch_id_clean,
        )

    batch = batch_context.get("batch")
    if not isinstance(batch, dict):
        raise RunBatchOrchestratorError(status_code=500, detail="batch orchestration returned invalid batch payload")

    batch_id_resolved = _sanitize_required(str(batch.get("id") or ""), field="batch_id")
    attached_run_ids: list[str] = []
    created_run_ids: list[str] = []
    orchestrated_items: list[dict[str, Any]] = []

    for index, candidate in enumerate(parsed_candidates):
        try:
            run_result = create_queued_run_from_project_snapshot(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                run_purpose=candidate["run_purpose"],
                idempotency_key=candidate["idempotency_key"],
            )
        except RunCreationError as exc:
            _rollback_best_effort(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                batch_was_created=batch_was_created,
                attached_run_ids=attached_run_ids,
                created_run_ids=created_run_ids,
            )
            raise RunBatchOrchestratorError(
                status_code=exc.status_code,
                detail=f"candidate[{index}] run creation failed: {exc.detail}",
            ) from exc
        except SupabaseHTTPError:
            _rollback_best_effort(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                batch_was_created=batch_was_created,
                attached_run_ids=attached_run_ids,
                created_run_ids=created_run_ids,
            )
            raise

        run = run_result.get("run")
        if not isinstance(run, dict):
            _rollback_best_effort(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                batch_was_created=batch_was_created,
                attached_run_ids=attached_run_ids,
                created_run_ids=created_run_ids,
            )
            raise RunBatchOrchestratorError(
                status_code=500,
                detail=f"candidate[{index}] run creation returned invalid payload",
            )

        run_id = _sanitize_required(str(run.get("id") or ""), field=f"candidates[{index}].run_id")
        was_deduplicated = bool(run_result.get("was_deduplicated"))
        if not was_deduplicated:
            created_run_ids.append(run_id)

        try:
            attach_result = attach_run_batch_item(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                run_id=run_id,
                candidate_label=candidate["candidate_label"],
                strategy_profile_version_id=candidate["strategy_profile_version_id"],
                scoring_profile_version_id=candidate["scoring_profile_version_id"],
            )
        except RunBatchError as exc:
            _rollback_best_effort(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                batch_was_created=batch_was_created,
                attached_run_ids=attached_run_ids,
                created_run_ids=created_run_ids,
            )
            raise RunBatchOrchestratorError(
                status_code=exc.status_code,
                detail=f"candidate[{index}] batch item attach failed: {exc.detail}",
            ) from exc
        except SupabaseHTTPError:
            _rollback_best_effort(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                batch_was_created=batch_was_created,
                attached_run_ids=attached_run_ids,
                created_run_ids=created_run_ids,
            )
            raise

        item = attach_result.get("item")
        if not isinstance(item, dict):
            _rollback_best_effort(
                supabase=supabase,
                access_token=access_token,
                owner_user_id=owner_user_id,
                project_id=project_id_clean,
                batch_id=batch_id_resolved,
                batch_was_created=batch_was_created,
                attached_run_ids=attached_run_ids,
                created_run_ids=created_run_ids,
            )
            raise RunBatchOrchestratorError(
                status_code=500,
                detail=f"candidate[{index}] attach returned invalid payload",
            )

        attached_run_ids.append(run_id)
        orchestrated_items.append(
            {
                "candidate_index": index,
                "candidate_label": candidate["candidate_label"],
                "strategy_profile_version_id": candidate["strategy_profile_version_id"],
                "scoring_profile_version_id": candidate["scoring_profile_version_id"],
                "run_purpose": candidate["run_purpose"],
                "idempotency_key": candidate["idempotency_key"],
                "run": run,
                "run_status": str(run.get("status") or "").strip() or "queued",
                "run_id": run_id,
                "was_deduplicated": was_deduplicated,
                "dedup_reason": str(run_result.get("dedup_reason") or "").strip() or None,
                "item": item,
            }
        )

    return {
        "batch": batch,
        "batch_was_created": batch_was_created,
        "failure_semantics": _FAILURE_SEMANTICS,
        "items": orchestrated_items,
        "total_candidates": len(orchestrated_items),
    }
