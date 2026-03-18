#!/usr/bin/env python3
"""H1-E3-T2 smoke: sheet creation service (H1 minimum)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser, get_current_user
from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.routes.sheets import router as sheets_router
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.sheet_definitions: dict[str, dict[str, Any]] = {}
        self.sheet_revisions: dict[str, dict[str, Any]] = {}

    def _rows_for_table(self, table: str) -> list[dict[str, Any]]:
        if table == "app.sheet_definitions":
            return list(self.sheet_definitions.values())
        if table == "app.sheet_revisions":
            return list(self.sheet_revisions.values())
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

        if table == "app.sheet_definitions":
            for existing in self.sheet_definitions.values():
                if (
                    str(existing.get("owner_user_id")) == str(row.get("owner_user_id"))
                    and str(existing.get("code")) == str(row.get("code"))
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint sheet_definitions_owner_user_id_code_key")
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.sheet_definitions[str(row["id"])] = row
            return dict(row)

        if table == "app.sheet_revisions":
            for existing in self.sheet_revisions.values():
                if (
                    str(existing.get("sheet_definition_id")) == str(row.get("sheet_definition_id"))
                    and int(existing.get("revision_no") or 0) == int(row.get("revision_no") or 0)
                ):
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint sheet_revisions_sheet_definition_id_revision_no_key"
                    )
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.sheet_revisions[str(row["id"])] = row
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
        if table != "app.sheet_definitions":
            return []

        rows = list(self.sheet_definitions.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            current = self.sheet_definitions[str(row["id"])]
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



def _build_test_app(fake: FakeSupabaseClient) -> FastAPI:
    app = FastAPI()
    app.include_router(sheets_router, prefix="/v1")
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
    test_app = _build_test_app(fake)

    try:
        client = TestClient(test_app)

        create_new_resp = client.post(
            "/v1/sheets",
            json={
                "code": "SHEET-001",
                "name": "Main stock",
                "width_mm": 3000.0,
                "height_mm": 1500.0,
                "grain_direction": "Long",
                "notes": "first revision",
                "source_label": "manual_rect",
            },
        )
        if create_new_resp.status_code != 201:
            raise RuntimeError(f"new definition create failed: {create_new_resp.status_code} {create_new_resp.text}")
        new_payload = create_new_resp.json()

        if new_payload.get("revision_no") != 1:
            raise RuntimeError("new definition should start with revision_no=1")
        if new_payload.get("was_existing_definition"):
            raise RuntimeError("new definition branch should return was_existing_definition=false")
        if float(new_payload.get("width_mm")) != 3000.0:
            raise RuntimeError("width_mm mismatch for first revision")
        if float(new_payload.get("height_mm")) != 1500.0:
            raise RuntimeError("height_mm mismatch for first revision")
        if str(new_payload.get("grain_direction") or "") != "long":
            raise RuntimeError("grain_direction should be normalized to lowercase")

        def_id = str(new_payload.get("sheet_definition_id") or "")
        rev1_id = str(new_payload.get("sheet_revision_id") or "")
        definition_row = fake.sheet_definitions.get(def_id)
        revision_row = fake.sheet_revisions.get(rev1_id)
        if not definition_row or not revision_row:
            raise RuntimeError("missing sheet rows after first create")
        if str(definition_row.get("current_revision_id") or "") != rev1_id:
            raise RuntimeError("current_revision_id did not point to first revision")

        create_existing_resp = client.post(
            "/v1/sheets",
            json={
                "code": "SHEET-001",
                "name": "Main stock renamed should be ignored",
                "width_mm": 3200.0,
                "height_mm": 1600.0,
                "grain_direction": "  cross  ",
                "notes": "second revision",
                "source_label": "manual_rect",
            },
        )
        if create_existing_resp.status_code != 201:
            raise RuntimeError(
                f"existing definition create failed: {create_existing_resp.status_code} {create_existing_resp.text}"
            )
        existing_payload = create_existing_resp.json()

        if not existing_payload.get("was_existing_definition"):
            raise RuntimeError("existing definition branch should return was_existing_definition=true")
        if str(existing_payload.get("sheet_definition_id") or "") != def_id:
            raise RuntimeError("existing definition branch must reuse sheet_definition")
        if existing_payload.get("revision_no") != 2:
            raise RuntimeError("existing definition branch should allocate next revision_no=2")
        if str(existing_payload.get("grain_direction") or "") != "cross":
            raise RuntimeError("second grain_direction normalization mismatch")

        rev2_id = str(existing_payload.get("sheet_revision_id") or "")
        definition_row = fake.sheet_definitions.get(def_id)
        if not definition_row or str(definition_row.get("current_revision_id") or "") != rev2_id:
            raise RuntimeError("current_revision_id did not advance to second revision")

        if len(fake.sheet_definitions) != 1:
            raise RuntimeError("existing-definition branch should not create a new sheet_definition")
        if len(fake.sheet_revisions) != 2:
            raise RuntimeError("expected two sheet_revisions after second create")

        invalid_size_before_defs = len(fake.sheet_definitions)
        invalid_size_before_revs = len(fake.sheet_revisions)
        invalid_size_resp = client.post(
            "/v1/sheets",
            json={
                "code": "SHEET-002",
                "name": "Invalid size",
                "width_mm": 0,
                "height_mm": 1000.0,
            },
        )
        if invalid_size_resp.status_code != 422:
            raise RuntimeError(
                f"invalid size branch should fail with 422 (got {invalid_size_resp.status_code})"
            )
        if len(fake.sheet_definitions) != invalid_size_before_defs or len(fake.sheet_revisions) != invalid_size_before_revs:
            raise RuntimeError("invalid-size branch created sheet records unexpectedly")

        missing_request_before_defs = len(fake.sheet_definitions)
        missing_request_before_revs = len(fake.sheet_revisions)
        missing_request_resp = client.post(
            "/v1/sheets",
            json={
                "code": "SHEET-003",
                "name": "Missing height",
                "width_mm": 1200.0,
            },
        )
        if missing_request_resp.status_code != 422:
            raise RuntimeError(
                f"missing-request branch should fail with 422 (got {missing_request_resp.status_code})"
            )
        if len(fake.sheet_definitions) != missing_request_before_defs or len(fake.sheet_revisions) != missing_request_before_revs:
            raise RuntimeError("missing-request branch created sheet records unexpectedly")

        print("[PASS] H1-E3-T2 sheet creation service smoke passed")
        return 0
    finally:
        test_app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
