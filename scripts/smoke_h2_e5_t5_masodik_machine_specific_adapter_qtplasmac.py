#!/usr/bin/env python3
"""H2-E5-T5 smoke: QtPlasmaC machine-specific adapter + Hypertherm regression."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
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
    QTPLASMAC_ADAPTER_KEY,
    QTPLASMAC_OUTPUT_FORMAT,
    QTPLASMAC_LEGACY_ARTIFACT_TYPE,
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
# Fake Supabase client (reused from T4 smoke pattern)
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
# Config baselines
# ---------------------------------------------------------------------------

_HYPERTHERM_CONFIG: dict[str, Any] = {
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

_QTPLASMAC_CONFIG: dict[str, Any] = {
    "program_format": {
        "file_extension": ".ngc",
        "code_page": "ascii",
        "line_ending": "lf",
        "comment_style": "semicolon",
        "word_separator": "none",
        "decimal_places": 4,
        "sequence_numbers": {"mode": "none"},
    },
    "motion_output": {
        "units": "mm",
        "distance_mode": "absolute",
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
        "program_start": ["G21", "G90", "G40", "G64 P0.05"],
        "program_end": ["M02", "%"],
        "rapid": "G00",
        "linear": "G01",
        "arc_cw": "G02",
        "arc_ccw": "G03",
        "process_on": "M03 $0 S1",
        "process_off": "M05 $0",
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
        "supports_arcs": False,
        "supports_ijk_arcs": False,
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
    adapter_key: str = QTPLASMAC_ADAPTER_KEY,
    output_format: str = QTPLASMAC_OUTPUT_FORMAT,
    config_override: dict[str, Any] | None = None,
    extra_contours: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Seed a complete happy-path scenario."""
    run_id = str(uuid4())
    plan_id = str(uuid4())
    deriv_id_0 = str(uuid4())
    deriv_id_1 = str(uuid4())

    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })

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

    config = config_override if config_override is not None else dict(_QTPLASMAC_CONFIG)
    fake.tables["app.postprocessor_profile_versions"].append({
        "id": PP_VERSION_ID,
        "config_jsonb": config,
    })

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

    fake._object_store[f"run-artifacts/{export_storage_path}"] = export_bytes

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
    # TEST 1: valid QtPlasmaC export + valid target config -> per-sheet machine_program
    # ===================================================================
    print("Test 1: valid QtPlasmaC export + valid target config -> machine_program artifacts")
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
    _test("adapter_key is qtplasmac", result1.get("adapter_key") == QTPLASMAC_ADAPTER_KEY)
    _test("output_format is qtplasmac", result1.get("output_format") == QTPLASMAC_OUTPUT_FORMAT)
    _test("programs_created == 1 (1 sheet)", result1.get("programs_created") == 1)
    sheets_out = result1.get("sheets") or []
    _test("sheets list has 1 entry", len(sheets_out) == 1)
    _test("1 upload", len(_uploaded) == 1)
    _test("1 register", len(_registered) == 1)

    # ===================================================================
    # TEST 2: artifact_kind='machine_program' and legacy_artifact_type correct
    # ===================================================================
    print("\nTest 2: artifact_kind='machine_program' and QtPlasmaC legacy_artifact_type")
    if _registered:
        reg0 = _registered[0]
        _test("artifact_kind is machine_program", reg0.get("artifact_kind") == _ARTIFACT_KIND)
        meta = reg0.get("metadata_json") or {}
        _test(
            "legacy_artifact_type correct",
            meta.get("legacy_artifact_type") == QTPLASMAC_LEGACY_ARTIFACT_TYPE,
        )
        _test("adapter_key in metadata", meta.get("adapter_key") == QTPLASMAC_ADAPTER_KEY)
        _test("output_format in metadata", meta.get("output_format") == QTPLASMAC_OUTPUT_FORMAT)
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

    # Filename format: .ngc extension
    expected_filename = f"{ids3['run_id']}_sheet_0.ngc"
    _test("filename format correct (.ngc)", sheets_a[0].get("filename") == expected_filename)

    # Storage path format
    sp = sheets_a[0].get("storage_path") or ""
    _test("storage_path has machine_program/linuxcnc_qtplasmac/",
          f"machine_program/{QTPLASMAC_ADAPTER_KEY}/" in sp)
    _test("storage_path ends with .ngc", sp.endswith(".ngc"))

    # ===================================================================
    # TEST 4: Hypertherm target still works (regression check)
    # ===================================================================
    print("\nTest 4: Hypertherm target regression check")
    fake4 = FakeSupabaseClient()
    ids4 = _seed_full(
        fake4,
        adapter_key=TARGET_ADAPTER_KEY,
        output_format=TARGET_OUTPUT_FORMAT,
        config_override=dict(_HYPERTHERM_CONFIG),
    )
    up4: list[dict[str, Any]] = []
    reg4: list[dict[str, Any]] = []
    result4 = generate_machine_programs_for_run(
        supabase=fake4,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids4["run_id"],
        upload_object=lambda **kw: up4.append(kw),
        register_artifact=lambda **kw: reg4.append(kw),
    )
    _test("Hypertherm result ok", isinstance(result4, dict))
    _test("Hypertherm adapter_key", result4.get("adapter_key") == TARGET_ADAPTER_KEY)
    _test("Hypertherm output_format", result4.get("output_format") == TARGET_OUTPUT_FORMAT)
    _test("Hypertherm 1 upload", len(up4) == 1)
    _test("Hypertherm 1 register", len(reg4) == 1)
    if reg4:
        ht_meta = reg4[0].get("metadata_json") or {}
        _test("Hypertherm legacy type", ht_meta.get("legacy_artifact_type") == TARGET_LEGACY_ARTIFACT_TYPE)
    ht_sheets = result4.get("sheets") or [{}]
    _test("Hypertherm filename .txt", ht_sheets[0].get("filename", "").endswith(".txt"))
    ht_sp = ht_sheets[0].get("storage_path") or ""
    _test("Hypertherm storage path has hypertherm_edge_connect/",
          f"machine_program/{TARGET_ADAPTER_KEY}/" in ht_sp)
    _test("Hypertherm storage_path ends .txt", ht_sp.endswith(".txt"))
    if up4:
        ht_prog = up4[0].get("payload", b"").decode("ascii", errors="replace")
        _test("Hypertherm has G21", "G21" in ht_prog)
        _test("Hypertherm has M07 (process on)", "M07" in ht_prog)
        _test("Hypertherm has M02 (program end)", "M02" in ht_prog)

    # ===================================================================
    # TEST 5: unsupported adapter/output_format -> deterministic error
    # ===================================================================
    print("\nTest 5: unsupported adapter -> deterministic error")
    fake5 = FakeSupabaseClient()
    ids5 = _seed_full(fake5, adapter_key="unsupported_machine", output_format="unsupported_format")

    got_error_5 = False
    try:
        generate_machine_programs_for_run(
            supabase=fake5,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids5["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineSpecificAdapterError as exc:
        got_error_5 = True
        _test("error mentions unsupported", "unsupported" in exc.detail.lower())
    _test("error raised for unsupported target", got_error_5)

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
    # TEST 8: missing required config blocks -> error
    # ===================================================================
    print("\nTest 8: missing required config blocks -> error")
    fake8 = FakeSupabaseClient()
    incomplete_config: dict[str, Any] = {
        "program_format": _QTPLASMAC_CONFIG["program_format"],
    }
    ids8 = _seed_full(fake8, config_override=incomplete_config)

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
        _test("error mentions config block", "config block" in exc.detail.lower())
    _test("error raised for missing config blocks", got_error_8)

    # ===================================================================
    # TEST 9: missing target metadata (adapter_key) -> error
    # ===================================================================
    print("\nTest 9: missing adapter_key in snapshot -> error")
    fake9 = FakeSupabaseClient()
    ids9 = _seed_full(fake9, adapter_key="")

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
        _test("error mentions adapter_key", "adapter_key" in exc.detail.lower())
    _test("error raised for missing adapter_key", got_error_9)

    # ===================================================================
    # TEST 10: no write to forbidden truth tables
    # ===================================================================
    print("\nTest 10: no write to forbidden truth tables")
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
    # TEST 11: no forbidden artifact kinds or side effects
    # ===================================================================
    print("\nTest 11: no forbidden artifact kinds or side effects")
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
    # TEST 12: no M190/M66 auto material-change side effect
    # ===================================================================
    print("\nTest 12: no M190/M66 auto material-change in QtPlasmaC output")
    if uploaded_a:
        qtpc_text = uploaded_a[0].get("payload", b"").decode("ascii", errors="replace")
        _test("no M190 in output", "M190" not in qtpc_text)
        _test("no M66 in output", "M66" not in qtpc_text)
    else:
        _test("upload present for check", False)

    # ===================================================================
    # TEST 13: QtPlasmaC G-code output structure
    # ===================================================================
    print("\nTest 13: QtPlasmaC G-code output structure")
    if uploaded_a:
        _test("has G21 (metric)", "G21" in qtpc_text)
        _test("has G90 (absolute)", "G90" in qtpc_text)
        _test("has G40 (cutter comp off)", "G40" in qtpc_text)
        _test("has G64 (path blending)", "G64" in qtpc_text)
        _test("has M03 $0 S1 (torch on)", "M03 $0 S1" in qtpc_text)
        _test("has M05 $0 (torch off)", "M05 $0" in qtpc_text)
        _test("has M02 (program end)", "M02" in qtpc_text)
        _test("has % (end of tape)", "%" in qtpc_text)
        _test("has rapid G00", "G00" in qtpc_text)
        _test("has linear G01", "G01" in qtpc_text)
        _test("has semicolon comment", qtpc_text.startswith(";"))
        _test("no volatile timestamp", "timestamp" not in qtpc_text.lower())
        _test("no datetime in output", not re.search(r"\d{4}-\d{2}-\d{2}", qtpc_text))

    # ===================================================================
    # TEST 14: idempotent rerun (no duplicate QtPlasmaC artifacts)
    # ===================================================================
    print("\nTest 14: idempotent rerun (no duplicate QtPlasmaC artifacts)")
    fake14 = FakeSupabaseClient()
    ids14 = _seed_full(fake14)

    up14a: list[dict[str, Any]] = []
    reg14a: list[dict[str, Any]] = []
    generate_machine_programs_for_run(
        supabase=fake14,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids14["run_id"],
        upload_object=lambda **kw: up14a.append(kw),
        register_artifact=lambda **kw: reg14a.append(kw),
    )

    for reg in reg14a:
        fake14.tables["app.run_artifacts"].append({
            "id": str(uuid4()),
            "run_id": reg.get("run_id"),
            "artifact_kind": reg.get("artifact_kind"),
            "storage_bucket": reg.get("storage_bucket"),
            "storage_path": reg.get("storage_path"),
            "metadata_jsonb": reg.get("metadata_json"),
        })

    up14b: list[dict[str, Any]] = []
    reg14b: list[dict[str, Any]] = []
    fake14.write_log.clear()
    generate_machine_programs_for_run(
        supabase=fake14,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids14["run_id"],
        upload_object=lambda **kw: up14b.append(kw),
        register_artifact=lambda **kw: reg14b.append(kw),
    )

    delete_ops = [w for w in fake14.write_log if w.get("op") == "delete" and w.get("table") == "app.run_artifacts"]
    _test("idempotent delete happened", len(delete_ops) >= 1, f"got {len(delete_ops)} delete ops")
    _test("second run produced same count", len(reg14b) == len(reg14a))

    # ===================================================================
    # TEST 15: no implicit generic adapter output / no bundle
    # ===================================================================
    print("\nTest 15: no implicit generic adapter output / no bundle")
    _test("exactly 1 upload per sheet (1 sheet)", len(_uploaded) == 1)
    _test("exactly 1 register per sheet (1 sheet)", len(_registered) == 1)

    # ===================================================================
    # TEST 16: frozen target constants match canvas
    # ===================================================================
    print("\nTest 16: frozen target constants")
    _test("QTPLASMAC_ADAPTER_KEY", QTPLASMAC_ADAPTER_KEY == "linuxcnc_qtplasmac")
    _test("QTPLASMAC_OUTPUT_FORMAT", QTPLASMAC_OUTPUT_FORMAT == "basic_manual_material_rs274ngc")
    _test("QTPLASMAC_LEGACY_ARTIFACT_TYPE", QTPLASMAC_LEGACY_ARTIFACT_TYPE == "linuxcnc_qtplasmac_basic_manual_material")
    _test("_ARTIFACT_KIND", _ARTIFACT_KIND == "machine_program")
    # Hypertherm constants unchanged
    _test("TARGET_ADAPTER_KEY unchanged", TARGET_ADAPTER_KEY == "hypertherm_edge_connect")
    _test("TARGET_OUTPUT_FORMAT unchanged", TARGET_OUTPUT_FORMAT == "basic_plasma_eia_rs274d")
    _test("TARGET_LEGACY_ARTIFACT_TYPE unchanged", TARGET_LEGACY_ARTIFACT_TYPE == "hypertherm_edge_connect_basic_plasma_eia")

    # ===================================================================
    # TEST 17: upload bucket is run-artifacts
    # ===================================================================
    print("\nTest 17: upload bucket is run-artifacts")
    if _uploaded:
        _test("bucket is run-artifacts", _uploaded[0].get("bucket") == "run-artifacts")

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
