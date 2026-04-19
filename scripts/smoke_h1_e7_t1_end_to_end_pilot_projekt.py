#!/usr/bin/env python3
"""H1-E7-T1 smoke: end-to-end pilot project chain on in-memory fake gateway."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.dxf_geometry_import import import_source_dxf_geometry_revision  # noqa: E402
from api.services.file_ingest_metadata import load_file_ingest_metadata  # noqa: E402
from api.services.part_creation import create_part_from_geometry_revision  # noqa: E402
from api.services.project_part_requirements import create_or_update_project_part_requirement  # noqa: E402
from api.services.project_sheet_inputs import create_or_update_project_sheet_input  # noqa: E402
from api.services.run_creation import create_queued_run_from_project_snapshot  # noqa: E402
from api.services.sheet_creation import create_sheet_revision  # noqa: E402
from api.supabase_client import SupabaseHTTPError  # noqa: E402
from worker.engine_adapter_input import build_solver_input_from_snapshot  # noqa: E402
from worker.raw_output_artifacts import persist_raw_output_artifacts  # noqa: E402
from worker.result_normalizer import normalize_solver_output_projection  # noqa: E402
from worker.sheet_dxf_artifacts import persist_sheet_dxf_artifacts  # noqa: E402
from worker.sheet_svg_artifacts import persist_sheet_svg_artifacts  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.projects": [],
            "app.project_settings": [],
            "app.project_technology_setups": [],
            "app.file_objects": [],
            "app.geometry_revisions": [],
            "app.geometry_validation_reports": [],
            "app.geometry_derivatives": [],
            "app.part_definitions": [],
            "app.part_revisions": [],
            "app.sheet_definitions": [],
            "app.sheet_revisions": [],
            "app.project_part_requirements": [],
            "app.project_sheet_inputs": [],
            "app.nesting_runs": [],
            "app.nesting_run_snapshots": [],
            "app.run_queue": [],
            "app.run_layout_sheets": [],
            "app.run_layout_placements": [],
            "app.run_layout_unplaced": [],
            "app.run_metrics": [],
            "app.run_artifacts": [],
        }
        self.storage: dict[tuple[str, str], bytes] = {}

    @staticmethod
    def _as_text(value: Any) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _parse_bool_token(token: str) -> bool | None:
        lowered = token.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        return None

    def _match_filter(self, value: Any, raw_filter: str) -> bool:
        token = raw_filter.strip()
        text = self._as_text(value)

        if token.startswith("eq."):
            probe = token[3:]
            probe_bool = self._parse_bool_token(probe)
            if probe_bool is not None:
                return bool(value) is probe_bool
            return text == probe

        if token.startswith("neq."):
            probe = token[4:]
            probe_bool = self._parse_bool_token(probe)
            if probe_bool is not None:
                return bool(value) is not probe_bool
            return text != probe

        if token.startswith("gt."):
            try:
                return float(value) > float(token[3:])
            except (TypeError, ValueError):
                return False

        if token.startswith("gte."):
            try:
                return float(value) >= float(token[4:])
            except (TypeError, ValueError):
                return False

        if token.startswith("lt."):
            try:
                return float(value) < float(token[3:])
            except (TypeError, ValueError):
                return False

        if token.startswith("lte."):
            try:
                return float(value) <= float(token[4:])
            except (TypeError, ValueError):
                return False

        return True

    def _apply_order(self, rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
        ordered = list(rows)
        tokens = [part.strip() for part in order_clause.split(",") if part.strip()]
        for token in reversed(tokens):
            key = token.split(".")[0]
            reverse = ".desc" in token
            ordered.sort(key=lambda row: self._as_text(row.get(key)), reverse=reverse)
        return ordered

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        _ = access_token
        rows = [_copy_json(row) for row in self.tables.get(table, [])]

        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._match_filter(row.get(key), raw_filter)]

        order_clause = str(params.get("order") or "").strip()
        if order_clause:
            rows = self._apply_order(rows, order_clause)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = str(params.get("limit") or "").strip()
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]

        return [_copy_json(row) for row in rows]

    def _enforce_unique_constraints(self, *, table: str, row: dict[str, Any]) -> None:
        existing = self.tables.get(table, [])

        if table == "app.geometry_derivatives":
            key = (
                self._as_text(row.get("geometry_revision_id")),
                self._as_text(row.get("derivative_kind")),
            )
            for item in existing:
                item_key = (
                    self._as_text(item.get("geometry_revision_id")),
                    self._as_text(item.get("derivative_kind")),
                )
                if item_key == key:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint geometry_derivatives_geometry_revision_kind")

        if table == "app.project_part_requirements":
            key = (self._as_text(row.get("project_id")), self._as_text(row.get("part_revision_id")))
            for item in existing:
                item_key = (self._as_text(item.get("project_id")), self._as_text(item.get("part_revision_id")))
                if item_key == key:
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint project_part_requirements_project_id_part_revision_id_key"
                    )

        if table == "app.project_sheet_inputs":
            key = (self._as_text(row.get("project_id")), self._as_text(row.get("sheet_revision_id")))
            for item in existing:
                item_key = (self._as_text(item.get("project_id")), self._as_text(item.get("sheet_revision_id")))
                if item_key == key:
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint project_sheet_inputs_project_id_sheet_revision_id_key"
                    )

        if table == "app.nesting_runs":
            project_id = self._as_text(row.get("project_id"))
            idem = row.get("idempotency_key")
            if idem is not None:
                idem_text = self._as_text(idem)
                for item in existing:
                    if self._as_text(item.get("project_id")) == project_id and self._as_text(item.get("idempotency_key")) == idem_text:
                        raise SupabaseHTTPError(
                            "duplicate key value violates unique constraint uq_nesting_runs_project_idempotency_key"
                        )

        if table == "app.nesting_run_snapshots":
            run_id = self._as_text(row.get("run_id"))
            snapshot_hash = self._as_text(row.get("snapshot_hash_sha256"))
            for item in existing:
                if self._as_text(item.get("run_id")) == run_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint nesting_run_snapshots_run_id")
                if snapshot_hash and self._as_text(item.get("snapshot_hash_sha256")) == snapshot_hash:
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint uq_nesting_run_snapshots_snapshot_hash_sha256"
                    )

        if table == "app.run_queue":
            run_id = self._as_text(row.get("run_id"))
            for item in existing:
                if self._as_text(item.get("run_id")) == run_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint run_queue_pkey")

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = _copy_json(payload)
        self._enforce_unique_constraints(table=table, row=row)

        now = _now_iso()
        row.setdefault("id", str(uuid4()))
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)

        if table not in self.tables:
            self.tables[table] = []
        self.tables[table].append(row)
        return _copy_json(row)

    def update_rows(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = self.tables.get(table, [])
        if not rows:
            return []

        matched: list[dict[str, Any]] = []
        for row in rows:
            keep = True
            for key, raw_filter in filters.items():
                if not self._match_filter(row.get(key), raw_filter):
                    keep = False
                    break
            if not keep:
                continue
            row.update(_copy_json(payload))
            row["updated_at"] = _now_iso()
            matched.append(_copy_json(row))
        return matched

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        rows = self.tables.get(table, [])
        if not rows:
            return

        kept: list[dict[str, Any]] = []
        for row in rows:
            remove = True
            for key, raw_filter in filters.items():
                if not self._match_filter(row.get(key), raw_filter):
                    remove = False
                    break
            if remove:
                continue
            kept.append(row)
        self.tables[table] = kept

    def execute_rpc(self, *, function_name: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token

        if function_name == "create_part_revision_atomic":
            part_definition_id = self._as_text(payload.get("p_part_definition_id"))
            source_geometry_revision_id = self._as_text(payload.get("p_source_geometry_revision_id"))
            selected_derivative_id = self._as_text(payload.get("p_selected_nesting_derivative_id"))

            definitions = self.tables["app.part_definitions"]
            definition = next((row for row in definitions if self._as_text(row.get("id")) == part_definition_id), None)
            if definition is None:
                raise SupabaseHTTPError("part_definition not found")

            revisions = [
                row
                for row in self.tables["app.part_revisions"]
                if self._as_text(row.get("part_definition_id")) == part_definition_id
            ]
            next_revision_no = max([int(row.get("revision_no") or 0) for row in revisions] + [0]) + 1

            revision = {
                "id": str(uuid4()),
                "part_definition_id": part_definition_id,
                "revision_no": next_revision_no,
                "lifecycle": "approved",
                "source_geometry_revision_id": source_geometry_revision_id,
                "selected_nesting_derivative_id": selected_derivative_id,
                "source_label": payload.get("p_source_label"),
                "source_checksum_sha256": payload.get("p_source_checksum_sha256"),
                "notes": payload.get("p_notes"),
                "created_at": _now_iso(),
            }
            self.tables["app.part_revisions"].append(revision)
            definition["current_revision_id"] = revision["id"]
            definition["updated_at"] = _now_iso()
            return {
                "part_definition": _copy_json(definition),
                "part_revision": _copy_json(revision),
            }

        if function_name == "create_sheet_revision_atomic":
            sheet_definition_id = self._as_text(payload.get("p_sheet_definition_id"))
            width_mm = float(payload.get("p_width_mm"))
            height_mm = float(payload.get("p_height_mm"))

            definitions = self.tables["app.sheet_definitions"]
            definition = next((row for row in definitions if self._as_text(row.get("id")) == sheet_definition_id), None)
            if definition is None:
                raise SupabaseHTTPError("sheet_definition not found")

            revisions = [
                row
                for row in self.tables["app.sheet_revisions"]
                if self._as_text(row.get("sheet_definition_id")) == sheet_definition_id
            ]
            next_revision_no = max([int(row.get("revision_no") or 0) for row in revisions] + [0]) + 1

            revision = {
                "id": str(uuid4()),
                "sheet_definition_id": sheet_definition_id,
                "revision_no": next_revision_no,
                "lifecycle": "approved",
                "width_mm": width_mm,
                "height_mm": height_mm,
                "grain_direction": payload.get("p_grain_direction"),
                "source_label": payload.get("p_source_label"),
                "notes": payload.get("p_notes"),
                "created_at": _now_iso(),
            }
            self.tables["app.sheet_revisions"].append(revision)
            definition["current_revision_id"] = revision["id"]
            definition["updated_at"] = _now_iso()
            return {
                "sheet_definition": _copy_json(definition),
                "sheet_revision": _copy_json(revision),
            }

        raise SupabaseHTTPError(f"unsupported rpc function: {function_name}")

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int,
    ) -> dict[str, Any]:
        _ = (access_token, expires_in)
        return {
            "download_url": f"https://download.local/{bucket}/{object_key}",
            "expires_at": _now_iso(),
        }

    def download_signed_object(self, *, signed_url: str) -> bytes:
        parsed = urlparse(signed_url)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise SupabaseHTTPError("invalid signed download path")
        bucket = parts[0]
        object_key = "/".join(parts[1:])
        blob = self.storage.get((bucket, object_key))
        if blob is None:
            raise SupabaseHTTPError("object not found")
        return bytes(blob)

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        self.storage[(bucket, object_key)] = bytes(payload)

    def register_artifact(
        self,
        *,
        run_id: str,
        artifact_kind: str,
        storage_bucket: str,
        storage_path: str,
        metadata_json: dict[str, Any],
    ) -> None:
        self.insert_row(
            table="app.run_artifacts",
            access_token="internal",
            payload={
                "run_id": run_id,
                "artifact_kind": artifact_kind,
                "storage_bucket": storage_bucket,
                "storage_path": storage_path,
                "metadata_jsonb": _copy_json(metadata_json),
            },
        )

    def replace_projection(
        self,
        *,
        run_id: str,
        sheets: list[dict[str, Any]],
        placements: list[dict[str, Any]],
        unplaced: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> None:
        self.delete_rows(table="app.run_layout_sheets", access_token="internal", filters={"run_id": f"eq.{run_id}"})
        self.delete_rows(table="app.run_layout_placements", access_token="internal", filters={"run_id": f"eq.{run_id}"})
        self.delete_rows(table="app.run_layout_unplaced", access_token="internal", filters={"run_id": f"eq.{run_id}"})
        self.delete_rows(table="app.run_metrics", access_token="internal", filters={"run_id": f"eq.{run_id}"})

        sheet_id_by_index: dict[int, str] = {}
        for row in sheets:
            sheet_index = int(row["sheet_index"])
            sheet_id = str(uuid4())
            sheet_id_by_index[sheet_index] = sheet_id
            self.insert_row(
                table="app.run_layout_sheets",
                access_token="internal",
                payload={
                    "id": sheet_id,
                    "run_id": run_id,
                    **_copy_json(row),
                },
            )

        for row in placements:
            sheet_index = int(row["sheet_index"])
            sheet_id = sheet_id_by_index.get(sheet_index)
            if sheet_id is None:
                raise RuntimeError(f"missing sheet mapping for placement sheet_index={sheet_index}")
            payload = _copy_json(row)
            payload["sheet_id"] = sheet_id
            self.insert_row(
                table="app.run_layout_placements",
                access_token="internal",
                payload={
                    "run_id": run_id,
                    **payload,
                },
            )

        for row in unplaced:
            self.insert_row(
                table="app.run_layout_unplaced",
                access_token="internal",
                payload={
                    "run_id": run_id,
                    **_copy_json(row),
                },
            )

        self.insert_row(
            table="app.run_metrics",
            access_token="internal",
            payload={
                "run_id": run_id,
                **_copy_json(metrics),
            },
        )


def _seed_project(fake: FakeSupabaseClient, *, owner_user_id: str) -> str:
    project = fake.insert_row(
        table="app.projects",
        access_token="seed",
        payload={
            "id": str(uuid4()),
            "owner_user_id": owner_user_id,
            "name": "H1 Pilot Project",
            "lifecycle": "active",
        },
    )
    project_id = str(project["id"])

    fake.insert_row(
        table="app.project_settings",
        access_token="seed",
        payload={
            "project_id": project_id,
            "default_units": "mm",
            "default_rotation_step_deg": 90,
            "notes": "pilot settings",
        },
    )

    fake.insert_row(
        table="app.project_technology_setups",
        access_token="seed",
        payload={
            "project_id": project_id,
            "preset_id": None,
            "display_name": "Pilot Tech",
            "lifecycle": "approved",
            "is_default": True,
            "machine_code": "M-PILOT",
            "material_code": "STEEL-S235",
            "thickness_mm": 2.0,
            "kerf_mm": 0.2,
            "spacing_mm": 1.0,
            "margin_mm": 0.0,
            "rotation_step_deg": 90,
            "allow_free_rotation": False,
            "notes": "h1_e7_t1",
        },
    )

    return project_id


def _ingest_file_and_import_geometry(
    fake: FakeSupabaseClient,
    *,
    owner_user_id: str,
    project_id: str,
    access_token: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    storage_bucket = "source-files"
    storage_path = f"projects/{project_id}/files/{uuid4()}/pilot_part.dxf"
    fixture_path = ROOT / "samples" / "dxf_demo" / "stock_rect_1000x2000.dxf"
    blob = fixture_path.read_bytes()
    fake.storage[(storage_bucket, storage_path)] = blob

    metadata = load_file_ingest_metadata(
        supabase=fake,
        access_token=access_token,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        signed_url_ttl_s=300,
    )

    file_row = fake.insert_row(
        table="app.file_objects",
        access_token=access_token,
        payload={
            "project_id": project_id,
            "storage_bucket": storage_bucket,
            "storage_path": storage_path,
            "file_name": metadata.file_name,
            "mime_type": metadata.mime_type,
            "file_kind": "source_dxf",
            "byte_size": metadata.byte_size,
            "sha256": metadata.sha256,
            "uploaded_by": owner_user_id,
        },
    )

    geometry_revision = import_source_dxf_geometry_revision(
        supabase=fake,
        access_token=access_token,
        project_id=project_id,
        source_file_object_id=str(file_row["id"]),
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        source_hash_sha256=metadata.sha256,
        created_by=owner_user_id,
        signed_url_ttl_s=300,
    )

    return file_row, geometry_revision


def _worker_like_projection_and_artifacts(
    fake: FakeSupabaseClient,
    *,
    run_id: str,
    project_id: str,
    snapshot_row: dict[str, Any],
) -> dict[str, Any]:
    solver_input = build_solver_input_from_snapshot(snapshot_row)
    _assert(bool(solver_input.get("parts")), "solver_input.parts is empty")
    _assert(bool(solver_input.get("stocks")), "solver_input.stocks is empty")

    part_id = str(solver_input["parts"][0]["id"])
    solver_output = {
        "contract_version": "v1",
        "status": "optimal",
        "placements": [
            {
                "instance_id": "pilot-inst-001",
                "part_id": part_id,
                "sheet_index": 0,
                "x": 0.0,
                "y": 0.0,
                "rotation_deg": 0.0,
            }
        ],
        "unplaced": [],
        "metrics": {
            "runtime_s": 0.01,
            "solver": "synthetic_for_h1_pilot",
        },
    }

    with TemporaryDirectory(prefix="vrs_h1_e7_t1_pilot_") as tmp:
        run_dir = Path(tmp)
        (run_dir / "solver_output.json").write_text(
            json.dumps(solver_output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "solver_stdout.log").write_text("pilot stdout\n", encoding="utf-8")
        (run_dir / "solver_stderr.log").write_text("", encoding="utf-8")
        (run_dir / "runner_meta.json").write_text(
            json.dumps({"run_id": run_id, "mode": "pilot"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "run.log").write_text("pilot run log\n", encoding="utf-8")

        raw_records = persist_raw_output_artifacts(
            run_dir=run_dir,
            project_id=project_id,
            run_id=run_id,
            storage_bucket="run-artifacts",
            upload_object=fake.upload_object,
            register_artifact=fake.register_artifact,
        )

        projection = normalize_solver_output_projection(
            run_id=run_id,
            snapshot_row=snapshot_row,
            run_dir=run_dir,
        )
        fake.replace_projection(
            run_id=run_id,
            sheets=projection.sheets,
            placements=projection.placements,
            unplaced=projection.unplaced,
            metrics=projection.metrics,
        )

        source_geometry_revision_ids = sorted(
            {
                str(item.get("source_geometry_revision_id") or "").strip()
                for item in snapshot_row.get("parts_manifest_jsonb", [])
                if isinstance(item, dict)
            }
        )
        source_geometry_revision_ids = [item for item in source_geometry_revision_ids if item]

        viewer_outline_map: dict[str, dict[str, Any]] = {}
        nesting_canonical_map: dict[str, dict[str, Any]] = {}
        for row in fake.tables["app.geometry_derivatives"]:
            geometry_revision_id = str(row.get("geometry_revision_id") or "").strip()
            derivative_kind = str(row.get("derivative_kind") or "").strip().lower()
            derivative_json = row.get("derivative_jsonb")
            if geometry_revision_id not in source_geometry_revision_ids or not isinstance(derivative_json, dict):
                continue
            if derivative_kind == "viewer_outline":
                viewer_outline_map[geometry_revision_id] = _copy_json(derivative_json)
            if derivative_kind == "nesting_canonical":
                nesting_canonical_map[geometry_revision_id] = _copy_json(derivative_json)

        svg_records = persist_sheet_svg_artifacts(
            project_id=project_id,
            run_id=run_id,
            storage_bucket="run-artifacts",
            snapshot_row=snapshot_row,
            projection_sheets=projection.sheets,
            projection_placements=projection.placements,
            viewer_outline_by_geometry_revision=viewer_outline_map,
            upload_object=fake.upload_object,
            register_artifact=fake.register_artifact,
        )

        dxf_records = persist_sheet_dxf_artifacts(
            project_id=project_id,
            run_id=run_id,
            storage_bucket="run-artifacts",
            snapshot_row=snapshot_row,
            projection_sheets=projection.sheets,
            projection_placements=projection.placements,
            nesting_canonical_by_geometry_revision=nesting_canonical_map,
            upload_object=fake.upload_object,
            register_artifact=fake.register_artifact,
        )

    run_updates = fake.update_rows(
        table="app.nesting_runs",
        access_token="internal",
        payload={
            "status": "done",
            "finished_at": _now_iso(),
            "solver_exit_code": 0,
            "placements_count": projection.summary.placed_count,
            "unplaced_count": projection.summary.unplaced_count,
            "sheet_count": projection.summary.used_sheet_count,
        },
        filters={"id": f"eq.{run_id}"},
    )
    _assert(len(run_updates) == 1, "run status update failed")

    return {
        "solver_input": solver_input,
        "raw_records": raw_records,
        "projection": projection,
        "svg_records": svg_records,
        "dxf_records": dxf_records,
    }


def main() -> int:
    owner_user_id = "00000000-0000-0000-0000-000000000001"
    access_token = "token-pilot"
    fake = FakeSupabaseClient()

    project_id = _seed_project(fake, owner_user_id=owner_user_id)

    file_row, geometry_revision = _ingest_file_and_import_geometry(
        fake,
        owner_user_id=owner_user_id,
        project_id=project_id,
        access_token=access_token,
    )
    _assert(str(geometry_revision.get("status") or "").lower() == "validated", "geometry revision not validated")

    derivatives_for_geometry = [
        row
        for row in fake.tables["app.geometry_derivatives"]
        if str(row.get("geometry_revision_id") or "") == str(geometry_revision.get("id") or "")
    ]
    derivative_kinds = sorted({str(row.get("derivative_kind") or "") for row in derivatives_for_geometry})
    _assert(derivative_kinds == ["nesting_canonical", "viewer_outline"], "unexpected derivative kinds")

    part_result = create_part_from_geometry_revision(
        supabase=fake,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id,
        raw_code="PILOT-PART-001",
        raw_name="Pilot Part 001",
        geometry_revision_id=str(geometry_revision["id"]),
        raw_source_label="h1_e7_t1_pilot",
    )
    part_revision_id = str(part_result["part_revision"]["id"])

    sheet_result = create_sheet_revision(
        supabase=fake,
        access_token=access_token,
        owner_user_id=owner_user_id,
        raw_code="PILOT-SHEET-001",
        raw_name="Pilot Sheet 001",
        raw_width_mm=1200.0,
        raw_height_mm=2400.0,
        raw_source_label="h1_e7_t1_pilot",
    )
    sheet_revision_id = str(sheet_result["sheet_revision"]["id"])

    requirement_result = create_or_update_project_part_requirement(
        supabase=fake,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id,
        part_revision_id=part_revision_id,
        raw_required_qty=1,
        raw_placement_priority=10,
        raw_placement_policy="normal",
        raw_is_active=True,
        raw_notes="pilot requirement",
    )
    _assert(bool(requirement_result.get("project_part_requirement")), "project part requirement missing")

    sheet_input_result = create_or_update_project_sheet_input(
        supabase=fake,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id,
        sheet_revision_id=sheet_revision_id,
        raw_required_qty=1,
        raw_is_active=True,
        raw_is_default=True,
        raw_placement_priority=0,
        raw_notes="pilot sheet input",
    )
    _assert(bool(sheet_input_result.get("project_sheet_input")), "project sheet input missing")

    run_create_result = create_queued_run_from_project_snapshot(
        supabase=fake,
        access_token=access_token,
        owner_user_id=owner_user_id,
        project_id=project_id,
        run_purpose="h1_e7_t1_pilot",
        idempotency_key="h1_e7_t1-pilot-001",
    )
    _assert(run_create_result.get("was_deduplicated") is False, "pilot create should not deduplicate")

    run_row = run_create_result["run"]
    run_id = str(run_row["id"])
    snapshot_row = run_create_result["snapshot"]

    fake.update_rows(
        table="app.nesting_runs",
        access_token="internal",
        payload={"status": "running", "started_at": _now_iso()},
        filters={"id": f"eq.{run_id}"},
    )

    worker_result = _worker_like_projection_and_artifacts(
        fake,
        run_id=run_id,
        project_id=project_id,
        snapshot_row=snapshot_row,
    )

    done_row = fake.select_rows(
        table="app.nesting_runs",
        access_token="internal",
        params={"id": f"eq.{run_id}", "limit": "1"},
    )[0]
    _assert(str(done_row.get("status") or "") == "done", "run did not reach done status")

    projection_sheet_rows = [row for row in fake.tables["app.run_layout_sheets"] if str(row.get("run_id") or "") == run_id]
    projection_placement_rows = [
        row for row in fake.tables["app.run_layout_placements"] if str(row.get("run_id") or "") == run_id
    ]
    metrics_rows = [row for row in fake.tables["app.run_metrics"] if str(row.get("run_id") or "") == run_id]

    _assert(len(projection_sheet_rows) > 0, "projection sheets are empty")
    _assert(len(projection_placement_rows) > 0, "projection placements are empty")
    _assert(len(metrics_rows) == 1, "run_metrics row missing")

    metrics_row = metrics_rows[0]
    _assert(int(metrics_row.get("placed_count") or 0) > 0, "run_metrics.placed_count must be > 0")
    _assert(int(metrics_row.get("used_sheet_count") or 0) > 0, "run_metrics.used_sheet_count must be > 0")

    artifact_rows = [row for row in fake.tables["app.run_artifacts"] if str(row.get("run_id") or "") == run_id]
    artifact_kinds = sorted({str(row.get("artifact_kind") or "") for row in artifact_rows})

    required_artifact_kinds = {"solver_output", "sheet_svg", "sheet_dxf"}
    missing_artifacts = sorted(required_artifact_kinds - set(artifact_kinds))
    _assert(not missing_artifacts, f"missing required artifact kinds: {missing_artifacts}")

    summary = {
        "project_id": project_id,
        "run_id": run_id,
        "source_file_object_id": str(file_row["id"]),
        "geometry_revision_id": str(geometry_revision["id"]),
        "part_revision_id": part_revision_id,
        "sheet_revision_id": sheet_revision_id,
        "run_status": str(done_row.get("status") or ""),
        "projection": {
            "sheet_rows": len(projection_sheet_rows),
            "placement_rows": len(projection_placement_rows),
            "unplaced_rows": len(
                [row for row in fake.tables["app.run_layout_unplaced"] if str(row.get("run_id") or "") == run_id]
            ),
            "placed_count": int(metrics_row.get("placed_count") or 0),
            "sheet_count": int(metrics_row.get("used_sheet_count") or 0),
        },
        "artifact_kinds": artifact_kinds,
        "artifact_count": len(artifact_rows),
        "raw_artifact_count": len(worker_result["raw_records"]),
        "sheet_svg_count": len(worker_result["svg_records"]),
        "sheet_dxf_count": len(worker_result["dxf_records"]),
        "snapshot_hash_sha256": str(snapshot_row.get("snapshot_hash_sha256") or ""),
    }

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    print("PASS: H1-E7-T1 end-to-end pilot project smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
