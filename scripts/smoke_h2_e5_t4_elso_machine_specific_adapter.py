#!/usr/bin/env python3
"""H2-E5-T4 smoke: machine-specific adapter — per-sheet machine_program artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.machine_specific_adapter import (  # noqa: E402
    generate_machine_programs_for_run,
    MachineSpecificAdapterError,
    TARGET_ADAPTER_KEY,
    TARGET_OUTPUT_FORMAT,
    TARGET_LEGACY_ARTIFACT_TYPE,
    _ARTIFACT_KIND,
    _ALLOWED_CONFIG_BLOCKS,
    _REQUIRED_CONFIG_BLOCKS,
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
            "app.postprocessor_profile_versions": [],
            "app.geometry_derivatives": [],
            "app.geometry_contour_classes": [],
            "app.cut_contour_rules": [],
        }
        self.write_log: list[dict[str, Any]] = []
        self._object_store: dict[str, bytes] = {}

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

    def create_signed_download_url(
        self, *, access_token: str, bucket: str, object_key: str,
    ) -> dict[str, Any]:
        return {"download_url": f"fake://{bucket}/{object_key}"}

    def download_signed_object(self, *, signed_url: str) -> bytes:
        # Strip fake:// prefix to recover the storage key
        key = signed_url.replace("fake://", "")
        return self._object_store.get(key, b"{}")


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
# Config baseline (from canvas)
# ---------------------------------------------------------------------------

_CONFIG_BASELINE: dict[str, Any] = {
    "program_format": {
        "file_extension": ".txt",
        "code_page": "ascii",
        "line_ending": "lf",
        "comment_style": "parentheses",
        "word_separator": "none",
        "decimal_places": 3,
        "sequence_numbers": {"mode": "none", "start": 10, "step": 10},
        "program_id_policy": {"integer_only": False, "max_length": 64},
    },
    "motion_output": {
        "units": "mm",
        "distance_mode": "incremental",
        "arc_center_mode": "incremental",
        "arc_format": "ijk",
        "rapid_mode": "G00",
    },
    "coordinate_mapping": {
        "origin_anchor": "sheet_bottom_left",
        "mirror_x": False,
        "mirror_y": False,
        "swap_xy": False,
    },
    "command_map": {
        "program_start": ["G21", "G91"],
        "program_end": ["M02"],
        "rapid": "G00",
        "linear": "G01",
        "arc_cw": "G02",
        "arc_ccw": "G03",
        "process_on": "M07",
        "process_off": "M08",
        "pierce_on": None,
        "pierce_off": None,
    },
    "lead_output": {
        "supports_embedded_leads": True,
        "supported_shapes": ["line", "arc"],
        "allow_zero_lead_out": True,
        "emit_entry_marker": False,
        "unsupported_lead": "error",
    },
    "process_mapping": {
        "default_tool_code": None,
        "process_code_map": {},
    },
    "artifact_packaging": {
        "program_name_template": "{run_id}_sheet_{sheet_index}",
        "ascii_only": True,
        "max_filename_length": 64,
        "one_file_per_sheet": True,
    },
    "capabilities": {
        "supports_arcs": True,
        "supports_ijk_arcs": True,
        "supports_radius_arcs": False,
        "supports_comments": True,
        "supports_explicit_pierce_commands": False,
        "supports_multi_sheet_bundle": False,
    },
    "fallbacks": {
        "unsupported_arc": "error",
        "unsupported_comment": "drop",
        "unsupported_pierce": "inline_process_on",
    },
    "export_guards": {
        "require_program_end": True,
        "require_process_off_at_end": True,
        "forbid_empty_output": True,
    },
}

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"
PROJECT_ID = "00000000-0000-0000-0000-000000000002"
PP_VERSION_ID = "00000000-0000-0000-0000-000000000004"


def _build_export_payload(
    *,
    run_id: str,
    plan_id: str,
    sheet_index: int = 0,
    contours: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if contours is None:
        contours = [
            {
                "contour_index": 0,
                "contour_kind": "outer",
                "feature_class": "default",
                "cut_order_index": 0,
                "entry_point_jsonb": {"x": 10.0, "y": 10.0},
                "lead_in_jsonb": {"type": "line", "source": "matched_rule"},
                "lead_out_jsonb": {"type": "line", "source": "matched_rule"},
            },
            {
                "contour_index": 1,
                "contour_kind": "inner",
                "feature_class": "default",
                "cut_order_index": 1,
                "entry_point_jsonb": {"x": 30.0, "y": 30.0},
                "lead_in_jsonb": {"type": "line", "source": "matched_rule"},
                "lead_out_jsonb": {"type": "none", "source": "matched_rule"},
            },
        ]
    return {
        "export_contract_version": "h2_e5_t3_v1",
        "run_id": run_id,
        "project_id": PROJECT_ID,
        "sheets": [
            {
                "sheet_index": sheet_index,
                "plan_id": plan_id,
                "contours": contours,
            },
        ],
    }


def _seed_full(
    fake: FakeSupabaseClient,
    *,
    adapter_key: str = TARGET_ADAPTER_KEY,
    output_format: str = TARGET_OUTPUT_FORMAT,
    config_override: dict[str, Any] | None = None,
    extra_contours: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Seed a complete happy-path scenario for the machine_specific_adapter."""
    run_id = str(uuid4())
    plan_id = str(uuid4())
    deriv_id_0 = str(uuid4())
    deriv_id_1 = str(uuid4())

    # Run
    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })

    # Snapshot with postprocessor selection
    fake.tables["app.nesting_run_snapshots"].append({
        "id": str(uuid4()),
        "run_id": run_id,
        "manufacturing_manifest_jsonb": {
            "mode": "h2_e5_t2_snapshot_selection",
            "project_id": PROJECT_ID,
            "selection_present": True,
            "postprocess_selection_present": True,
            "postprocessor_profile_version": {
                "active_postprocessor_profile_version_id": PP_VERSION_ID,
                "adapter_key": adapter_key,
                "output_format": output_format,
                "schema_version": "v1",
            },
        },
        "includes_manufacturing": True,
        "includes_postprocess": True,
    })

    # Postprocessor profile version with config_jsonb
    config = config_override if config_override is not None else dict(_CONFIG_BASELINE)
    fake.tables["app.postprocessor_profile_versions"].append({
        "id": PP_VERSION_ID,
        "config_jsonb": config,
    })

    # Export artifact (manufacturing_plan_json)
    export_payload = _build_export_payload(
        run_id=run_id, plan_id=plan_id, contours=extra_contours,
    )
    export_bytes = json.dumps(export_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    export_sha = hashlib.sha256(export_bytes).hexdigest()
    export_storage_path = f"projects/{PROJECT_ID}/runs/{run_id}/manufacturing_plan_json/{export_sha}.json"

    fake.tables["app.run_artifacts"].append({
        "id": str(uuid4()),
        "run_id": run_id,
        "artifact_kind": "manufacturing_plan_json",
        "storage_bucket": "run-artifacts",
        "storage_path": export_storage_path,
        "metadata_jsonb": {"legacy_artifact_type": "manufacturing_plan_json"},
    })

    # Store the actual bytes so FakeSupabaseClient can return them on download
    fake._object_store[f"run-artifacts/{export_storage_path}"] = export_bytes

    # Manufacturing contours (geometry resolution path)
    fake.tables["app.run_manufacturing_contours"].extend([
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "contour_index": 0,
            "geometry_derivative_id": deriv_id_0,
        },
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "contour_index": 1,
            "geometry_derivative_id": deriv_id_1,
        },
    ])

    # Geometry derivatives (manufacturing_canonical)
    fake.tables["app.geometry_derivatives"].extend([
        {
            "id": deriv_id_0,
            "derivative_kind": "manufacturing_canonical",
            "derivative_jsonb": {
                "contours": [
                    {
                        "contour_index": 0,
                        "contour_role": "outer",
                        "winding": "ccw",
                        "points": [
                            [0.0, 0.0], [100.0, 0.0], [100.0, 80.0], [0.0, 80.0],
                        ],
                    },
                ],
            },
        },
        {
            "id": deriv_id_1,
            "derivative_kind": "manufacturing_canonical",
            "derivative_jsonb": {
                "contours": [
                    {
                        "contour_index": 1,
                        "contour_role": "inner",
                        "winding": "cw",
                        "points": [
                            [20.0, 20.0], [60.0, 20.0], [60.0, 50.0], [20.0, 50.0],
                        ],
                    },
                ],
            },
        },
    ])

    return {
        "run_id": run_id,
        "plan_id": plan_id,
        "deriv_id_0": deriv_id_0,
        "deriv_id_1": deriv_id_1,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed, _uploaded, _registered

    # ===================================================================
    # TEST 1: valid plan + valid config -> per-sheet machine_program artifacts
    # ===================================================================
    print("Test 1: valid export + valid target config -> machine_program artifacts")
    fake1 = FakeSupabaseClient()
    ids1 = _seed_full(fake1)
    _uploaded = []
    _registered = []

    result1 = generate_machine_programs_for_run(
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
    _test("adapter_key correct", result1.get("adapter_key") == TARGET_ADAPTER_KEY)
    _test("output_format correct", result1.get("output_format") == TARGET_OUTPUT_FORMAT)
    _test("programs_created == 1 (1 sheet)", result1.get("programs_created") == 1)
    sheets_out = result1.get("sheets") or []
    _test("sheets list has 1 entry", len(sheets_out) == 1)
    _test("1 upload", len(_uploaded) == 1)
    _test("1 register", len(_registered) == 1)

    # ===================================================================
    # TEST 2: artifact_kind and legacy_artifact_type correct
    # ===================================================================
    print("\nTest 2: artifact_kind='machine_program' and legacy_artifact_type correct")
    if _registered:
        reg0 = _registered[0]
        _test("artifact_kind is machine_program", reg0.get("artifact_kind") == _ARTIFACT_KIND)
        meta = reg0.get("metadata_json") or {}
        _test(
            "legacy_artifact_type correct",
            meta.get("legacy_artifact_type") == TARGET_LEGACY_ARTIFACT_TYPE,
        )
        _test("adapter_key in metadata", meta.get("adapter_key") == TARGET_ADAPTER_KEY)
        _test("output_format in metadata", meta.get("output_format") == TARGET_OUTPUT_FORMAT)
        _test("sheet_index in metadata", "sheet_index" in meta)
        _test("content_sha256 in metadata", "content_sha256" in meta)
        _test("size_bytes in metadata", "size_bytes" in meta)
    else:
        _test("register called", False, "no register calls")

    # ===================================================================
    # TEST 3: hash / filename / storage path deterministic
    # ===================================================================
    print("\nTest 3: deterministic output (same truth -> same hash, filename, path)")
    fake3 = FakeSupabaseClient()
    ids3 = _seed_full(fake3)

    uploaded_a: list[dict[str, Any]] = []
    registered_a: list[dict[str, Any]] = []
    result_a = generate_machine_programs_for_run(
        supabase=fake3,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids3["run_id"],
        upload_object=lambda **kw: uploaded_a.append(kw),
        register_artifact=lambda **kw: registered_a.append(kw),
    )

    uploaded_b: list[dict[str, Any]] = []
    registered_b: list[dict[str, Any]] = []
    result_b = generate_machine_programs_for_run(
        supabase=fake3,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids3["run_id"],
        upload_object=lambda **kw: uploaded_b.append(kw),
        register_artifact=lambda **kw: registered_b.append(kw),
    )

    sheets_a = result_a.get("sheets") or [{}]
    sheets_b = result_b.get("sheets") or [{}]
    _test("content_sha256 matches", sheets_a[0].get("content_sha256") == sheets_b[0].get("content_sha256"))
    _test("filename matches", sheets_a[0].get("filename") == sheets_b[0].get("filename"))
    _test("storage_path matches", sheets_a[0].get("storage_path") == sheets_b[0].get("storage_path"))
    _test("size_bytes matches", sheets_a[0].get("size_bytes") == sheets_b[0].get("size_bytes"))

    # Byte-level equality
    payload_a = uploaded_a[0].get("payload", b"") if uploaded_a else b""
    payload_b = uploaded_b[0].get("payload", b"") if uploaded_b else b""
    _test("byte-level identical", payload_a == payload_b)

    # Filename format check
    expected_filename = f"{ids3['run_id']}_sheet_0.txt"
    _test("filename format correct", sheets_a[0].get("filename") == expected_filename)

    # Storage path format check
    sp = sheets_a[0].get("storage_path") or ""
    _test("storage_path has machine_program/hypertherm_edge_connect/",
          f"machine_program/{TARGET_ADAPTER_KEY}/" in sp)
    _test("storage_path ends with .txt", sp.endswith(".txt"))

    # ===================================================================
    # TEST 4: unsupported lead -> error (config says "error")
    # ===================================================================
    print("\nTest 4: unsupported lead-in type -> error")
    fake4 = FakeSupabaseClient()
    unsupported_lead_contours = [
        {
            "contour_index": 0,
            "contour_kind": "outer",
            "feature_class": "default",
            "cut_order_index": 0,
            "entry_point_jsonb": {"x": 0.0, "y": 0.0},
            "lead_in_jsonb": {"type": "spiral", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "none", "source": "matched_rule"},
        },
    ]
    ids4 = _seed_full(fake4, extra_contours=unsupported_lead_contours)

    got_error_4 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake4,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids4["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_4 = True
        _test("error mentions lead", "lead" in exc.detail.lower())
    _test("error raised for unsupported lead", got_error_4)

    # ===================================================================
    # TEST 5: unsupported lead with fallback policy -> skip (no error)
    # ===================================================================
    print("\nTest 5: unsupported lead with skip fallback -> no error")
    fake5 = FakeSupabaseClient()
    config_skip = dict(_CONFIG_BASELINE)
    config_skip["lead_output"] = dict(_CONFIG_BASELINE["lead_output"])
    config_skip["lead_output"]["unsupported_lead"] = "skip"
    ids5 = _seed_full(fake5, config_override=config_skip, extra_contours=unsupported_lead_contours)

    got_error_5 = False
    try:
        result5 = generate_machine_programs_for_run(
            supabase=fake5,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids5["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
        _test("skip fallback produces result", isinstance(result5, dict))
    except MachineSpecificAdapterError:
        got_error_5 = True
    _test("no error with skip fallback", not got_error_5)

    # ===================================================================
    # TEST 6: ownership boundary
    # ===================================================================
    print("\nTest 6: ownership boundary")
    fake6 = FakeSupabaseClient()
    ids6 = _seed_full(fake6)
    other_owner = "00000000-0000-0000-0000-000000000099"

    got_error_6 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake6,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=other_owner,
            run_id=ids6["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_6 = True
        _test("error mentions not found/owned", "not found" in exc.detail.lower() or "not owned" in exc.detail.lower())
    _test("error raised for ownership violation", got_error_6)

    # ===================================================================
    # TEST 7: missing manufacturing_plan_json artifact -> error
    # ===================================================================
    print("\nTest 7: missing manufacturing_plan_json artifact -> error")
    fake7 = FakeSupabaseClient()
    run_id_7 = str(uuid4())
    fake7.tables["app.nesting_runs"].append({
        "id": run_id_7,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })
    # No manufacturing_plan_json artifact seeded

    got_error_7 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake7,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=run_id_7,
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_7 = True
        _test("error mentions manufacturing_plan_json", "manufacturing_plan_json" in exc.detail.lower())
    _test("error raised for missing export artifact", got_error_7)

    # ===================================================================
    # TEST 8: adapter_key mismatch -> error
    # ===================================================================
    print("\nTest 8: adapter_key mismatch -> error")
    fake8 = FakeSupabaseClient()
    ids8 = _seed_full(fake8, adapter_key="wrong_adapter")

    got_error_8 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake8,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids8["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_8 = True
        _test("error mentions adapter_key mismatch", "adapter_key" in exc.detail.lower())
    _test("error raised for adapter_key mismatch", got_error_8)

    # ===================================================================
    # TEST 9: output_format mismatch -> error
    # ===================================================================
    print("\nTest 9: output_format mismatch -> error")
    fake9 = FakeSupabaseClient()
    ids9 = _seed_full(fake9, output_format="wrong_format")

    got_error_9 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake9,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids9["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_9 = True
        _test("error mentions output_format mismatch", "output_format" in exc.detail.lower())
    _test("error raised for output_format mismatch", got_error_9)

    # ===================================================================
    # TEST 10: missing required config blocks -> error
    # ===================================================================
    print("\nTest 10: missing required config blocks -> error")
    fake10 = FakeSupabaseClient()
    incomplete_config: dict[str, Any] = {
        "program_format": _CONFIG_BASELINE["program_format"],
        # Missing all other required blocks
    }
    ids10 = _seed_full(fake10, config_override=incomplete_config)

    got_error_10 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake10,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids10["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_10 = True
        _test("error mentions config block", "config block" in exc.detail.lower())
    _test("error raised for missing config blocks", got_error_10)

    # ===================================================================
    # TEST 11: no write to forbidden truth tables
    # ===================================================================
    print("\nTest 11: no write to forbidden truth tables")
    forbidden_tables = {
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.run_manufacturing_metrics",
        "app.geometry_contour_classes",
        "app.cut_contour_rules",
        "app.postprocessor_profile_versions",
    }
    violated = set()
    for w in fake1.write_log:
        tbl = w.get("table", "")
        if tbl in forbidden_tables:
            violated.add(tbl)
    for w in fake3.write_log:
        tbl = w.get("table", "")
        if tbl in forbidden_tables:
            violated.add(tbl)
    _test("no write to forbidden truth tables", len(violated) == 0,
          f"violated: {violated}")

    # ===================================================================
    # TEST 12: no forbidden artifact kinds or side effects
    # ===================================================================
    print("\nTest 12: no forbidden artifact kinds or side effects")
    for reg in _registered + registered_a + registered_b:
        ak = str(reg.get("artifact_kind") or "")
        _test(f"artifact_kind is machine_program (got {ak})", ak == _ARTIFACT_KIND)

    all_write_logs = fake1.write_log + fake3.write_log
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
    # TEST 13: idempotent rerun (delete-then-insert)
    # ===================================================================
    print("\nTest 13: idempotent rerun (no duplicate artifacts)")
    fake13 = FakeSupabaseClient()
    ids13 = _seed_full(fake13)

    # First run
    up13a: list[dict[str, Any]] = []
    reg13a: list[dict[str, Any]] = []
    generate_machine_programs_for_run(
        supabase=fake13,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids13["run_id"],
        upload_object=lambda **kw: up13a.append(kw),
        register_artifact=lambda **kw: reg13a.append(kw),
    )

    # Simulate that the first run registered artifacts into the fake table
    for reg in reg13a:
        fake13.tables["app.run_artifacts"].append({
            "id": str(uuid4()),
            "run_id": reg.get("run_id"),
            "artifact_kind": reg.get("artifact_kind"),
            "storage_bucket": reg.get("storage_bucket"),
            "storage_path": reg.get("storage_path"),
            "metadata_jsonb": reg.get("metadata_json"),
        })

    # Second run (should delete first, then insert)
    up13b: list[dict[str, Any]] = []
    reg13b: list[dict[str, Any]] = []
    fake13.write_log.clear()  # Clear to track only the second run's writes
    generate_machine_programs_for_run(
        supabase=fake13,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids13["run_id"],
        upload_object=lambda **kw: up13b.append(kw),
        register_artifact=lambda **kw: reg13b.append(kw),
    )

    delete_ops = [w for w in fake13.write_log if w.get("op") == "delete" and w.get("table") == "app.run_artifacts"]
    _test("idempotent delete happened", len(delete_ops) >= 1,
          f"got {len(delete_ops)} delete ops")
    _test("second run produced same count", len(reg13b) == len(reg13a))

    # ===================================================================
    # TEST 14: G-code output structure
    # ===================================================================
    print("\nTest 14: G-code output structure")
    if uploaded_a:
        program_text = uploaded_a[0].get("payload", b"").decode("ascii", errors="replace")
        _test("has program start G21", "G21" in program_text)
        _test("has program start G91", "G91" in program_text)
        _test("has program end M02", "M02" in program_text)
        _test("has process on M07", "M07" in program_text)
        _test("has process off M08", "M08" in program_text)
        _test("has rapid G00", "G00" in program_text)
        _test("has linear G01", "G01" in program_text)
        _test("has comment (parentheses)", program_text.startswith("("))
        _test("no volatile timestamp", "timestamp" not in program_text.lower())
        # Check for ISO date patterns (YYYY-MM-DD) rather than bare "202" which UUIDs can contain
        import re
        _test("no datetime in output", not re.search(r"\d{4}-\d{2}-\d{2}", program_text))

    # ===================================================================
    # TEST 15: upload bucket is run-artifacts
    # ===================================================================
    print("\nTest 15: upload bucket is run-artifacts")
    if _uploaded:
        _test("bucket is run-artifacts", _uploaded[0].get("bucket") == "run-artifacts")

    # ===================================================================
    # TEST 16: no second implicit adapter output
    # ===================================================================
    print("\nTest 16: no second implicit adapter output")
    _test("exactly 1 upload per sheet (1 sheet)", len(_uploaded) == 1)
    _test("exactly 1 register per sheet (1 sheet)", len(_registered) == 1)

    # ===================================================================
    # TEST 17: frozen target constants match canvas
    # ===================================================================
    print("\nTest 17: frozen target constants")
    _test("TARGET_ADAPTER_KEY", TARGET_ADAPTER_KEY == "hypertherm_edge_connect")
    _test("TARGET_OUTPUT_FORMAT", TARGET_OUTPUT_FORMAT == "basic_plasma_eia_rs274d")
    _test("TARGET_LEGACY_ARTIFACT_TYPE", TARGET_LEGACY_ARTIFACT_TYPE == "hypertherm_edge_connect_basic_plasma_eia")
    _test("_ARTIFACT_KIND", _ARTIFACT_KIND == "machine_program")

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
