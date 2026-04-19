#!/usr/bin/env python3
"""H2-E5-T3 smoke: machine-neutral exporter — manufacturing_plan_json artifact."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.machine_neutral_exporter import (  # noqa: E402
    generate_machine_neutral_export,
    MachineNeutralExporterError,
    EXPORT_CONTRACT_VERSION,
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
# Fake Supabase client
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.nesting_runs": [],
            "app.nesting_run_snapshots": [],
            "app.run_manufacturing_plans": [],
            "app.run_manufacturing_contours": [],
            "app.run_manufacturing_metrics": [],
            "app.run_layout_sheets": [],
            "app.run_artifacts": [],
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
        if "id" not in row and "run_id" not in row:
            row["id"] = str(uuid4())
        self.tables.setdefault(table, []).append(row)
        self.write_log.append({"op": "insert", "table": table, "payload": row})
        return row

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        self.write_log.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        return [dict(payload)]

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_log.append({"op": "delete", "table": table, "filters": filters})
        rows = self.tables.get(table, [])
        meta_keys = {"select", "order", "limit", "offset"}
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
# Upload/register fakes
# ---------------------------------------------------------------------------

_uploaded: list[dict[str, Any]] = []
_registered: list[dict[str, Any]] = []


def _fake_upload(**kwargs: Any) -> None:
    _uploaded.append(kwargs)


def _fake_register(**kwargs: Any) -> None:
    _registered.append(kwargs)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"
PROJECT_ID = "00000000-0000-0000-0000-000000000002"
MFG_PROFILE_VERSION_ID = "00000000-0000-0000-0000-000000000003"
PP_VERSION_ID = "00000000-0000-0000-0000-000000000004"


def _seed_full(
    fake: FakeSupabaseClient,
    *,
    with_postprocessor: bool = False,
    with_metrics: bool = True,
) -> dict[str, str]:
    """Seed a complete happy-path scenario with persisted manufacturing plan."""
    run_id = str(uuid4())
    plan_id = str(uuid4())
    sheet_id = str(uuid4())

    # Run
    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })

    # Sheet
    fake.tables["app.run_layout_sheets"].append({
        "id": sheet_id,
        "run_id": run_id,
        "sheet_index": 0,
    })

    # Manufacturing manifest in snapshot
    mfg_manifest: dict[str, Any] = {
        "mode": "h2_e5_t2_snapshot_selection",
        "project_id": PROJECT_ID,
        "selection_present": True,
        "active_manufacturing_profile_version_id": MFG_PROFILE_VERSION_ID,
        "postprocess_selection_present": with_postprocessor,
    }
    if with_postprocessor:
        mfg_manifest["postprocessor_profile_version"] = {
            "active_postprocessor_profile_version_id": PP_VERSION_ID,
            "adapter_key": "generic",
            "output_format": "json",
            "schema_version": "v1",
        }

    fake.tables["app.nesting_run_snapshots"].append({
        "id": str(uuid4()),
        "run_id": run_id,
        "manufacturing_manifest_jsonb": mfg_manifest,
        "includes_manufacturing": True,
    })

    # Persisted manufacturing plan
    fake.tables["app.run_manufacturing_plans"].append({
        "id": plan_id,
        "run_id": run_id,
        "sheet_id": sheet_id,
        "manufacturing_profile_version_id": MFG_PROFILE_VERSION_ID,
        "cut_rule_set_id": str(uuid4()),
        "status": "generated",
        "summary_jsonb": {"builder_scope": "h2_e4_t2", "placement_count": 1},
    })

    # Manufacturing contours
    fake.tables["app.run_manufacturing_contours"].extend([
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "contour_index": 0,
            "contour_kind": "outer",
            "feature_class": "default",
            "entry_point_jsonb": {"x": 10.0, "y": 10.0, "rotation_deg": 0.0, "source": "placement_transform"},
            "lead_in_jsonb": {"type": "line", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "line", "source": "matched_rule"},
            "cut_order_index": 0,
        },
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "contour_index": 1,
            "contour_kind": "inner",
            "feature_class": "default",
            "entry_point_jsonb": {"x": 30.0, "y": 30.0, "rotation_deg": 0.0, "source": "placement_transform"},
            "lead_in_jsonb": {"type": "arc", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "none", "source": "matched_rule"},
            "cut_order_index": 1,
        },
    ])

    # Optional metrics
    if with_metrics:
        fake.tables["app.run_manufacturing_metrics"].append({
            "run_id": run_id,
            "pierce_count": 2,
            "outer_contour_count": 1,
            "inner_contour_count": 1,
            "estimated_cut_length_mm": 320.0,
            "estimated_rapid_length_mm": 28.2843,
            "estimated_process_time_s": 7.5414,
            "metrics_jsonb": {"calculator_scope": "h2_e4_t3"},
        })

    return {
        "run_id": run_id,
        "plan_id": plan_id,
        "sheet_id": sheet_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed, _uploaded, _registered

    # ===================================================================
    # TEST 1: valid plan -> export artifact created
    # ===================================================================
    print("Test 1: valid persisted plan -> manufacturing_plan_json artifact created")
    fake1 = FakeSupabaseClient()
    ids1 = _seed_full(fake1, with_postprocessor=True)
    _uploaded = []
    _registered = []

    result1 = generate_machine_neutral_export(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
        upload_object=_fake_upload,
        register_artifact=_fake_register,
    )
    _test("result is dict", isinstance(result1, dict))
    _test("run_id correct", result1.get("run_id") == ids1["run_id"])
    _test("project_id correct", result1.get("project_id") == PROJECT_ID)
    _test("filename is out/manufacturing_plan.json", result1.get("filename") == "out/manufacturing_plan.json")
    _test("storage_path has manufacturing_plan_json", "manufacturing_plan_json/" in (result1.get("storage_path") or ""))
    _test("content_sha256 present", bool(result1.get("content_sha256")))
    _test("size_bytes > 0", (result1.get("size_bytes") or 0) > 0)
    _test("export_contract_version correct", result1.get("export_contract_version") == EXPORT_CONTRACT_VERSION)
    _test("1 upload", len(_uploaded) == 1)
    _test("1 register", len(_registered) == 1)

    # ===================================================================
    # TEST 2: payload is deterministic
    # ===================================================================
    print("\nTest 2: payload is deterministic (same truth -> same bytes)")
    _uploaded_2: list[dict[str, Any]] = []
    _registered_2: list[dict[str, Any]] = []

    result2 = generate_machine_neutral_export(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
        upload_object=lambda **kw: _uploaded_2.append(kw),
        register_artifact=lambda **kw: _registered_2.append(kw),
    )
    _test("content_sha256 matches first run", result2.get("content_sha256") == result1.get("content_sha256"))
    _test("size_bytes matches", result2.get("size_bytes") == result1.get("size_bytes"))

    # Verify actual byte-level equality
    payload1 = _uploaded[0].get("payload", b"")
    payload2 = _uploaded_2[0].get("payload", b"")
    _test("byte-level identical", payload1 == payload2)

    # ===================================================================
    # TEST 3: active postprocessor selection metadata included
    # ===================================================================
    print("\nTest 3: postprocessor selection metadata present, no machine-ready emit")
    payload_json = json.loads(payload1) if isinstance(payload1, bytes) else {}
    _test("payload has postprocessor_selection", "postprocessor_selection" in payload_json)
    pp_sel = payload_json.get("postprocessor_selection") or {}
    _test("pp has active_postprocessor_profile_version_id", pp_sel.get("active_postprocessor_profile_version_id") == PP_VERSION_ID)
    _test("pp has adapter_key", pp_sel.get("adapter_key") == "generic")
    _test("pp has output_format", pp_sel.get("output_format") == "json")
    _test("pp has schema_version", pp_sel.get("schema_version") == "v1")

    # Verify no machine-specific fields
    payload_text = payload1.decode("utf-8") if isinstance(payload1, bytes) else ""
    _test("no machine_ready_bundle in payload", "machine_ready_bundle" not in payload_text)
    _test("no gcode in payload", "gcode" not in payload_text.lower())
    _test("no machine_log in payload", "machine_log" not in payload_text)

    # ===================================================================
    # TEST 4: export works without postprocessor ref
    # ===================================================================
    print("\nTest 4: export without postprocessor ref")
    fake4 = FakeSupabaseClient()
    ids4 = _seed_full(fake4, with_postprocessor=False)
    _uploaded_4: list[dict[str, Any]] = []
    _registered_4: list[dict[str, Any]] = []

    result4 = generate_machine_neutral_export(
        supabase=fake4,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids4["run_id"],
        upload_object=lambda **kw: _uploaded_4.append(kw),
        register_artifact=lambda **kw: _registered_4.append(kw),
    )
    _test("export succeeds without postprocessor", isinstance(result4, dict))
    _test("content_sha256 present", bool(result4.get("content_sha256")))

    payload4_bytes = _uploaded_4[0].get("payload", b"") if _uploaded_4 else b""
    payload4_json = json.loads(payload4_bytes) if payload4_bytes else {}
    _test("no postprocessor_selection key", "postprocessor_selection" not in payload4_json)

    # ===================================================================
    # TEST 5: rerun is idempotent (no duplicates)
    # ===================================================================
    print("\nTest 5: idempotent rerun")
    _uploaded_5: list[dict[str, Any]] = []
    _registered_5: list[dict[str, Any]] = []

    result5 = generate_machine_neutral_export(
        supabase=fake4,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids4["run_id"],
        upload_object=lambda **kw: _uploaded_5.append(kw),
        register_artifact=lambda **kw: _registered_5.append(kw),
    )
    _test("rerun succeeds", isinstance(result5, dict))
    _test("sha256 matches first", result5.get("content_sha256") == result4.get("content_sha256"))

    # Check that delete happened before insert
    delete_ops = [w for w in fake4.write_log if w.get("op") == "delete" and w.get("table") == "app.run_artifacts"]
    _test("idempotent delete happened", len(delete_ops) >= 2,
          f"got {len(delete_ops)} delete ops")

    # ===================================================================
    # TEST 6: service does not write to earlier truth tables
    # ===================================================================
    print("\nTest 6: no write to earlier truth tables")
    forbidden_tables = {
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.run_manufacturing_metrics",
        "app.geometry_contour_classes",
        "app.project_manufacturing_selection",
        "app.postprocessor_profile_versions",
    }
    violated = set()
    for w in fake1.write_log:
        tbl = w.get("table", "")
        if tbl in forbidden_tables:
            violated.add(tbl)
    for w in fake4.write_log:
        tbl = w.get("table", "")
        if tbl in forbidden_tables:
            violated.add(tbl)
    _test("no write to forbidden truth tables", len(violated) == 0,
          f"violated: {violated}")

    # ===================================================================
    # TEST 7: no machine_ready_bundle / machine_log / G-code / adapter-run
    # ===================================================================
    print("\nTest 7: no machine-specific side effects")
    for reg in list(_registered) + list(_registered_4) + list(_registered_5):
        ak = str(reg.get("artifact_kind") or "")
        _test(f"artifact_kind is manufacturing_plan_json (got {ak})",
              ak == "manufacturing_plan_json")

    # Check no forbidden artifact kinds in any write log
    all_write_logs = fake1.write_log + fake4.write_log
    forbidden_artifact_kinds = {"machine_ready_bundle", "machine_log", "gcode", "adapter_run"}
    found_forbidden = set()
    for w in all_write_logs:
        if w.get("op") == "insert" and w.get("table") == "app.run_artifacts":
            ak = str(w.get("payload", {}).get("artifact_kind") or "")
            if ak in forbidden_artifact_kinds:
                found_forbidden.add(ak)
    _test("no forbidden artifact kinds", len(found_forbidden) == 0,
          f"found: {found_forbidden}")

    # ===================================================================
    # TEST 8: error on missing manufacturing plan
    # ===================================================================
    print("\nTest 8: error on missing manufacturing plan")
    fake8 = FakeSupabaseClient()
    run_id_8 = str(uuid4())
    fake8.tables["app.nesting_runs"].append({
        "id": run_id_8,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })
    fake8.tables["app.nesting_run_snapshots"].append({
        "id": str(uuid4()),
        "run_id": run_id_8,
        "manufacturing_manifest_jsonb": {},
        "includes_manufacturing": False,
    })

    got_error_8 = False
    try:
        generate_machine_neutral_export(
            supabase=fake8,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=run_id_8,
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineNeutralExporterError as exc:
        got_error_8 = True
        _test("error mentions plan", "plan" in exc.detail.lower())
    _test("error raised for missing plans", got_error_8)

    # ===================================================================
    # TEST 9: error on ownership violation
    # ===================================================================
    print("\nTest 9: error on ownership violation")
    fake9 = FakeSupabaseClient()
    ids9 = _seed_full(fake9)
    other_owner = "00000000-0000-0000-0000-000000000099"

    got_error_9 = False
    try:
        generate_machine_neutral_export(
            supabase=fake9,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=other_owner,
            run_id=ids9["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineNeutralExporterError as exc:
        got_error_9 = True
        _test("error mentions not found/owned", "not found" in exc.detail.lower() or "not owned" in exc.detail.lower())
    _test("error raised for ownership violation", got_error_9)

    # ===================================================================
    # TEST 10: payload structure matches export contract
    # ===================================================================
    print("\nTest 10: payload structure matches export contract")
    _test("has export_contract_version", payload_json.get("export_contract_version") == EXPORT_CONTRACT_VERSION)
    _test("has run_id", payload_json.get("run_id") == ids1["run_id"])
    _test("has project_id", payload_json.get("project_id") == PROJECT_ID)
    _test("has manufacturing_profile_version_id", payload_json.get("manufacturing_profile_version_id") == MFG_PROFILE_VERSION_ID)
    _test("has sheets list", isinstance(payload_json.get("sheets"), list))
    _test("sheets has 1 entry", len(payload_json.get("sheets") or []) == 1)

    sheet_block = (payload_json.get("sheets") or [{}])[0]
    _test("sheet has sheet_index", "sheet_index" in sheet_block)
    _test("sheet has contours list", isinstance(sheet_block.get("contours"), list))
    _test("sheet has 2 contours", len(sheet_block.get("contours") or []) == 2)

    if sheet_block.get("contours"):
        c0 = sheet_block["contours"][0]
        _test("contour has contour_kind", "contour_kind" in c0)
        _test("contour has feature_class", "feature_class" in c0)
        _test("contour has cut_order_index", "cut_order_index" in c0)
        _test("contour has entry_point_jsonb", "entry_point_jsonb" in c0)
        _test("contour has lead_in_jsonb", "lead_in_jsonb" in c0)
        _test("contour has lead_out_jsonb", "lead_out_jsonb" in c0)

    # Optional metrics present in payload
    _test("has manufacturing_metrics", "manufacturing_metrics" in payload_json)
    mm = payload_json.get("manufacturing_metrics") or {}
    _test("metrics has pierce_count", "pierce_count" in mm)

    # ===================================================================
    # TEST 11: artifact metadata policy
    # ===================================================================
    print("\nTest 11: artifact metadata policy")
    if _registered:
        meta = _registered[0].get("metadata_json") or {}
        _test("metadata has filename", meta.get("filename") == "out/manufacturing_plan.json")
        _test("metadata has size_bytes", "size_bytes" in meta)
        _test("metadata has content_sha256", "content_sha256" in meta)
        _test("metadata has legacy_artifact_type", meta.get("legacy_artifact_type") == "manufacturing_plan_json")
        _test("metadata has export_scope", meta.get("export_scope") == "h2_e5_t3")
        _test("metadata has export_contract_version", meta.get("export_contract_version") == EXPORT_CONTRACT_VERSION)

    # ===================================================================
    # TEST 12: upload bucket is run-artifacts
    # ===================================================================
    print("\nTest 12: bucket is run-artifacts")
    if _uploaded:
        _test("bucket is run-artifacts", _uploaded[0].get("bucket") == "run-artifacts")

    # ===================================================================
    # TEST 13: canonical JSON has sorted keys (deterministic)
    # ===================================================================
    print("\nTest 13: canonical JSON structure")
    if isinstance(payload1, bytes):
        raw_text = payload1.decode("utf-8")
        # Verify it's valid JSON
        reparsed = json.loads(raw_text)
        # Verify sorted keys (re-serialized with sort_keys should match)
        canonical = json.dumps(reparsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        _test("payload is canonical JSON (sorted keys, compact)", raw_text == canonical)

    # ===================================================================
    # Summary
    # ===================================================================
    print(f"\n{'=' * 60}")
    total = passed + failed
    print(f"  TOTAL: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
    if failed:
        print("  STATUS: FAIL")
    else:
        print("  STATUS: PASS")
    print(f"{'=' * 60}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
