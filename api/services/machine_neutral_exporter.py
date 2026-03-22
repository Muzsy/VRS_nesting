"""H2-E5-T3 — Machine-neutral exporter service.

Generates a deterministic, canonical, machine-neutral JSON export artifact
from the persisted H2 manufacturing truth:
* run_manufacturing_plans + run_manufacturing_contours (H2-E4-T2)
* nesting_run_snapshots.manufacturing_manifest_jsonb (snapshot selection)
* optionally run_manufacturing_metrics (H2-E4-T3)
* optionally geometry_derivatives (manufacturing_canonical) for contour points

**Non-negotiable scope boundaries**
* Reads ONLY persisted manufacturing plan truth + snapshot.
* Never reads raw solver output, live project_manufacturing_selection,
  preview SVG artifacts, or worker run directories.
* Writes ONLY to run_artifacts (manufacturing_plan_json kind).
* Never writes to run_manufacturing_plans, run_manufacturing_contours,
  run_manufacturing_metrics, geometry_contour_classes,
  project_manufacturing_selection, or postprocessor_profile_versions.
* No machine-specific adapter, machine_ready_bundle, G-code/NC output,
  worker auto-hook, or export UI.
* Idempotent: delete-then-insert per run (no duplicate export artifacts).
* Deterministic: no volatile timestamps or non-deterministic fields in payload.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from api.supabase_client import SupabaseClient

UploadFn = Callable[..., None]
RegisterFn = Callable[..., None]

logger = logging.getLogger("vrs_api.machine_neutral_exporter")

EXPORT_CONTRACT_VERSION = "h2_e5_t3_v1"
_STORAGE_BUCKET = "run-artifacts"
_ARTIFACT_KIND = "manufacturing_plan_json"


@dataclass
class MachineNeutralExporterError(Exception):
    status_code: int
    detail: str


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_machine_neutral_export(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    run_id: str,
    upload_object: UploadFn,
    register_artifact: RegisterFn,
) -> dict[str, Any]:
    """Generate a machine-neutral export artifact for a run.

    Returns a summary dict with the created artifact details.
    """
    run_id = _require(run_id, "run_id")
    owner_user_id = _require(owner_user_id, "owner_user_id")

    # 1) Verify run ownership and get project_id
    run = _load_run_for_owner(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
        owner_user_id=owner_user_id,
    )
    project_id = str(run.get("project_id") or "").strip()
    if not project_id:
        raise MachineNeutralExporterError(
            status_code=400, detail="run missing project_id",
        )

    # 2) Load persisted manufacturing plans
    plans = _load_manufacturing_plans(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    if not plans:
        raise MachineNeutralExporterError(
            status_code=400,
            detail="run has no persisted manufacturing plans",
        )

    # 3) Load manufacturing contours for all plans
    plan_ids = [str(p.get("id") or "").strip() for p in plans if p.get("id")]
    contours = _load_manufacturing_contours(
        supabase=supabase,
        access_token=access_token,
        plan_ids=plan_ids,
    )

    # 4) Load snapshot for manufacturing manifest
    snapshot = _load_snapshot(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )
    mfg_manifest = snapshot.get("manufacturing_manifest_jsonb")
    if not isinstance(mfg_manifest, dict):
        mfg_manifest = {}

    # 5) Optionally load manufacturing metrics
    metrics = _load_manufacturing_metrics(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )

    # 6) Load sheets for sheet-level data
    sheets = _load_sheets(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )

    # 7) Build the canonical export payload
    payload = _build_export_payload(
        run_id=run_id,
        project_id=project_id,
        plans=plans,
        contours=contours,
        sheets=sheets,
        mfg_manifest=mfg_manifest,
        metrics=metrics,
    )

    # 8) Serialize deterministically
    payload_bytes = _canonical_json_bytes(payload)
    content_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    size_bytes = len(payload_bytes)

    # 9) Deterministic filename and storage path
    filename = "out/manufacturing_plan.json"
    storage_path = (
        f"projects/{project_id}/runs/{run_id}/"
        f"manufacturing_plan_json/{content_sha256}.json"
    )

    metadata = {
        "legacy_artifact_type": _ARTIFACT_KIND,
        "filename": filename,
        "size_bytes": size_bytes,
        "content_sha256": content_sha256,
        "export_scope": "h2_e5_t3",
        "export_contract_version": EXPORT_CONTRACT_VERSION,
    }

    # 10) Idempotent: delete existing manufacturing_plan_json artifacts
    _delete_existing_export_artifacts(
        supabase=supabase,
        access_token=access_token,
        run_id=run_id,
    )

    # 11) Upload to storage
    upload_object(
        bucket=_STORAGE_BUCKET,
        object_key=storage_path,
        payload=payload_bytes,
    )

    # 12) Register artifact
    register_artifact(
        run_id=run_id,
        artifact_kind=_ARTIFACT_KIND,
        storage_bucket=_STORAGE_BUCKET,
        storage_path=storage_path,
        metadata_json=metadata,
    )

    return {
        "run_id": run_id,
        "project_id": project_id,
        "filename": filename,
        "storage_path": storage_path,
        "content_sha256": content_sha256,
        "size_bytes": size_bytes,
        "export_contract_version": EXPORT_CONTRACT_VERSION,
    }


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------


def _build_export_payload(
    *,
    run_id: str,
    project_id: str,
    plans: list[dict[str, Any]],
    contours: list[dict[str, Any]],
    sheets: list[dict[str, Any]],
    mfg_manifest: dict[str, Any],
    metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the canonical, deterministic export payload."""

    # Extract manufacturing profile version from manifest
    manufacturing_profile_version_id = str(
        mfg_manifest.get("active_manufacturing_profile_version_id") or "",
    ).strip() or None

    # Postprocessor selection metadata (from snapshot, NOT live)
    postprocessor_metadata = _extract_postprocessor_metadata(mfg_manifest)

    # Group contours by plan_id
    contours_by_plan: dict[str, list[dict[str, Any]]] = {}
    for c in contours:
        plan_id = str(c.get("manufacturing_plan_id") or "").strip()
        contours_by_plan.setdefault(plan_id, []).append(c)

    # Build sheet index lookup
    sheet_by_id: dict[str, dict[str, Any]] = {}
    for s in sheets:
        sid = str(s.get("id") or "").strip()
        if sid:
            sheet_by_id[sid] = s

    # Build per-sheet export blocks (deterministic order)
    sheet_exports: list[dict[str, Any]] = []
    for plan in plans:
        plan_id = str(plan.get("id") or "").strip()
        sheet_id = str(plan.get("sheet_id") or "").strip()
        sheet = sheet_by_id.get(sheet_id, {})
        sheet_index = int(sheet.get("sheet_index") if sheet.get("sheet_index") is not None else 0)

        plan_contours = contours_by_plan.get(plan_id, [])
        # Deterministic contour ordering by cut_order_index, then contour_index
        plan_contours.sort(
            key=lambda c: (
                int(c.get("cut_order_index") if c.get("cut_order_index") is not None else 0),
                int(c.get("contour_index") if c.get("contour_index") is not None else 0),
            ),
        )

        contour_exports: list[dict[str, Any]] = []
        for c in plan_contours:
            contour_export: dict[str, Any] = {
                "contour_index": c.get("contour_index"),
                "contour_kind": str(c.get("contour_kind") or ""),
                "feature_class": str(c.get("feature_class") or "default"),
                "cut_order_index": c.get("cut_order_index"),
                "entry_point_jsonb": c.get("entry_point_jsonb"),
                "lead_in_jsonb": c.get("lead_in_jsonb"),
                "lead_out_jsonb": c.get("lead_out_jsonb"),
            }
            contour_exports.append(contour_export)

        plan_summary = plan.get("summary_jsonb")
        if not isinstance(plan_summary, dict):
            plan_summary = {}

        sheet_export: dict[str, Any] = {
            "sheet_index": sheet_index,
            "sheet_id": sheet_id,
            "plan_id": plan_id,
            "manufacturing_profile_version_id": str(
                plan.get("manufacturing_profile_version_id") or "",
            ).strip() or None,
            "cut_rule_set_id": str(
                plan.get("cut_rule_set_id") or "",
            ).strip() or None,
            "plan_status": str(plan.get("status") or ""),
            "plan_summary": plan_summary,
            "contours": contour_exports,
        }
        sheet_exports.append(sheet_export)

    # Deterministic sheet ordering
    sheet_exports.sort(key=lambda s: int(s.get("sheet_index") or 0))

    # Build top-level payload
    payload: dict[str, Any] = {
        "export_contract_version": EXPORT_CONTRACT_VERSION,
        "run_id": run_id,
        "project_id": project_id,
        "manufacturing_profile_version_id": manufacturing_profile_version_id,
        "sheets": sheet_exports,
    }

    # Optional: manufacturing metrics
    if metrics is not None:
        payload["manufacturing_metrics"] = {
            "pierce_count": metrics.get("pierce_count"),
            "outer_contour_count": metrics.get("outer_contour_count"),
            "inner_contour_count": metrics.get("inner_contour_count"),
            "estimated_cut_length_mm": metrics.get("estimated_cut_length_mm"),
            "estimated_rapid_length_mm": metrics.get("estimated_rapid_length_mm"),
            "estimated_process_time_s": metrics.get("estimated_process_time_s"),
            "metrics_jsonb": metrics.get("metrics_jsonb"),
        }

    # Postprocessor metadata (from snapshot, metadata only)
    if postprocessor_metadata is not None:
        payload["postprocessor_selection"] = postprocessor_metadata

    return payload


