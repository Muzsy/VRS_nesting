#!/usr/bin/env python3
"""H1-E4-T1 smoke: run snapshot builder (H1 minimum)."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_snapshot_builder import (  # noqa: E402
    RunSnapshotBuilderError,
    build_run_snapshot_payload,
)


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.projects": [],
            "app.project_settings": [],
            "app.project_technology_setups": [],
            "app.project_part_requirements": [],
            "app.part_revisions": [],
            "app.part_definitions": [],
            "app.project_sheet_inputs": [],
            "app.sheet_revisions": [],
            "app.sheet_definitions": [],
            "app.geometry_derivatives": [],
        }
        self._query_counter: dict[str, int] = {}

    @staticmethod
    def _match_filter(value: Any, raw_filter: str) -> bool:
        normalized = raw_filter.strip()
        text = "" if value is None else str(value)

        def _as_bool_token(token: str) -> bool | None:
            lowered = token.lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            return None

        if normalized.startswith("eq."):
            token = normalized[3:]
            token_bool = _as_bool_token(token)
            if token_bool is not None:
                return bool(value) is token_bool
            return text == token
        if normalized.startswith("neq."):
            token = normalized[4:]
            token_bool = _as_bool_token(token)
            if token_bool is not None:
                return bool(value) is not token_bool
            return text != token
        if normalized.startswith("gt."):
            try:
                return float(value) > float(normalized[3:])
            except (TypeError, ValueError):
                return False
        if normalized.startswith("lt."):
            try:
                return float(value) < float(normalized[3:])
            except (TypeError, ValueError):
                return False
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
        rows = [dict(item) for item in self.tables.get(table, [])]

        # Intentionally alternate order for these two tables to prove hash determinism.
        if table in {"app.project_part_requirements", "app.project_sheet_inputs"}:
            count = self._query_counter.get(table, 0)
            self._query_counter[table] = count + 1
            if count % 2 == 1:
                rows = list(reversed(rows))

        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._match_filter(row.get(key), raw_filter)]

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
        return rows


def _seed_happy_path(fake: FakeSupabaseClient) -> dict[str, str]:
    owner_id = "00000000-0000-0000-0000-000000000001"
    project_id = str(uuid4())
    tech_id = str(uuid4())

    part_definition_id = str(uuid4())
    part_revision_id = str(uuid4())
    derivative_id = str(uuid4())
    source_geometry_revision_id = str(uuid4())
    requirement_id = str(uuid4())

    sheet_definition_id = str(uuid4())
    sheet_revision_id = str(uuid4())
    sheet_input_id = str(uuid4())

    fake.tables["app.projects"].append(
        {
            "id": project_id,
            "owner_user_id": owner_id,
            "name": "Project A",
            "lifecycle": "active",
        }
    )
    fake.tables["app.project_settings"].append(
        {
            "project_id": project_id,
            "default_units": "mm",
            "default_rotation_step_deg": 90,
            "notes": "settings",
        }
    )
    fake.tables["app.project_technology_setups"].append(
        {
            "id": tech_id,
            "project_id": project_id,
            "preset_id": None,
            "display_name": "Tech A",
            "lifecycle": "approved",
            "is_default": True,
            "machine_code": "M1",
            "material_code": "S235",
            "thickness_mm": 2.0,
            "kerf_mm": 0.2,
            "spacing_mm": 1.5,
            "margin_mm": 5.0,
            "rotation_step_deg": 90,
            "allow_free_rotation": False,
            "notes": None,
            "created_at": "2026-03-19T00:00:00Z",
        }
    )

    fake.tables["app.part_definitions"].append(
        {
            "id": part_definition_id,
            "owner_user_id": owner_id,
            "code": "PART-001",
            "name": "Part 001",
            "current_revision_id": part_revision_id,
        }
    )
    fake.tables["app.part_revisions"].append(
        {
            "id": part_revision_id,
            "part_definition_id": part_definition_id,
            "revision_no": 2,
            "lifecycle": "approved",
            "source_geometry_revision_id": source_geometry_revision_id,
            "selected_nesting_derivative_id": derivative_id,
        }
    )
    fake.tables["app.geometry_derivatives"].append(
        {
            "id": derivative_id,
            "geometry_revision_id": source_geometry_revision_id,
            "derivative_kind": "nesting_canonical",
            "derivative_hash_sha256": "derivhash",
            "source_geometry_hash_sha256": "geohash",
        }
    )
    fake.tables["app.project_part_requirements"].append(
        {
            "id": requirement_id,
            "project_id": project_id,
            "part_revision_id": part_revision_id,
            "required_qty": 7,
            "placement_priority": 10,
            "placement_policy": "hard_first",
            "is_active": True,
            "notes": "req",
        }
    )

    fake.tables["app.sheet_definitions"].append(
        {
            "id": sheet_definition_id,
            "owner_user_id": owner_id,
            "code": "SHEET-01",
            "name": "Sheet 01",
            "current_revision_id": sheet_revision_id,
        }
    )
    fake.tables["app.sheet_revisions"].append(
        {
            "id": sheet_revision_id,
            "sheet_definition_id": sheet_definition_id,
            "revision_no": 1,
            "lifecycle": "approved",
            "width_mm": 3000.0,
            "height_mm": 1500.0,
            "grain_direction": "x+",
        }
    )
    fake.tables["app.project_sheet_inputs"].append(
        {
            "id": sheet_input_id,
            "project_id": project_id,
            "sheet_revision_id": sheet_revision_id,
            "required_qty": 3,
            "is_active": True,
            "is_default": True,
            "placement_priority": 5,
            "notes": "sheet",
        }
    )

    return {
        "owner_id": owner_id,
        "project_id": project_id,
        "part_revision_id": part_revision_id,
        "sheet_revision_id": sheet_revision_id,
    }


def _expect_error(fn: Any, *, status_code: int, detail_contains: str) -> None:
    try:
        fn()
    except RunSnapshotBuilderError as exc:
        if exc.status_code != status_code:
            raise RuntimeError(f"unexpected status code: {exc.status_code} != {status_code}")
        if detail_contains not in exc.detail:
            raise RuntimeError(f"unexpected error detail: {exc.detail!r}")
        return
    raise RuntimeError("expected RunSnapshotBuilderError")


def main() -> int:
    fake = FakeSupabaseClient()
    seeded = _seed_happy_path(fake)

    ok_payload = build_run_snapshot_payload(
        supabase=fake,
        access_token="token-u1",
        owner_user_id=seeded["owner_id"],
        project_id=seeded["project_id"],
    )
    required_keys = {
        "snapshot_version",
        "project_manifest_jsonb",
        "technology_manifest_jsonb",
        "parts_manifest_jsonb",
        "sheets_manifest_jsonb",
        "geometry_manifest_jsonb",
        "solver_config_jsonb",
        "manufacturing_manifest_jsonb",
        "snapshot_hash_sha256",
    }
    missing = required_keys - set(ok_payload.keys())
    if missing:
        raise RuntimeError(f"missing snapshot keys: {sorted(missing)}")
    if len(str(ok_payload.get("snapshot_hash_sha256") or "")) != 64:
        raise RuntimeError("snapshot hash is missing or invalid")

    second_payload = build_run_snapshot_payload(
        supabase=fake,
        access_token="token-u1",
        owner_user_id=seeded["owner_id"],
        project_id=seeded["project_id"],
    )
    if ok_payload.get("snapshot_hash_sha256") != second_payload.get("snapshot_hash_sha256"):
        raise RuntimeError("snapshot hash is not deterministic for identical input")

    no_tech = FakeSupabaseClient()
    no_tech_seeded = _seed_happy_path(no_tech)
    no_tech.tables["app.project_technology_setups"] = []
    _expect_error(
        lambda: build_run_snapshot_payload(
            supabase=no_tech,
            access_token="token-u1",
            owner_user_id=no_tech_seeded["owner_id"],
            project_id=no_tech_seeded["project_id"],
        ),
        status_code=400,
        detail_contains="missing approved project technology setup",
    )

    no_requirements = FakeSupabaseClient()
    no_requirements_seeded = _seed_happy_path(no_requirements)
    for row in no_requirements.tables["app.project_part_requirements"]:
        row["is_active"] = False
    _expect_error(
        lambda: build_run_snapshot_payload(
            supabase=no_requirements,
            access_token="token-u1",
            owner_user_id=no_requirements_seeded["owner_id"],
            project_id=no_requirements_seeded["project_id"],
        ),
        status_code=400,
        detail_contains="missing active project part requirements",
    )

    no_sheet_inputs = FakeSupabaseClient()
    no_sheet_inputs_seeded = _seed_happy_path(no_sheet_inputs)
    for row in no_sheet_inputs.tables["app.project_sheet_inputs"]:
        row["is_active"] = False
    _expect_error(
        lambda: build_run_snapshot_payload(
            supabase=no_sheet_inputs,
            access_token="token-u1",
            owner_user_id=no_sheet_inputs_seeded["owner_id"],
            project_id=no_sheet_inputs_seeded["project_id"],
        ),
        status_code=400,
        detail_contains="missing active project sheet inputs",
    )

    part_not_approved = FakeSupabaseClient()
    part_not_approved_seeded = _seed_happy_path(part_not_approved)
    part_not_approved.tables["app.part_revisions"][0]["lifecycle"] = "draft"
    _expect_error(
        lambda: build_run_snapshot_payload(
            supabase=part_not_approved,
            access_token="token-u1",
            owner_user_id=part_not_approved_seeded["owner_id"],
            project_id=part_not_approved_seeded["project_id"],
        ),
        status_code=400,
        detail_contains="part revision is not approved",
    )

    part_without_derivative = FakeSupabaseClient()
    part_without_derivative_seeded = _seed_happy_path(part_without_derivative)
    part_without_derivative.tables["app.part_revisions"][0]["selected_nesting_derivative_id"] = None
    part_without_derivative.tables["app.part_revisions"][0]["source_geometry_revision_id"] = None
    _expect_error(
        lambda: build_run_snapshot_payload(
            supabase=part_without_derivative,
            access_token="token-u1",
            owner_user_id=part_without_derivative_seeded["owner_id"],
            project_id=part_without_derivative_seeded["project_id"],
        ),
        status_code=400,
        detail_contains="invalid selected_nesting_derivative_id",
    )

    print("[PASS] H1-E4-T1 run snapshot builder smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
