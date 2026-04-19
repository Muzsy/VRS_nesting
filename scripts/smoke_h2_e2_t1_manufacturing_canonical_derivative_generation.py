#!/usr/bin/env python3
"""H2-E2-T1 smoke: manufacturing_canonical derivative generation + part binding."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import ezdxf
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser, get_current_user
from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.main import app as main_app
from api.routes.parts import router as parts_router
from api.services.geometry_derivative_generator import generate_h1_minimum_geometry_derivatives
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.file_objects: dict[str, dict[str, Any]] = {}
        self.geometry_revisions: dict[str, dict[str, Any]] = {}
        self.geometry_validation_reports: dict[str, dict[str, Any]] = {}
        self.geometry_derivatives: dict[str, dict[str, Any]] = {}
        self.part_definitions: dict[str, dict[str, Any]] = {}
        self.part_revisions: dict[str, dict[str, Any]] = {}
        self.storage: dict[tuple[str, str], bytes] = {}

    def get_auth_user(self, access_token: str) -> dict[str, Any]:
        if access_token == "token-u1":
            return {"id": "00000000-0000-0000-0000-000000000001", "email": "u1@example.com"}
        raise RuntimeError("invalid token")

    def _rows_for_table(self, table: str) -> list[dict[str, Any]]:
        if table == "app.projects":
            return list(self.projects.values())
        if table == "app.file_objects":
            return list(self.file_objects.values())
        if table == "app.geometry_revisions":
            return list(self.geometry_revisions.values())
        if table == "app.geometry_validation_reports":
            return list(self.geometry_validation_reports.values())
        if table == "app.geometry_derivatives":
            return list(self.geometry_derivatives.values())
        if table == "app.part_definitions":
            return list(self.part_definitions.values())
        if table == "app.part_revisions":
            return list(self.part_revisions.values())
        return []

    @staticmethod
    def _matches(row: dict[str, Any], key: str, raw_filter: str) -> bool:
        value = row.get(key)
        if raw_filter.startswith("eq."):
            return str(value) == raw_filter[3:]
        if raw_filter.startswith("neq."):
            return str(value) != raw_filter[4:]
        if raw_filter.startswith("gte."):
            return str(value or "") >= raw_filter[4:]
        return True

    @staticmethod
    def _apply_order(rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
        ordered = list(rows)
        for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
            key = token.split(".")[0]
            reverse = ".desc" in token
            ordered.sort(key=lambda row: str(row.get(key) or ""), reverse=reverse)
        return ordered

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = self._rows_for_table(table)

        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        order_clause = params.get("order", "").strip()
        if order_clause:
            rows = self._apply_order(rows, order_clause)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = params.get("limit", "")
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]
        return [dict(row) for row in rows]

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        now = datetime.now(timezone.utc).isoformat()
        row = dict(payload)

        if table == "app.file_objects":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.file_objects[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_revisions":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.geometry_revisions[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_validation_reports":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.geometry_validation_reports[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_derivatives":
            for existing in self.geometry_derivatives.values():
                if (
                    str(existing.get("geometry_revision_id")) == str(row.get("geometry_revision_id"))
                    and str(existing.get("derivative_kind")) == str(row.get("derivative_kind"))
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint geometry_derivatives_geometry_revision_kind")
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.geometry_derivatives[str(row["id"])] = row
            return dict(row)

        if table == "app.part_definitions":
            for existing in self.part_definitions.values():
                if (
                    str(existing.get("owner_user_id")) == str(row.get("owner_user_id"))
                    and str(existing.get("code")) == str(row.get("code"))
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint part_definitions_owner_user_id_code_key")
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.part_definitions[str(row["id"])] = row
            return dict(row)

        if table == "app.part_revisions":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.part_revisions[str(row["id"])] = row
            return dict(row)

        raise RuntimeError(f"unsupported table insert: {table}")

    def update_rows(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        if table == "app.geometry_revisions":
            storage = self.geometry_revisions
        elif table == "app.geometry_derivatives":
            storage = self.geometry_derivatives
        elif table == "app.part_definitions":
            storage = self.part_definitions
        elif table == "app.part_revisions":
            storage = self.part_revisions
        else:
            return []

        rows = list(storage.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            current = storage[str(row["id"])]
            current.update(payload)
            current["updated_at"] = now
            updated.append(dict(current))
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = (table, access_token, filters)

    def remove_object(self, *, access_token: str, bucket: str, object_key: str) -> None:
        _ = access_token
        self.storage.pop((bucket, object_key), None)

    def create_signed_upload_url(
        self, *, access_token: str, bucket: str, object_key: str, expires_in: int = 300,
    ) -> dict[str, Any]:
        _ = (access_token, expires_in)
        token = str(uuid4())
        return {
            "upload_url": f"https://upload.local/{bucket}/{object_key}?token={token}",
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }

    def create_signed_download_url(
        self, *, access_token: str, bucket: str, object_key: str, expires_in: int = 900,
    ) -> dict[str, Any]:
        _ = (access_token, expires_in)
        return {
            "download_url": f"https://download.local/{bucket}/{object_key}",
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }

    def download_signed_object(self, *, signed_url: str) -> bytes:
        parsed = urlparse(signed_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            raise SupabaseHTTPError("invalid signed download path")
        bucket = path_parts[0]
        object_key = "/".join(path_parts[1:])
        blob = self.storage.get((bucket, object_key))
        if blob is None:
            raise SupabaseHTTPError("object not found")
        return blob

    def put_uploaded_object(self, *, signed_upload_url: str, blob: bytes) -> tuple[str, str]:
        parsed = urlparse(signed_upload_url)
        _ = parse_qs(parsed.query)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise RuntimeError("invalid upload path")
        bucket = parts[0]
        object_key = "/".join(parts[1:])
        self.storage[(bucket, object_key)] = blob
        return bucket, object_key

    def execute_rpc(
        self, *, function_name: str, access_token: str, payload: dict[str, Any] | None = None,
    ) -> Any:
        _ = access_token
        if function_name != "create_part_revision_atomic":
            raise SupabaseHTTPError(f"unsupported rpc function: {function_name}")

        args = payload or {}
        part_definition_id = str(args.get("p_part_definition_id") or "").strip()
        if not part_definition_id:
            raise SupabaseHTTPError("missing p_part_definition_id")
        part_definition = self.part_definitions.get(part_definition_id)
        if part_definition is None:
            raise SupabaseHTTPError("part_definition not found")

        revision_numbers = [
            int(row.get("revision_no") or 0)
            for row in self.part_revisions.values()
            if str(row.get("part_definition_id") or "").strip() == part_definition_id
        ]
        next_revision_no = (max(revision_numbers) if revision_numbers else 0) + 1

        now = datetime.now(timezone.utc).isoformat()
        part_revision_id = str(uuid4())
        part_revision = {
            "id": part_revision_id,
            "part_definition_id": part_definition_id,
            "revision_no": next_revision_no,
            "lifecycle": "approved",
            "source_label": args.get("p_source_label"),
            "source_checksum_sha256": args.get("p_source_checksum_sha256"),
            "notes": args.get("p_notes"),
            "source_geometry_revision_id": str(args.get("p_source_geometry_revision_id") or "").strip() or None,
            "selected_nesting_derivative_id": str(args.get("p_selected_nesting_derivative_id") or "").strip() or None,
            "selected_manufacturing_derivative_id": str(args.get("p_selected_manufacturing_derivative_id") or "").strip() or None,
            "created_at": now,
            "updated_at": now,
        }
        self.part_revisions[part_revision_id] = part_revision

        part_definition["current_revision_id"] = part_revision_id
        part_definition["updated_at"] = now

        return {
            "part_definition": dict(part_definition),
            "part_revision": dict(part_revision),
        }


def _make_valid_dxf_bytes() -> bytes:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="vrs_h2e2t1_ok_") as tmp:
        tmp_path = Path(tmp) / "part.dxf"
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_lwpolyline(
            [(0.0, 0.0), (120.0, 0.0), (120.0, 80.0), (0.0, 80.0)],
            dxfattribs={"layer": "CUT_OUTER", "closed": True},
        )
        msp.add_lwpolyline(
            [(10.0, 10.0), (30.0, 10.0), (30.0, 25.0), (10.0, 25.0)],
            dxfattribs={"layer": "CUT_INNER", "closed": True},
        )
        doc.saveas(tmp_path)
        return tmp_path.read_bytes()


def _settings() -> Settings:
    return Settings(
        supabase_url="https://fake.supabase.local",
        supabase_anon_key="fake-anon",
        supabase_project_ref="",
        supabase_db_password="",
        database_url="",
        storage_bucket="source-files",
        max_dxf_size_mb=50,
        rate_limit_window_s=60,
        rate_limit_runs_per_window=10,
        rate_limit_bundles_per_window=4,
        rate_limit_upload_urls_per_window=100,
        signed_url_ttl_s=300,
        enable_security_headers=False,
        allowed_origins=("http://localhost:5173",),
    )


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _build_part_test_app(fake: FakeSupabaseClient) -> FastAPI:
    app = FastAPI()
    app.include_router(parts_router, prefix="/v1")
    app.dependency_overrides[get_supabase_client] = lambda: fake
    app.dependency_overrides[get_settings] = _settings
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000001",
        email="u1@example.com",
        access_token="token-u1",
    )
    return app


def main() -> int:
    fake = FakeSupabaseClient()
    main_app.dependency_overrides[get_supabase_client] = lambda: fake
    main_app.dependency_overrides[get_settings] = _settings

    try:
        client = TestClient(main_app)
        headers = {"Authorization": "Bearer token-u1"}
        user_id = "00000000-0000-0000-0000-000000000001"
        project_id = str(uuid4())
        fake.projects[project_id] = {
            "id": project_id,
            "owner_user_id": user_id,
            "lifecycle": "draft",
        }

        # ======================================================================
        # TEST 1: Valid geometry -> three derivatives generated
        # ======================================================================
        ok_upload_resp = client.post(
            f"/v1/projects/{project_id}/files/upload-url",
            headers=headers,
            json={
                "filename": "part_ok.dxf",
                "content_type": "application/dxf",
                "size_bytes": 1024,
                "file_kind": "source_dxf",
            },
        )
        if ok_upload_resp.status_code != 200:
            raise RuntimeError(f"ok upload-url failed: {ok_upload_resp.status_code} {ok_upload_resp.text}")
        ok_upload = ok_upload_resp.json()
        ok_file_id = str(ok_upload["file_id"])
        ok_storage_path = str(ok_upload["storage_path"])
        fake.put_uploaded_object(signed_upload_url=str(ok_upload["upload_url"]), blob=_make_valid_dxf_bytes())

        ok_complete_resp = client.post(
            f"/v1/projects/{project_id}/files",
            headers=headers,
            json={
                "file_id": ok_file_id,
                "storage_path": ok_storage_path,
                "file_kind": "source_dxf",
            },
        )
        if ok_complete_resp.status_code != 200:
            raise RuntimeError(f"ok complete failed: {ok_complete_resp.status_code} {ok_complete_resp.text}")

        ok_revisions = [row for row in fake.geometry_revisions.values() if str(row.get("source_file_object_id")) == ok_file_id]
        if len(ok_revisions) != 1:
            raise RuntimeError(f"expected 1 geometry revision for ok file, got {len(ok_revisions)}")
        ok_revision = ok_revisions[0]
        if ok_revision.get("status") != "validated":
            raise RuntimeError("valid geometry should end in validated status")

        revision_id = str(ok_revision.get("id"))
        derivatives = [row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) == revision_id]
        if len(derivatives) != 3:
            raise RuntimeError(f"expected exactly 3 derivatives for validated geometry, got {len(derivatives)}")

        by_kind = {str(row.get("derivative_kind")): row for row in derivatives}
        expected_kinds = {"nesting_canonical", "viewer_outline", "manufacturing_canonical"}
        if set(by_kind.keys()) != expected_kinds:
            raise RuntimeError(f"unexpected derivative kinds: {sorted(by_kind.keys())}")

        print("  [OK] Test 1: valid geometry produces 3 derivatives")

        # ======================================================================
        # TEST 2: Manufacturing payload is NOT an alias of nesting payload
        # ======================================================================
        nesting = by_kind["nesting_canonical"]
        manufacturing = by_kind["manufacturing_canonical"]
        viewer = by_kind["viewer_outline"]

        nesting_json = nesting.get("derivative_jsonb")
        manufacturing_json = manufacturing.get("derivative_jsonb")
        viewer_json = viewer.get("derivative_jsonb")

        if not isinstance(nesting_json, dict) or not isinstance(manufacturing_json, dict):
            raise RuntimeError("missing derivative payloads")

        # Structural difference: nesting has "polygon", manufacturing has "contours"
        if nesting_json == manufacturing_json:
            raise RuntimeError("manufacturing_canonical payload must differ from nesting_canonical")
        if "polygon" not in nesting_json:
            raise RuntimeError("nesting_canonical should have 'polygon' key")
        if "contours" not in manufacturing_json:
            raise RuntimeError("manufacturing_canonical should have 'contours' key")
        if "polygon" in manufacturing_json:
            raise RuntimeError("manufacturing_canonical must NOT have 'polygon' key (that's nesting structure)")
        if "contours" in nesting_json:
            raise RuntimeError("nesting_canonical must NOT have 'contours' key (that's manufacturing structure)")

        # Manufacturing contours should separate outer and holes
        contours = manufacturing_json["contours"]
        if not isinstance(contours, list) or len(contours) < 1:
            raise RuntimeError("manufacturing contours must be a non-empty list")
        outer_contours = [c for c in contours if c.get("contour_role") == "outer"]
        hole_contours = [c for c in contours if c.get("contour_role") == "hole"]
        if len(outer_contours) != 1:
            raise RuntimeError(f"expected 1 outer contour, got {len(outer_contours)}")
        if len(hole_contours) != 1:
            raise RuntimeError(f"expected 1 hole contour (from DXF with inner ring), got {len(hole_contours)}")

        contour_summary = manufacturing_json.get("contour_summary")
        if not isinstance(contour_summary, dict):
            raise RuntimeError("manufacturing payload must have contour_summary")
        if contour_summary.get("outer_count") != 1 or contour_summary.get("hole_count") != 1:
            raise RuntimeError("contour_summary counts mismatch")

        print("  [OK] Test 2: manufacturing payload is structurally distinct from nesting")

        # ======================================================================
        # TEST 3: All derivative records have correct metadata fields
        # ======================================================================
        for kind, row in by_kind.items():
            if row.get("producer_version") != "geometry_derivative_generator.v1":
                raise RuntimeError(f"producer_version mismatch for {kind}")
            if row.get("source_geometry_hash_sha256") != ok_revision.get("canonical_hash_sha256"):
                raise RuntimeError(f"source_geometry_hash_sha256 mismatch for {kind}")
            derivative_json = row.get("derivative_jsonb")
            if not isinstance(derivative_json, dict):
                raise RuntimeError(f"derivative_jsonb missing for {kind}")
            expected_hash = _canonical_hash(derivative_json)
            if row.get("derivative_hash_sha256") != expected_hash:
                raise RuntimeError(f"derivative_hash_sha256 mismatch for {kind}")

        if nesting.get("format_version") != "nesting_canonical.v1":
            raise RuntimeError("nesting format_version mismatch")
        if viewer.get("format_version") != "viewer_outline.v1":
            raise RuntimeError("viewer format_version mismatch")
        if manufacturing.get("format_version") != "manufacturing_canonical.v1":
            raise RuntimeError("manufacturing format_version mismatch")

        print("  [OK] Test 3: derivative metadata fields correct for all 3 kinds")

        # ======================================================================
        # TEST 4: Regeneration is idempotent (no duplicate manufacturing rows)
        # ======================================================================
        ids_before = {kind: str(row.get("id")) for kind, row in by_kind.items()}
        hashes_before = {kind: str(row.get("derivative_hash_sha256")) for kind, row in by_kind.items()}

        regenerate_result = generate_h1_minimum_geometry_derivatives(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            geometry_revision=ok_revision,
        )
        generated = regenerate_result.get("generated")
        if not isinstance(generated, dict) or set(generated.keys()) != expected_kinds:
            raise RuntimeError("regenerate result missing kinds")

        derivatives_after = [row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) == revision_id]
        if len(derivatives_after) != 3:
            raise RuntimeError(f"regenerate should not create duplicate derivative rows (got {len(derivatives_after)})")

        by_kind_after = {str(row.get("derivative_kind")): row for row in derivatives_after}
        for kind in expected_kinds:
            if str(by_kind_after[kind].get("id")) != ids_before[kind]:
                raise RuntimeError(f"regenerate should reuse existing derivative id for {kind}")
            if str(by_kind_after[kind].get("derivative_hash_sha256")) != hashes_before[kind]:
                raise RuntimeError(f"regenerate hash changed unexpectedly for {kind}")

        print("  [OK] Test 4: regeneration is idempotent, no duplicates")

        # ======================================================================
        # TEST 5: Rejected geometry -> no derivatives at all
        # ======================================================================
        rejected_revision = fake.insert_row(
            table="app.geometry_revisions",
            access_token="token-u1",
            payload={
                "project_id": project_id,
                "source_file_object_id": str(uuid4()),
                "geometry_role": "part",
                "revision_no": 999,
                "status": "rejected",
                "canonical_format_version": "normalized_geometry.v1",
                "canonical_geometry_jsonb": {
                    "geometry_role": "part",
                    "format_version": "normalized_geometry.v1",
                    "units": "mm",
                    "outer_ring": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
                    "hole_rings": [],
                    "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 1.0, "max_y": 1.0, "width": 1.0, "height": 1.0},
                },
                "canonical_hash_sha256": "abc",
                "source_hash_sha256": "def",
                "bbox_jsonb": {"min_x": 0.0, "min_y": 0.0, "max_x": 1.0, "max_y": 1.0, "width": 1.0, "height": 1.0},
                "created_by": user_id,
            },
        )
        rejected_result = generate_h1_minimum_geometry_derivatives(
            supabase=fake,  # type: ignore[arg-type]
            access_token="token-u1",
            geometry_revision=rejected_revision,
        )
        if not str(rejected_result.get("skipped_reason") or ""):
            raise RuntimeError("rejected geometry should return skipped_reason")
        rejected_derivatives = [
            row for row in fake.geometry_derivatives.values() if str(row.get("geometry_revision_id")) == str(rejected_revision.get("id"))
        ]
        if rejected_derivatives:
            raise RuntimeError("rejected geometry must not create any derivative rows (including manufacturing)")

        print("  [OK] Test 5: rejected geometry produces no derivatives")

        # ======================================================================
        # TEST 6: Part creation binds both nesting AND manufacturing derivatives
        # ======================================================================
        main_app.dependency_overrides.clear()

        part_fake = FakeSupabaseClient()
        part_app = _build_part_test_app(part_fake)
        part_client = TestClient(part_app)

        part_fake.projects[project_id] = {
            "id": project_id,
            "owner_user_id": user_id,
            "lifecycle": "draft",
        }

        geo_rev_id = str(uuid4())
        part_fake.insert_row(
            table="app.geometry_revisions",
            access_token="token-u1",
            payload={
                "id": geo_rev_id,
                "project_id": project_id,
                "source_file_object_id": str(uuid4()),
                "geometry_role": "part",
                "revision_no": 1,
                "status": "validated",
                "canonical_format_version": "normalized_geometry.v1",
                "canonical_geometry_jsonb": {},
                "canonical_hash_sha256": "testhash1",
                "source_hash_sha256": "testhash1",
            },
        )

        nesting_deriv_id = str(uuid4())
        part_fake.insert_row(
            table="app.geometry_derivatives",
            access_token="token-u1",
            payload={
                "id": nesting_deriv_id,
                "geometry_revision_id": geo_rev_id,
                "derivative_kind": "nesting_canonical",
                "producer_version": "smoke",
                "format_version": "nesting_canonical.v1",
                "derivative_jsonb": {"k": "nesting_canonical"},
            },
        )

        mfg_deriv_id = str(uuid4())
        part_fake.insert_row(
            table="app.geometry_derivatives",
            access_token="token-u1",
            payload={
                "id": mfg_deriv_id,
                "geometry_revision_id": geo_rev_id,
                "derivative_kind": "manufacturing_canonical",
                "producer_version": "smoke",
                "format_version": "manufacturing_canonical.v1",
                "derivative_jsonb": {"k": "manufacturing_canonical"},
            },
        )

        part_resp = part_client.post(
            f"/v1/projects/{project_id}/parts",
            json={
                "code": "PART-MFG-001",
                "name": "Manufacturing bound part",
                "geometry_revision_id": geo_rev_id,
            },
        )
        if part_resp.status_code != 201:
            raise RuntimeError(f"part creation failed: {part_resp.status_code} {part_resp.text}")

        part_payload = part_resp.json()
        if part_payload.get("selected_nesting_derivative_id") != nesting_deriv_id:
            raise RuntimeError("part revision should reference nesting derivative")

        # The API response model doesn't expose manufacturing derivative id yet (route not in scope),
        # so we verify the binding via the persisted part_revision row directly.
        part_rev_id = str(part_payload.get("part_revision_id"))
        rev_row = part_fake.part_revisions.get(part_rev_id)
        if not rev_row:
            raise RuntimeError("part_revision row not found after create")
        if str(rev_row.get("selected_nesting_derivative_id")) != nesting_deriv_id:
            raise RuntimeError("persisted nesting derivative id mismatch")
        if str(rev_row.get("selected_manufacturing_derivative_id")) != mfg_deriv_id:
            raise RuntimeError("persisted manufacturing derivative id mismatch")
        if str(rev_row.get("source_geometry_revision_id")) != geo_rev_id:
            raise RuntimeError("source_geometry_revision_id mismatch — same-geometry integrity broken")

        print("  [OK] Test 6: part creation binds both nesting and manufacturing derivatives")

        part_app.dependency_overrides.clear()

        print("\n[PASS] H2-E2-T1 manufacturing_canonical derivative generation smoke passed")
        return 0
    finally:
        main_app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