def _extract_postprocessor_metadata(
    mfg_manifest: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract postprocessor selection metadata from snapshot manifest.

    This is metadata-only: no machine-specific emit, no config application.
    """
    if not mfg_manifest.get("postprocess_selection_present"):
        return None

    pp_version = mfg_manifest.get("postprocessor_profile_version")
    if not isinstance(pp_version, dict):
        return None

    active_pp_version_id = str(
        pp_version.get("active_postprocessor_profile_version_id") or "",
    ).strip()
    if not active_pp_version_id:
        return None

    return {
        "active_postprocessor_profile_version_id": active_pp_version_id,
        "adapter_key": str(pp_version.get("adapter_key") or "").strip() or None,
        "output_format": str(pp_version.get("output_format") or "").strip() or None,
        "schema_version": str(pp_version.get("schema_version") or "").strip() or None,
    }


# ---------------------------------------------------------------------------
# Canonical JSON serialization
# ---------------------------------------------------------------------------


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize payload to deterministic, canonical JSON bytes.

    Uses sorted keys and compact separators for byte-level reproducibility.
    """
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _require(value: str | None, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise MachineNeutralExporterError(status_code=400, detail=f"missing {field}")
    return cleaned


def _load_run_for_owner(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_runs",
        access_token=access_token,
        params={
            "select": "id,owner_user_id,project_id,status",
            "id": f"eq.{run_id}",
            "owner_user_id": f"eq.{owner_user_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineNeutralExporterError(
            status_code=404, detail="run not found or not owned by user",
        )
    return rows[0]


def _load_snapshot(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any]:
    rows = supabase.select_rows(
        table="app.nesting_run_snapshots",
        access_token=access_token,
        params={
            "select": "id,run_id,manufacturing_manifest_jsonb,includes_manufacturing",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise MachineNeutralExporterError(
            status_code=404, detail="snapshot not found for run",
        )
    return rows[0]


def _load_manufacturing_plans(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_manufacturing_plans",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_id,manufacturing_profile_version_id,"
                      "cut_rule_set_id,status,summary_jsonb",
            "run_id": f"eq.{run_id}",
            "order": "sheet_id.asc",
        },
    )


def _load_manufacturing_contours(
    *,
    supabase: SupabaseClient,
    access_token: str,
    plan_ids: list[str],
) -> list[dict[str, Any]]:
    all_contours: list[dict[str, Any]] = []
    for plan_id in plan_ids:
        rows = supabase.select_rows(
            table="app.run_manufacturing_contours",
            access_token=access_token,
            params={
                "select": "id,manufacturing_plan_id,contour_index,contour_kind,"
                          "feature_class,entry_point_jsonb,lead_in_jsonb,"
                          "lead_out_jsonb,cut_order_index",
                "manufacturing_plan_id": f"eq.{plan_id}",
                "order": "cut_order_index.asc",
            },
        )
        all_contours.extend(rows)
    return all_contours


def _load_sheets(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> list[dict[str, Any]]:
    return supabase.select_rows(
        table="app.run_layout_sheets",
        access_token=access_token,
        params={
            "select": "id,run_id,sheet_index",
            "run_id": f"eq.{run_id}",
            "order": "sheet_index.asc",
        },
    )


def _load_manufacturing_metrics(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> dict[str, Any] | None:
    rows = supabase.select_rows(
        table="app.run_manufacturing_metrics",
        access_token=access_token,
        params={
            "select": "run_id,pierce_count,outer_contour_count,inner_contour_count,"
                      "estimated_cut_length_mm,estimated_rapid_length_mm,"
                      "estimated_process_time_s,metrics_jsonb",
            "run_id": f"eq.{run_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def _delete_existing_export_artifacts(
    *,
    supabase: SupabaseClient,
    access_token: str,
    run_id: str,
) -> None:
    """Idempotent: delete existing manufacturing_plan_json artifacts."""
    supabase.delete_rows(
        table="app.run_artifacts",
        access_token=access_token,
        filters={
            "run_id": f"eq.{run_id}",
            "artifact_kind": f"eq.{_ARTIFACT_KIND}",
        },
    )
