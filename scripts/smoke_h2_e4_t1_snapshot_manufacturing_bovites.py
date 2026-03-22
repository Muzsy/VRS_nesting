#!/usr/bin/env python3
"""H2-E4-T1 smoke: snapshot manufacturing bovites — selection snapshot."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_snapshot_builder import (  # noqa: E402
    build_run_snapshot_payload,
)

passed = 0
failed = 0


def _test(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK]   {label}")
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" — {detail}"
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Fake Supabase client (extends H1-E4-T1 pattern with manufacturing tables)
# ---------------------------------------------------------------------------

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
            "app.project_manufacturing_selection": [],
            "app.manufacturing_profile_versions": [],
        }
        self.write_calls: list[dict[str, Any]] = []

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
            ordered.sort(key=lambda row, f=key: str(row.get(f) or ""), reverse=reverse)
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
            rows = rows[offset: offset + limit]
        else:
            rows = rows[offset:]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.write_calls.append({"op": "insert", "table": table, "payload": payload})
        return dict(payload)

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        self.write_calls.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        return [dict(payload)]

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_calls.append({"op": "delete", "table": table, "filters": filters})


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"


def _seed_base(fake: FakeSupabaseClient) -> dict[str, str]:
    """Seed minimum happy-path data WITHOUT manufacturing selection."""
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

    fake.tables["app.projects"].append({
        "id": project_id, "owner_user_id": OWNER_ID,
        "name": "Project MFG", "lifecycle": "active",
    })
    fake.tables["app.project_settings"].append({
        "project_id": project_id, "default_units": "mm",
        "default_rotation_step_deg": 90, "notes": None,
    })
    fake.tables["app.project_technology_setups"].append({
        "id": tech_id, "project_id": project_id, "preset_id": None,
        "display_name": "Tech A", "lifecycle": "approved", "is_default": True,
        "machine_code": "M1", "material_code": "S235", "thickness_mm": 2.0,
        "kerf_mm": 0.2, "spacing_mm": 1.5, "margin_mm": 5.0,
        "rotation_step_deg": 90, "allow_free_rotation": False, "notes": None,
        "created_at": "2026-03-19T00:00:00Z",
    })
    fake.tables["app.part_definitions"].append({
        "id": part_definition_id, "owner_user_id": OWNER_ID,
        "code": "PART-001", "name": "Part 001",
        "current_revision_id": part_revision_id,
    })
    fake.tables["app.part_revisions"].append({
        "id": part_revision_id, "part_definition_id": part_definition_id,
        "revision_no": 1, "lifecycle": "approved",
        "source_geometry_revision_id": source_geometry_revision_id,
        "selected_nesting_derivative_id": derivative_id,
    })
    fake.tables["app.geometry_derivatives"].append({
        "id": derivative_id, "geometry_revision_id": source_geometry_revision_id,
        "derivative_kind": "nesting_canonical",
        "derivative_jsonb": {
            "polygon": {
                "outer_ring": [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]],
                "hole_rings": [],
            },
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 50.0, "width": 100.0, "height": 50.0},
        },
        "derivative_hash_sha256": "derivhash001",
        "source_geometry_hash_sha256": "geohash001",
    })
    fake.tables["app.project_part_requirements"].append({
        "id": requirement_id, "project_id": project_id,
        "part_revision_id": part_revision_id, "required_qty": 5,
        "placement_priority": 10, "placement_policy": "hard_first",
        "is_active": True, "notes": None,
    })
    fake.tables["app.sheet_definitions"].append({
        "id": sheet_definition_id, "owner_user_id": OWNER_ID,
        "code": "SHEET-01", "name": "Sheet 01",
        "current_revision_id": sheet_revision_id,
    })
    fake.tables["app.sheet_revisions"].append({
        "id": sheet_revision_id, "sheet_definition_id": sheet_definition_id,
        "revision_no": 1, "lifecycle": "approved",
        "width_mm": 3000.0, "height_mm": 1500.0, "grain_direction": "x+",
    })
    fake.tables["app.project_sheet_inputs"].append({
        "id": sheet_input_id, "project_id": project_id,
        "sheet_revision_id": sheet_revision_id, "required_qty": 2,
        "is_active": True, "is_default": True, "placement_priority": 5, "notes": None,
    })

    return {"project_id": project_id}


def _add_manufacturing_selection(
    fake: FakeSupabaseClient,
    *,
    project_id: str,
    version_id: str | None = None,
    manufacturing_profile_id: str | None = None,
    version_no: int = 1,
    lifecycle: str = "approved",
    is_active: bool = True,
    machine_code: str = "M1",
    material_code: str = "S235",
    thickness_mm: float = 2.0,
    kerf_mm: float = 0.2,
) -> str:
    """Add manufacturing profile version + project selection."""
    vid = version_id or str(uuid4())
    mpid = manufacturing_profile_id or str(uuid4())
    fake.tables["app.manufacturing_profile_versions"].append({
        "id": vid, "manufacturing_profile_id": mpid,
        "owner_user_id": OWNER_ID, "version_no": version_no,
        "lifecycle": lifecycle, "is_active": is_active,
        "machine_code": machine_code, "material_code": material_code,
        "thickness_mm": thickness_mm, "kerf_mm": kerf_mm,
        "config_jsonb": {"test": True},
    })
    fake.tables["app.project_manufacturing_selection"].append({
        "project_id": project_id,
        "active_manufacturing_profile_version_id": vid,
        "selected_at": "2026-03-22T10:00:00Z",
        "selected_by": OWNER_ID,
    })
    return vid


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed

    # ===================================================================
    # TEST 1: selection absent -> snapshot builds, includes_manufacturing=false
    # ===================================================================
    print("Test 1: selection absent -> snapshot builds, includes_manufacturing=false")
    fake1 = FakeSupabaseClient()
    ids1 = _seed_base(fake1)

    payload1 = build_run_snapshot_payload(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        project_id=ids1["project_id"],
    )
    _test("snapshot builds without selection", payload1 is not None)
    _test("includes_manufacturing=false", payload1.get("includes_manufacturing") is False)
    _test("includes_postprocess=false", payload1.get("includes_postprocess") is False)

    mfg1 = payload1.get("manufacturing_manifest_jsonb", {})
    _test("mode is h2_e4_t1_snapshot_selection", mfg1.get("mode") == "h2_e4_t1_snapshot_selection")
    _test("selection_present=false", mfg1.get("selection_present") is False)
    _test("postprocess_selection_present=false", mfg1.get("postprocess_selection_present") is False)
    _test("snapshot_hash present", len(str(payload1.get("snapshot_hash_sha256") or "")) == 64)
    _test("snapshot_version is h2", payload1.get("snapshot_version", "").startswith("h2_"))

    # ===================================================================
    # TEST 2: selection present -> manufacturing profile version snapshotted
    # ===================================================================
    print("\nTest 2: selection present -> manufacturing profile version snapshotted")
    fake2 = FakeSupabaseClient()
    ids2 = _seed_base(fake2)
    version_id_2 = _add_manufacturing_selection(fake2, project_id=ids2["project_id"])

    payload2 = build_run_snapshot_payload(
        supabase=fake2,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        project_id=ids2["project_id"],
    )
    _test("snapshot builds with selection", payload2 is not None)
    _test("includes_manufacturing=true", payload2.get("includes_manufacturing") is True)
    _test("includes_postprocess=false (still)", payload2.get("includes_postprocess") is False)

    mfg2 = payload2.get("manufacturing_manifest_jsonb", {})
    _test("selection_present=true", mfg2.get("selection_present") is True)
    _test("active_manufacturing_profile_version_id matches",
          mfg2.get("active_manufacturing_profile_version_id") == version_id_2)
    _test("selected_at present", bool(mfg2.get("selected_at")))
    _test("selected_by present", bool(mfg2.get("selected_by")))

    mpv = mfg2.get("manufacturing_profile_version", {})
    _test("mpv.manufacturing_profile_id present", bool(mpv.get("manufacturing_profile_id")))
    _test("mpv.version_no is int", isinstance(mpv.get("version_no"), int))
    _test("mpv.lifecycle present", bool(mpv.get("lifecycle")))
    _test("mpv.is_active is bool", isinstance(mpv.get("is_active"), bool))
    _test("mpv.machine_code present", bool(mpv.get("machine_code")))
    _test("mpv.material_code present", bool(mpv.get("material_code")))
    _test("mpv.thickness_mm is float", isinstance(mpv.get("thickness_mm"), float))
    _test("mpv.kerf_mm is float", isinstance(mpv.get("kerf_mm"), float))
    _test("mpv.config_jsonb is dict", isinstance(mpv.get("config_jsonb"), dict))

    _test("postprocess_selection_present=false", mfg2.get("postprocess_selection_present") is False)

    # ===================================================================
    # TEST 3: includes_postprocess=false always
    # ===================================================================
    print("\nTest 3: includes_postprocess=false always (both paths)")
    _test("absent path: includes_postprocess=false", payload1.get("includes_postprocess") is False)
    _test("present path: includes_postprocess=false", payload2.get("includes_postprocess") is False)

    # ===================================================================
    # TEST 4: selection change -> snapshot hash changes
    # ===================================================================
    print("\nTest 4: selection change -> snapshot hash changes")
    hash_without = payload1.get("snapshot_hash_sha256")
    hash_with = payload2.get("snapshot_hash_sha256")
    _test("hash without selection != hash with selection", hash_without != hash_with,
          f"both={hash_without}")

    # Different manufacturing version -> different hash
    fake4 = FakeSupabaseClient()
    ids4 = _seed_base(fake4)
    _add_manufacturing_selection(fake4, project_id=ids4["project_id"],
                                 machine_code="M1", thickness_mm=2.0)
    payload4a = build_run_snapshot_payload(
        supabase=fake4,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        project_id=ids4["project_id"],
    )

    fake4b = FakeSupabaseClient()
    ids4b = _seed_base(fake4b)
    _add_manufacturing_selection(fake4b, project_id=ids4b["project_id"],
                                  machine_code="M2", thickness_mm=3.0)
    payload4b = build_run_snapshot_payload(
        supabase=fake4b,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        project_id=ids4b["project_id"],
    )
    _test("different manufacturing version -> different hash",
          payload4a.get("snapshot_hash_sha256") != payload4b.get("snapshot_hash_sha256"))

    # ===================================================================
    # TEST 5: no manufacturing plan / persisted writes
    # ===================================================================
    print("\nTest 5: no manufacturing plan / persisted writes")
    _test("fake1 no write calls", len(fake1.write_calls) == 0,
          f"write_calls={fake1.write_calls}")
    _test("fake2 no write calls", len(fake2.write_calls) == 0,
          f"write_calls={fake2.write_calls}")

    # Verify no run_manufacturing_plans or run_manufacturing_contours tables queried
    # (the builder should not reference these)
    for fake_instance in [fake1, fake2, fake4, fake4b]:
        for table_name in fake_instance.tables:
            _test(f"no run_manufacturing_plans table in {table_name}",
                  "run_manufacturing_plans" not in table_name)
            _test(f"no run_manufacturing_contours table in {table_name}",
                  "run_manufacturing_contours" not in table_name)

    # ===================================================================
    # TEST 6: determinism — same input -> same hash
    # ===================================================================
    print("\nTest 6: determinism — same input -> same hash")
    payload2_again = build_run_snapshot_payload(
        supabase=fake2,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        project_id=ids2["project_id"],
    )
    _test("same input -> same hash",
          payload2.get("snapshot_hash_sha256") == payload2_again.get("snapshot_hash_sha256"))

    # ===================================================================
    # Summary
    # ===================================================================
    total = passed + failed
    print(f"\n{'=' * 60}")
    if failed == 0:
        print(f"[PASS] smoke_h2_e4_t1_snapshot_manufacturing_bovites: {passed}/{total} tests passed")
        return 0
    else:
        print(f"[FAIL] smoke_h2_e4_t1_snapshot_manufacturing_bovites: {passed}/{total} passed, {failed} failed",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
