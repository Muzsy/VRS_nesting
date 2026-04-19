#!/usr/bin/env python3
"""H2-E5-T2 smoke: postprocessor profile/version domain aktivalasa."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.postprocessor_profiles import (  # noqa: E402
    PostprocessorProfileError,
    create_postprocessor_profile,
    create_postprocessor_profile_version,
    delete_postprocessor_profile,
    delete_postprocessor_profile_version,
    get_postprocessor_profile,
    get_postprocessor_profile_version,
    list_postprocessor_profile_versions,
    list_postprocessor_profiles,
    update_postprocessor_profile,
    update_postprocessor_profile_version,
)
from api.services.run_snapshot_builder import (  # noqa: E402
    _build_manufacturing_manifest,
    _normalize_bool,
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
            msg += f" -- {detail}"
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.postprocessor_profiles": [],
            "app.postprocessor_profile_versions": [],
            "app.manufacturing_profiles": [],
            "app.manufacturing_profile_versions": [],
            "app.project_manufacturing_selection": [],
            "app.profiles": [],
            "app.projects": [],
        }
        self.write_log: list[dict[str, Any]] = []

    @staticmethod
    def _match_filter(value: Any, raw_filter: str) -> bool:
        normalized = raw_filter.strip()
        text = "" if value is None else str(value)
        if normalized.startswith("eq."):
            token = normalized[3:]
            low = token.lower()
            if low == "true":
                return bool(value) is True
            if low == "false":
                return bool(value) is False
            return text == token
        if normalized.startswith("neq."):
            return text != normalized[4:]
        if normalized.startswith("gt."):
            try:
                return float(text) > float(normalized[3:])
            except (TypeError, ValueError):
                return False
        return True

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
            for token in reversed([p.strip() for p in order_clause.split(",") if p.strip()]):
                col = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda r, c=col: str(r.get(c) or ""), reverse=reverse)

        limit_raw = params.get("limit", "")
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload)
        if "id" not in row:
            row["id"] = str(uuid4())
        self.tables.setdefault(table, []).append(row)
        self.write_log.append({"op": "insert", "table": table, "payload": row})
        return row

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        meta_keys = {"select", "order", "limit", "offset"}
        updated: list[dict[str, Any]] = []
        for row in self.tables.get(table, []):
            match = True
            for key, raw_filter in filters.items():
                if key in meta_keys:
                    continue
                if not self._match_filter(row.get(key), raw_filter):
                    match = False
                    break
            if match:
                row.update(payload)
                updated.append(dict(row))
        self.write_log.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_log.append({"op": "delete", "table": table, "filters": filters})
        meta_keys = {"select", "order", "limit", "offset"}
        rows = self.tables.get(table, [])
        remaining = []
        for row in rows:
            keep = False
            for key, raw_filter in filters.items():
                if key in meta_keys:
                    continue
                if not self._match_filter(row.get(key), raw_filter):
                    keep = True
                    break
            if keep:
                remaining.append(row)
        self.tables[table] = remaining


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OWNER_A = str(uuid4())
OWNER_B = str(uuid4())
TOKEN = "fake-token"


# ===========================================================================
# 1. Profile CRUD
# ===========================================================================

def test_profile_crud() -> None:
    print("\n=== 1. Postprocessor profile CRUD ===")
    sb = FakeSupabaseClient()

    profile = create_postprocessor_profile(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        profile_code="PP-LASER-01",
        display_name="Laser postprocessor",
        adapter_key="laser_generic",
    )
    _test("profile created", profile.get("profile_code") == "PP-LASER-01")
    _test("owner correct", profile.get("owner_user_id") == OWNER_A)
    _test("adapter_key set", profile.get("adapter_key") == "laser_generic")

    profiles = list_postprocessor_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
    )
    _test("list returns 1", len(profiles) == 1)

    got = get_postprocessor_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
    )
    _test("get returns correct", got["id"] == profile["id"])

    updated = update_postprocessor_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
        updates={"display_name": "Updated laser"},
    )
    _test("update works", updated.get("display_name") == "Updated laser")

    deleted = delete_postprocessor_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
    )
    _test("delete returns row", deleted["id"] == profile["id"])

    remaining = list_postprocessor_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
    )
    _test("list empty after delete", len(remaining) == 0)


# ===========================================================================
# 2. Version CRUD under profile
# ===========================================================================

def test_version_crud() -> None:
    print("\n=== 2. Postprocessor version CRUD ===")
    sb = FakeSupabaseClient()

    profile = create_postprocessor_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_code="PP-01", display_name="Test",
    )
    pid = str(profile["id"])

    v1 = create_postprocessor_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid,
        adapter_key="generic", output_format="gcode", schema_version="v1",
    )
    _test("version created", v1.get("version_no") == 1)
    _test("output_format", v1.get("output_format") == "gcode")

    v2 = create_postprocessor_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid,
        adapter_key="generic", output_format="json", schema_version="v2",
    )
    _test("version_no auto-increment", v2.get("version_no") == 2)

    versions = list_postprocessor_profile_versions(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid,
    )
    _test("list returns 2", len(versions) == 2)

    got = get_postprocessor_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid, version_id=str(v1["id"]),
    )
    _test("get version correct", got["id"] == v1["id"])

    updated = update_postprocessor_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid, version_id=str(v1["id"]),
        updates={"output_format": "nc"},
    )
    _test("version update works", updated.get("output_format") == "nc")

    delete_postprocessor_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid, version_id=str(v2["id"]),
    )
    remaining = list_postprocessor_profile_versions(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid,
    )
    _test("version deleted", len(remaining) == 1)


# ===========================================================================
# 3. Owner boundary: foreign owner cannot access
# ===========================================================================

def test_owner_boundary() -> None:
    print("\n=== 3. Owner boundary ===")
    sb = FakeSupabaseClient()

    profile = create_postprocessor_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_code="PP-OWNER", display_name="Owner A profile",
    )
    pid = str(profile["id"])

    # Owner B cannot get Owner A's profile
    try:
        get_postprocessor_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid,
        )
        _test("foreign owner get rejected", False, detail="should have raised")
    except PostprocessorProfileError as exc:
        _test("foreign owner get rejected", exc.status_code == 404)

    # Owner B cannot update Owner A's profile
    try:
        update_postprocessor_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid, updates={"display_name": "hacked"},
        )
        _test("foreign owner update rejected", False, detail="should have raised")
    except PostprocessorProfileError as exc:
        _test("foreign owner update rejected", exc.status_code == 404)

    # Owner B cannot delete Owner A's profile
    try:
        delete_postprocessor_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid,
        )
        _test("foreign owner delete rejected", False, detail="should have raised")
    except PostprocessorProfileError as exc:
        _test("foreign owner delete rejected", exc.status_code == 404)

    # Version under foreign profile
    v1 = create_postprocessor_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        postprocessor_profile_id=pid,
    )
    try:
        get_postprocessor_profile_version(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            postprocessor_profile_id=pid, version_id=str(v1["id"]),
        )
        _test("foreign owner version get rejected", False, detail="should have raised")
    except PostprocessorProfileError as exc:
        _test("foreign owner version get rejected", exc.status_code == 404)


# ===========================================================================
# 4. Snapshot builder: no postprocessor ref -> false
# ===========================================================================

def test_snapshot_no_postprocess_ref() -> None:
    print("\n=== 4. Snapshot: no postprocessor ref ===")
    sb = FakeSupabaseClient()
    project_id = str(uuid4())

    # No manufacturing selection at all
    manifest, has_mfg = _build_manufacturing_manifest(
        supabase=sb, access_token=TOKEN, project_id=project_id,
    )
    _test("no selection -> selection_present=False", manifest.get("selection_present") is False)
    _test("no selection -> postprocess_selection_present=False", manifest.get("postprocess_selection_present") is False)
    _test("no selection -> includes_manufacturing=False", has_mfg is False)


# ===========================================================================
# 5. Snapshot builder: active postprocessor ref -> true
# ===========================================================================

def test_snapshot_with_postprocess_ref() -> None:
    print("\n=== 5. Snapshot: active postprocessor ref ===")
    sb = FakeSupabaseClient()
    project_id = str(uuid4())
    mpv_id = str(uuid4())
    ppv_id = str(uuid4())

    # Set up manufacturing selection
    sb.tables["app.project_manufacturing_selection"].append({
        "project_id": project_id,
        "active_manufacturing_profile_version_id": mpv_id,
        "selected_at": "2026-03-22T00:00:00Z",
        "selected_by": OWNER_A,
    })
    sb.tables["app.manufacturing_profile_versions"].append({
        "id": mpv_id,
        "manufacturing_profile_id": str(uuid4()),
        "version_no": 1,
        "lifecycle": "approved",
        "is_active": True,
        "machine_code": "LASER-01",
        "material_code": "STEEL-1MM",
        "thickness_mm": 1.0,
        "kerf_mm": 0.1,
        "config_jsonb": {},
        "active_postprocessor_profile_version_id": ppv_id,
    })
    sb.tables["app.postprocessor_profile_versions"].append({
        "id": ppv_id,
        "postprocessor_profile_id": str(uuid4()),
        "owner_user_id": OWNER_A,
        "version_no": 1,
        "lifecycle": "approved",
        "is_active": True,
        "adapter_key": "laser_generic",
        "output_format": "gcode",
        "schema_version": "v1",
        "config_jsonb": {},
    })

    manifest, has_mfg = _build_manufacturing_manifest(
        supabase=sb, access_token=TOKEN, project_id=project_id,
    )
    _test("selection_present=True", manifest.get("selection_present") is True)
    _test("postprocess_selection_present=True", manifest.get("postprocess_selection_present") is True)
    _test("includes_manufacturing=True", has_mfg is True)
    _test("postprocessor_profile_version present", "postprocessor_profile_version" in manifest)

    ppv_snap = manifest.get("postprocessor_profile_version", {})
    _test("ppv adapter_key snapshotted", ppv_snap.get("adapter_key") == "laser_generic")
    _test("ppv output_format snapshotted", ppv_snap.get("output_format") == "gcode")
    _test("ppv schema_version snapshotted", ppv_snap.get("schema_version") == "v1")
    _test("ppv active_postprocessor_profile_version_id snapshotted", ppv_snap.get("active_postprocessor_profile_version_id") == ppv_id)


# ===========================================================================
# 6. Snapshot builder: inactive postprocessor ref -> false
# ===========================================================================

def test_snapshot_inactive_postprocess_ref() -> None:
    print("\n=== 6. Snapshot: inactive postprocessor ref ===")
    sb = FakeSupabaseClient()
    project_id = str(uuid4())
    mpv_id = str(uuid4())
    ppv_id = str(uuid4())

    sb.tables["app.project_manufacturing_selection"].append({
        "project_id": project_id,
        "active_manufacturing_profile_version_id": mpv_id,
        "selected_at": "2026-03-22T00:00:00Z",
        "selected_by": OWNER_A,
    })
    sb.tables["app.manufacturing_profile_versions"].append({
        "id": mpv_id,
        "manufacturing_profile_id": str(uuid4()),
        "version_no": 1,
        "lifecycle": "approved",
        "is_active": True,
        "machine_code": "LASER-01",
        "material_code": "STEEL",
        "thickness_mm": 1.0,
        "kerf_mm": 0.1,
        "config_jsonb": {},
        "active_postprocessor_profile_version_id": ppv_id,
    })
    sb.tables["app.postprocessor_profile_versions"].append({
        "id": ppv_id,
        "postprocessor_profile_id": str(uuid4()),
        "owner_user_id": OWNER_A,
        "version_no": 1,
        "lifecycle": "draft",
        "is_active": False,  # inactive!
        "adapter_key": "generic",
        "output_format": "json",
        "schema_version": "v1",
        "config_jsonb": {},
    })

    manifest, _ = _build_manufacturing_manifest(
        supabase=sb, access_token=TOKEN, project_id=project_id,
    )
    _test("inactive ppv -> postprocess_selection_present=False", manifest.get("postprocess_selection_present") is False)
    _test("inactive ppv -> no postprocessor_profile_version key", "postprocessor_profile_version" not in manifest)


# ===========================================================================
# 7. No export / adapter / machine-ready scope
# ===========================================================================

def test_no_export_scope() -> None:
    print("\n=== 7. No export / adapter / machine-ready scope ===")
    import api.services.postprocessor_profiles as pp_mod
    source = Path(pp_mod.__file__).read_text()
    _test("no machine_ready in service", "machine_ready" not in source)
    _test("no export_bundle in service", "export_bundle" not in source)
    _test("no adapter_run in service", "adapter_run" not in source.lower())

    import api.routes.postprocessor_profiles as pp_route
    route_source = Path(pp_route.__file__).read_text()
    _test("no machine_ready in route", "machine_ready" not in route_source)
    _test("no export_bundle in route", "export_bundle" not in route_source)


# ===========================================================================
# 8. No catalog-FK world
# ===========================================================================

def test_no_catalog_fk() -> None:
    print("\n=== 8. No catalog-FK world ===")
    migration_path = ROOT / "supabase" / "migrations" / "20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql"
    sql = migration_path.read_text()
    _test("no machine_catalog FK", "machine_catalog" not in sql)
    _test("no material_catalog FK", "material_catalog" not in sql)

    import api.services.postprocessor_profiles as pp_mod
    source = Path(pp_mod.__file__).read_text()
    _test("no machine_catalog in service", "machine_catalog" not in source)
    _test("no material_catalog in service", "material_catalog" not in source)


# ===========================================================================
# 9. Mode tag consistency
# ===========================================================================

def test_mode_tag() -> None:
    print("\n=== 9. Snapshot mode tag ===")
    sb = FakeSupabaseClient()
    project_id = str(uuid4())

    manifest, _ = _build_manufacturing_manifest(
        supabase=sb, access_token=TOKEN, project_id=project_id,
    )
    _test("mode tag is h2_e5_t2", manifest.get("mode") == "h2_e5_t2_snapshot_selection")


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    print("H2-E5-T2 smoke: postprocessor profile/version domain aktivalasa\n")

    test_profile_crud()
    test_version_crud()
    test_owner_boundary()
    test_snapshot_no_postprocess_ref()
    test_snapshot_with_postprocess_ref()
    test_snapshot_inactive_postprocess_ref()
    test_no_export_scope()
    test_no_catalog_fk()
    test_mode_tag()

    total = passed + failed
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        sys.exit(1)
    else:
        print("SMOKE PASS")
        sys.exit(0)
