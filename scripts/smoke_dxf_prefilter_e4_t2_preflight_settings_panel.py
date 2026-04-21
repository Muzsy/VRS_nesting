#!/usr/bin/env python3
"""DXF Prefilter E4-T2 smoke checks.

Deterministic smoke that validates:
- DxfIntakePage settings panel fields/defaults/reset presence,
- API completeUpload optional rules_profile_snapshot_jsonb support,
- complete_upload route bridge forwards snapshot to runtime task,
- runtime no longer hardcodes rules_profile=None in pipeline persistence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser
from api.routes.files import FileCompleteRequest, complete_upload
import api.routes.files as files_mod


def _assert(condition: bool, message: str) -> None:
    if not condition:
        print(f"  FAIL: {message}")
        raise SystemExit(1)


def _scenario(name: str) -> None:
    print(f"  {name} ... ", end="", flush=True)


def _ok() -> None:
    print("OK")


def scenario_settings_panel_fields_defaults_and_reset() -> None:
    _scenario("INTAKE SETTINGS PANEL FIELDS/DEFAULTS")
    src = (ROOT / "frontend/src/pages/DxfIntakePage.tsx").read_text(encoding="utf-8")

    required_fields = [
        "strict_mode",
        "auto_repair_enabled",
        "interactive_review_on_ambiguity",
        "max_gap_close_mm",
        "duplicate_contour_merge_tolerance_mm",
        "cut_color_map",
        "marking_color_map",
        "Reset to defaults",
        "rules_profile_snapshot_jsonb",
    ]
    for token in required_fields:
        _assert(token in src, f"missing intake settings token: {token}")

    _assert(re.search(r"strict_mode:\s*false", src) is not None, "strict_mode default should be false")
    _assert(re.search(r"auto_repair_enabled:\s*false", src) is not None, "auto_repair_enabled default should be false")
    _assert(
        re.search(r"interactive_review_on_ambiguity:\s*true", src) is not None,
        "interactive_review_on_ambiguity default should be true",
    )
    _assert(re.search(r"max_gap_close_mm:\s*1(?:\.0+)?", src) is not None, "max_gap_close_mm default should be 1.0")
    _assert(
        re.search(r"duplicate_contour_merge_tolerance_mm:\s*0\.05", src) is not None,
        "duplicate_contour_merge_tolerance_mm default should be 0.05",
    )
    _ok()


def scenario_api_complete_upload_supports_optional_snapshot() -> None:
    _scenario("API OPTIONAL SNAPSHOT PAYLOAD")
    api_src = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")

    _assert(
        "rules_profile_snapshot_jsonb?: PreflightRulesProfileSnapshot | null" in api_src,
        "completeUpload payload type missing optional rules_profile_snapshot_jsonb",
    )
    _ok()


class _RouteFakeSupabase:
    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if table == "app.projects":
            return [{"id": str(params.get("id", ""))}]
        raise AssertionError(f"unexpected select_rows table={table}")

    def insert_row(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if table != "app.file_objects":
            raise AssertionError(f"unexpected insert_row table={table}")
        return {
            **payload,
            "id": payload["id"],
            "created_at": "2026-04-21T00:00:00+00:00",
        }


def scenario_route_bridge_forwards_snapshot_to_runtime_task() -> None:
    _scenario("ROUTE BRIDGE SNAPSHOT FORWARD")

    file_id = uuid4()
    project_id = uuid4()
    storage_path = f"projects/{project_id}/files/{file_id}/part.dxf"
    snapshot = {
        "strict_mode": True,
        "auto_repair_enabled": False,
        "interactive_review_on_ambiguity": True,
        "max_gap_close_mm": 1.0,
        "duplicate_contour_merge_tolerance_mm": 0.05,
        "cut_color_map": [1, 3],
        "marking_color_map": [2],
    }

    original_loader = files_mod.load_file_ingest_metadata
    files_mod.load_file_ingest_metadata = lambda **_: SimpleNamespace(
        file_name="part.dxf",
        mime_type="application/dxf",
        byte_size=128,
        sha256="abc123",
    )
    try:
        background_tasks = BackgroundTasks()
        response = complete_upload(
            project_id=project_id,
            req=FileCompleteRequest(
                file_id=UUID(str(file_id)),
                storage_path=storage_path,
                file_kind="source_dxf",
                rules_profile_snapshot_jsonb=snapshot,
            ),
            background_tasks=background_tasks,
            user=AuthenticatedUser(id="user-1", access_token="token"),
            supabase=_RouteFakeSupabase(),
            settings=SimpleNamespace(storage_bucket="source-files", signed_url_ttl_s=300),
        )
    finally:
        files_mod.load_file_ingest_metadata = original_loader

    _assert(len(background_tasks.tasks) == 2, "route should register 2 background tasks")
    _assert(
        background_tasks.tasks[0].func is files_mod.validate_dxf_file_async,
        "legacy validate_dxf_file_async task missing",
    )
    _assert(
        background_tasks.tasks[1].func is files_mod.run_preflight_for_upload,
        "run_preflight_for_upload task missing",
    )
    _assert(
        background_tasks.tasks[1].kwargs.get("rules_profile") == snapshot,
        "route did not forward rules_profile snapshot to runtime task",
    )
    _assert(response.file_kind == "source_dxf", "response file_kind mismatch")
    _ok()


def scenario_runtime_no_rules_profile_none_hardcode() -> None:
    _scenario("RUNTIME RULES_PROFILE PLUMBING")
    runtime_src = (ROOT / "api/services/dxf_preflight_runtime.py").read_text(encoding="utf-8")

    _assert("rules_profile=None" not in runtime_src, "runtime should not persist hardcoded rules_profile=None")
    _assert(
        "rules_profile=rules_profile" in runtime_src,
        "runtime should forward rules_profile to downstream calls",
    )
    _ok()


def main() -> None:
    print("DXF Prefilter E4-T2 smoke:")
    scenario_settings_panel_fields_defaults_and_reset()
    scenario_api_complete_upload_supports_optional_snapshot()
    scenario_route_bridge_forwards_snapshot_to_runtime_task()
    scenario_runtime_no_rules_profile_none_hardcode()
    print("All smoke scenarios passed.")


if __name__ == "__main__":
    main()
