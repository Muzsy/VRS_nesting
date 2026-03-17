#!/usr/bin/env python3
"""H1-E3-T1 smoke: part creation service + derivative binding (H1 minimum)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.main import app
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.geometry_revisions: dict[str, dict[str, Any]] = {}
        self.geometry_derivatives: dict[str, dict[str, Any]] = {}
        self.part_definitions: dict[str, dict[str, Any]] = {}
        self.part_revisions: dict[str, dict[str, Any]] = {}

    def get_auth_user(self, access_token: str) -> dict[str, Any]:
        if access_token == "token-u1":
            return {"id": "00000000-0000-0000-0000-000000000001", "email": "u1@example.com"}
        raise RuntimeError("invalid token")

    def _rows_for_table(self, table: str) -> list[dict[str, Any]]:
        if table == "app.projects":
            return list(self.projects.values())
        if table == "app.geometry_revisions":
            return list(self.geometry_revisions.values())
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
            for existing in self.part_revisions.values():
                if (
                    str(existing.get("part_definition_id")) == str(row.get("part_definition_id"))
                    and int(existing.get("revision_no") or 0) == int(row.get("revision_no") or 0)
                ):
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint part_revisions_part_definition_id_revision_no_key"
                    )
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.part_revisions[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_revisions":
            row.setdefault("id", str(uuid4()))
            self.geometry_revisions[str(row["id"])] = row
            return dict(row)

        if table == "app.geometry_derivatives":
            row.setdefault("id", str(uuid4()))
            self.geometry_derivatives[str(row["id"])] = row
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
        if table == "app.part_definitions":
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



def _add_geometry_revision(
    fake: FakeSupabaseClient,
    *,
    project_id: str,
    status: str,
    canonical_hash: str,
) -> str:
    row = fake.insert_row(
        table="app.geometry_revisions",
        access_token="token-u1",
        payload={
            "id": str(uuid4()),
            "project_id": project_id,
            "source_file_object_id": str(uuid4()),
            "geometry_role": "part",
            "revision_no": 1,
            "status": status,
            "canonical_format_version": "normalized_geometry.v1",
            "canonical_geometry_jsonb": {},
            "canonical_hash_sha256": canonical_hash,
            "source_hash_sha256": canonical_hash,
        },
    )
    return str(row["id"])



def _add_derivative(fake: FakeSupabaseClient, *, geometry_revision_id: str, derivative_kind: str) -> str:
    row = fake.insert_row(
        table="app.geometry_derivatives",
        access_token="token-u1",
        payload={
            "id": str(uuid4()),
            "geometry_revision_id": geometry_revision_id,
            "derivative_kind": derivative_kind,
            "producer_version": "smoke",
            "format_version": "smoke.v1",
            "derivative_jsonb": {"k": derivative_kind},
        },
    )
    return str(row["id"])



def main() -> int:
    fake = FakeSupabaseClient()
    app.dependency_overrides[get_supabase_client] = lambda: fake
    app.dependency_overrides[get_settings] = _settings

    try:
        client = TestClient(app)
        headers = {"Authorization": "Bearer token-u1"}
        user_id = "00000000-0000-0000-0000-000000000001"

        project_id = str(uuid4())
        other_project_id = str(uuid4())
        fake.projects[project_id] = {
            "id": project_id,
            "owner_user_id": user_id,
            "lifecycle": "draft",
        }
        fake.projects[other_project_id] = {
            "id": other_project_id,
            "owner_user_id": user_id,
            "lifecycle": "draft",
        }

        ok_geometry_1 = _add_geometry_revision(
            fake,
            project_id=project_id,
            status="validated",
            canonical_hash="okhash1",
        )
        ok_derivative_1 = _add_derivative(fake, geometry_revision_id=ok_geometry_1, derivative_kind="nesting_canonical")

        create_new_resp = client.post(
            f"/v1/projects/{project_id}/parts",
            headers=headers,
            json={
                "code": "PART-001",
                "name": "Main plate",
                "geometry_revision_id": ok_geometry_1,
                "notes": "initial",
                "source_label": "source_dxf",
            },
        )
        if create_new_resp.status_code != 201:
            raise RuntimeError(f"new definition create failed: {create_new_resp.status_code} {create_new_resp.text}")
        new_payload = create_new_resp.json()

        if new_payload.get("revision_no") != 1:
            raise RuntimeError("new definition should start with revision_no=1")
        if new_payload.get("was_existing_definition"):
            raise RuntimeError("new definition branch should return was_existing_definition=false")
        if new_payload.get("selected_nesting_derivative_id") != ok_derivative_1:
            raise RuntimeError("selected_nesting_derivative_id mismatch for first revision")

        def_id = str(new_payload.get("part_definition_id"))
        rev1_id = str(new_payload.get("part_revision_id"))
        definition_row = fake.part_definitions.get(def_id)
        revision_row = fake.part_revisions.get(rev1_id)
        if not definition_row or not revision_row:
            raise RuntimeError("missing part rows after successful create")
        if str(definition_row.get("current_revision_id")) != rev1_id:
            raise RuntimeError("current_revision_id did not point to first revision")
        if str(revision_row.get("source_geometry_revision_id")) != ok_geometry_1:
            raise RuntimeError("source_geometry_revision_id mismatch")
        if str(revision_row.get("selected_nesting_derivative_id")) != ok_derivative_1:
            raise RuntimeError("selected_nesting_derivative_id not persisted on part_revision")
        if str(revision_row.get("source_checksum_sha256")) != "okhash1":
            raise RuntimeError("source_checksum_sha256 should come from geometry canonical hash")

        ok_geometry_2 = _add_geometry_revision(
            fake,
            project_id=project_id,
            status="validated",
            canonical_hash="okhash2",
        )
        ok_derivative_2 = _add_derivative(fake, geometry_revision_id=ok_geometry_2, derivative_kind="nesting_canonical")

        create_existing_resp = client.post(
            f"/v1/projects/{project_id}/parts",
            headers=headers,
            json={
                "code": "PART-001",
                "name": "Main plate v2 title ignored",
                "geometry_revision_id": ok_geometry_2,
                "notes": "second revision",
                "source_label": "source_dxf",
            },
        )
        if create_existing_resp.status_code != 201:
            raise RuntimeError(
                f"existing definition create failed: {create_existing_resp.status_code} {create_existing_resp.text}"
            )
        existing_payload = create_existing_resp.json()

        if not existing_payload.get("was_existing_definition"):
            raise RuntimeError("existing definition branch should return was_existing_definition=true")
        if existing_payload.get("part_definition_id") != def_id:
            raise RuntimeError("existing definition branch must reuse part_definition")
        if existing_payload.get("revision_no") != 2:
            raise RuntimeError("existing definition branch should allocate next revision_no=2")
        if existing_payload.get("selected_nesting_derivative_id") != ok_derivative_2:
            raise RuntimeError("second revision selected_nesting_derivative_id mismatch")

        rev2_id = str(existing_payload.get("part_revision_id"))
        definition_row = fake.part_definitions.get(def_id)
        if not definition_row or str(definition_row.get("current_revision_id")) != rev2_id:
            raise RuntimeError("current_revision_id did not advance to second revision")

        if len(fake.part_definitions) != 1:
            raise RuntimeError("existing-definition branch should not create a new part_definition")
        if len(fake.part_revisions) != 2:
            raise RuntimeError("expected two part_revisions after second successful create")

        missing_derivative_geometry = _add_geometry_revision(
            fake,
            project_id=project_id,
            status="validated",
            canonical_hash="missingderiv",
        )
        _add_derivative(fake, geometry_revision_id=missing_derivative_geometry, derivative_kind="viewer_outline")

        before_missing = len(fake.part_revisions)
        missing_derivative_resp = client.post(
            f"/v1/projects/{project_id}/parts",
            headers=headers,
            json={
                "code": "PART-002",
                "name": "Missing derivative",
                "geometry_revision_id": missing_derivative_geometry,
            },
        )
        if missing_derivative_resp.status_code != 400:
            raise RuntimeError(
                "missing-derivative branch should fail with HTTP 400 "
                f"(got {missing_derivative_resp.status_code})"
            )
        if "missing nesting_canonical derivative" not in missing_derivative_resp.text:
            raise RuntimeError("missing-derivative response did not mention missing nesting_canonical")
        if len(fake.part_revisions) != before_missing:
            raise RuntimeError("missing-derivative branch created a part_revision unexpectedly")

        not_validated_geometry = _add_geometry_revision(
            fake,
            project_id=project_id,
            status="parsed",
            canonical_hash="parsedhash",
        )
        _add_derivative(fake, geometry_revision_id=not_validated_geometry, derivative_kind="nesting_canonical")

        before_not_validated = len(fake.part_revisions)
        not_validated_resp = client.post(
            f"/v1/projects/{project_id}/parts",
            headers=headers,
            json={
                "code": "PART-003",
                "name": "Parsed geometry",
                "geometry_revision_id": not_validated_geometry,
            },
        )
        if not_validated_resp.status_code != 400:
            raise RuntimeError(
                "non-validated geometry branch should fail with HTTP 400 "
                f"(got {not_validated_resp.status_code})"
            )
        if "not validated" not in not_validated_resp.text:
            raise RuntimeError("non-validated response did not mention status check")
        if len(fake.part_revisions) != before_not_validated:
            raise RuntimeError("non-validated branch created a part_revision unexpectedly")

        foreign_geometry = _add_geometry_revision(
            fake,
            project_id=other_project_id,
            status="validated",
            canonical_hash="foreignhash",
        )
        _add_derivative(fake, geometry_revision_id=foreign_geometry, derivative_kind="nesting_canonical")

        before_foreign = len(fake.part_revisions)
        foreign_resp = client.post(
            f"/v1/projects/{project_id}/parts",
            headers=headers,
            json={
                "code": "PART-004",
                "name": "Foreign geometry",
                "geometry_revision_id": foreign_geometry,
            },
        )
        if foreign_resp.status_code != 403:
            raise RuntimeError(
                "foreign-project branch should fail with HTTP 403 "
                f"(got {foreign_resp.status_code})"
            )
        if "does not belong to project" not in foreign_resp.text:
            raise RuntimeError("foreign-project response did not mention project boundary")
        if len(fake.part_revisions) != before_foreign:
            raise RuntimeError("foreign-project branch created a part_revision unexpectedly")

        print("[PASS] H1-E3-T1 part creation service es derivative binding smoke passed")
        return 0
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
