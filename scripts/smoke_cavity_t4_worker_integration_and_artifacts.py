#!/usr/bin/env python3
"""Smoke for cavity T4 worker integration + cavity_plan artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import worker.main as worker_main  # noqa: E402
from vrs_nesting.config.nesting_quality_profiles import compact_runtime_policy, runtime_policy_for_quality_profile  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _snapshot(*, quality_profile: str) -> dict[str, Any]:
    return {
        "snapshot_status": "ready",
        "project_manifest_jsonb": {"project_id": "p1", "project_name": "Project One"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-parent",
                "part_revision_id": "parent-a",
                "part_definition_id": "part-def-parent",
                "part_code": "PARENT_A",
                "required_qty": 1,
                "placement_priority": 1,
                "selected_nesting_derivative_id": "drv-parent-a",
                "source_geometry_revision_id": "geo-parent-a",
            },
            {
                "project_part_requirement_id": "req-child",
                "part_revision_id": "child-a",
                "part_definition_id": "part-def-child",
                "part_code": "CHILD_A",
                "required_qty": 2,
                "placement_priority": 2,
                "selected_nesting_derivative_id": "drv-child-a",
                "source_geometry_revision_id": "geo-child-a",
            },
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-input-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-001",
                "required_qty": 1,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 100.0,
                "height_mm": 100.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "drv-parent-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 20.0, 20.0),
                    "hole_rings": [_rect(2.0, 2.0, 12.0, 12.0)],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 20.0,
                    "max_y": 20.0,
                    "width": 20.0,
                    "height": 20.0,
                },
            },
            {
                "selected_nesting_derivative_id": "drv-child-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 3.0, 3.0),
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 3.0,
                    "max_y": 3.0,
                    "width": 3.0,
                    "height": 3.0,
                },
            },
        ],
        "solver_config_jsonb": {
            "seed": 7,
            "time_limit_s": 2,
            "rotation_step_deg": 90,
            "allow_free_rotation": False,
            "kerf_mm": 0.0,
            "spacing_mm": 0.0,
            "margin_mm": 0.0,
            "engine_backend_hint": "nesting_engine_v2",
            "quality_profile": quality_profile,
            "nesting_engine_runtime_policy": compact_runtime_policy(
                runtime_policy_for_quality_profile(quality_profile)
            ),
        },
    }


class FakeClient:
    def __init__(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot
        self.uploaded: dict[str, bytes] = {}
        self.run_artifacts: list[dict[str, Any]] = []
        self.raw_registered: list[dict[str, Any]] = []
        self.snapshot_hashes: list[str] = []
        self.done_calls = 0

    def mark_run_running(self, run_id: str) -> None:
        _ = run_id

    def fetch_run_snapshot(self, run_id: str) -> dict[str, Any]:
        _ = run_id
        return dict(self._snapshot)

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        _ = bucket
        self.uploaded[object_key] = bytes(payload)

    def set_run_input_snapshot_hash(self, *, run_id: str, snapshot_hash: str) -> None:
        _ = run_id
        self.snapshot_hashes.append(snapshot_hash)

    def insert_run_artifact(self, **kwargs: Any) -> None:
        self.run_artifacts.append(dict(kwargs))

    def register_run_artifact_raw(self, **kwargs: Any) -> None:
        self.raw_registered.append(dict(kwargs))

    def fetch_run_status(self, run_id: str) -> str:
        _ = run_id
        return "running"

    def heartbeat_queue_item(self, *, queue_id: str, worker_id: str, lease_token: str) -> bool:
        _ = (queue_id, worker_id, lease_token)
        return True

    def replace_run_projection(self, **kwargs: Any) -> None:
        _ = kwargs

    def fetch_viewer_outline_derivatives(self, *, geometry_revision_ids: list[str]) -> dict[str, dict[str, Any]]:
        _ = geometry_revision_ids
        return {}

    def fetch_nesting_canonical_derivatives(self, *, geometry_revision_ids: list[str]) -> dict[str, dict[str, Any]]:
        _ = geometry_revision_ids
        return {}

    def complete_run_done_and_dequeue(
        self,
        *,
        run_id: str,
        solver_exit_code: int,
        placements_count: int,
        unplaced_count: int,
        sheet_count: int,
    ) -> None:
        _ = (run_id, solver_exit_code, placements_count, unplaced_count, sheet_count)
        self.done_calls += 1

    def complete_run_failed_and_dequeue(self, *, run_id: str, message: str) -> None:
        raise RuntimeError(f"unexpected failed path run_id={run_id} msg={message}")

    def requeue_run_with_delay(self, *, run_id: str, message: str, retry_delay_s: int) -> None:
        raise RuntimeError(f"unexpected requeue path run_id={run_id} msg={message} retry={retry_delay_s}")

    def complete_run_cancelled_and_dequeue(self, *, run_id: str, message: str) -> None:
        raise RuntimeError(f"unexpected cancel path run_id={run_id} msg={message}")


class FakePopen:
    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self.returncode: int | None = None
        self._poll_calls = 0

    def poll(self) -> int | None:
        if self.returncode is not None:
            return self.returncode
        if self._poll_calls == 0:
            self._poll_calls += 1
            return None
        self.returncode = 0
        return 0

    def terminate(self) -> None:
        if self.returncode is None:
            self.returncode = -15

    def kill(self) -> None:
        if self.returncode is None:
            self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        if self.returncode is None:
            self.returncode = 0
        return int(self.returncode)

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        _ = timeout
        if self.returncode is None:
            self.returncode = 0
        return (f"{self._run_dir}\n", "")


def _settings(temp_root: Path) -> worker_main.WorkerSettings:
    return worker_main.WorkerSettings(
        supabase_url="https://example.supabase.co",
        supabase_project_ref="proj",
        supabase_access_token="token",
        supabase_service_role_key="service",
        storage_bucket="vrs-nesting",
        worker_id="worker-smoke-t4",
        poll_interval_s=0.1,
        retry_delay_s=1,
        alert_backlog_seconds=60,
        run_timeout_extra_s=0,
        run_log_sync_interval_s=1.0,
        queue_heartbeat_s=1.0,
        queue_lease_ttl_s=10,
        stale_temp_cleanup_max_age_s=60.0,
        run_root=temp_root / "runs-root",
        temp_root=temp_root,
        run_artifacts_bucket="run-artifacts",
        sparrow_bin="",
        once=True,
        engine_backend=worker_main.ENGINE_BACKEND_NESTING_V2,
        quality_profile_override=None,
    )


def _run_case(*, quality_profile: str) -> FakeClient:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"smoke_cavity_t4_{quality_profile}_"))
    try:
        client = FakeClient(_snapshot(quality_profile=quality_profile))
        settings = _settings(temp_dir)
        fake_run_dir = temp_dir / "runs" / "fake-run"
        fake_run_dir.mkdir(parents=True, exist_ok=True)

        queue_item = {
            "id": "queue-1",
            "run_id": "run-1",
            "lease_token": "lease-token",
            "attempts": 1,
            "max_attempts": 1,
        }

        projection = SimpleNamespace(
            sheets=[
                {
                    "sheet_index": 0,
                    "sheet_revision_id": "sheet-rev-1",
                    "width_mm": 100.0,
                    "height_mm": 100.0,
                    "utilization_ratio": 0.1,
                    "metadata_jsonb": {},
                }
            ],
            placements=[],
            unplaced=[],
            metrics={
                "placed_count": 0,
                "unplaced_count": 0,
                "used_sheet_count": 1,
                "utilization_ratio": 0.1,
                "remnant_value": 0.0,
                "metrics_jsonb": {},
            },
            summary=SimpleNamespace(placed_count=0, unplaced_count=0, used_sheet_count=1),
        )

        with (
            patch.object(
                worker_main.subprocess,
                "Popen",
                side_effect=lambda cmd, stdout, stderr, text: FakePopen(fake_run_dir),
            ),
            patch.object(worker_main.time, "sleep", return_value=None),
            patch.object(worker_main, "persist_raw_output_artifacts", return_value=[]),
            patch.object(worker_main, "persist_sheet_svg_artifacts", return_value=[]),
            patch.object(worker_main, "persist_sheet_dxf_artifacts", return_value=[]),
            patch.object(worker_main, "_sync_run_log_artifact", return_value=0),
            patch.object(worker_main, "normalize_solver_output_projection", return_value=projection),
            patch.object(worker_main, "assert_projection_within_sheet_bounds", return_value=None),
        ):
            worker_main._process_queue_item(client, settings, queue_item)
        return client
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _assert_prepack_case(client: FakeClient) -> None:
    solver_snapshot_key = "runs/run-1/inputs/solver_input_snapshot.json"
    cavity_plan_key = "runs/run-1/inputs/cavity_plan.json"
    _assert(solver_snapshot_key in client.uploaded, "missing solver input snapshot upload")
    _assert(cavity_plan_key in client.uploaded, "missing cavity_plan upload")

    solver_payload = json.loads(client.uploaded[solver_snapshot_key].decode("utf-8"))
    parts = solver_payload.get("parts")
    _assert(isinstance(parts, list), "solver snapshot parts missing")
    virtual_parts = [p for p in parts if str(p.get("id", "")).startswith("__cavity_composite__")]
    _assert(len(virtual_parts) >= 1, "expected virtual parent part in prepacked solver input")
    _assert(all(p.get("holes_points_mm") == [] for p in virtual_parts), "virtual parent must have no holes")

    cavity_plan = json.loads(client.uploaded[cavity_plan_key].decode("utf-8"))
    _assert(cavity_plan.get("version") == "cavity_plan_v1", "invalid cavity plan version")
    _assert(cavity_plan.get("enabled") is True, "cavity plan must be enabled")

    raw_types = [str(item.get("metadata_json", {}).get("legacy_artifact_type") or "") for item in client.raw_registered]
    _assert("cavity_plan" in raw_types, "cavity_plan artifact registration missing")

    engine_meta_raw = next(
        (
            item
            for item in client.raw_registered
            if str(item.get("metadata_json", {}).get("legacy_artifact_type") or "") == "engine_meta"
        ),
        None,
    )
    _assert(engine_meta_raw is not None, "engine_meta artifact registration missing")
    engine_meta_key = str(engine_meta_raw["storage_path"])
    engine_meta_payload = json.loads(client.uploaded[engine_meta_key].decode("utf-8"))
    cavity_meta = engine_meta_payload.get("cavity_prepack")
    _assert(isinstance(cavity_meta, dict), "engine_meta missing cavity_prepack summary")
    _assert(cavity_meta.get("enabled") is True, "engine_meta cavity_prepack.enabled mismatch")
    _assert(int(cavity_meta.get("virtual_parent_count") or 0) >= 1, "virtual_parent_count should be >= 1")


def _assert_non_prepack_case(client: FakeClient) -> None:
    solver_snapshot_key = "runs/run-1/inputs/solver_input_snapshot.json"
    cavity_plan_key = "runs/run-1/inputs/cavity_plan.json"
    _assert(solver_snapshot_key in client.uploaded, "missing solver input snapshot upload in non-prepack case")
    _assert(cavity_plan_key not in client.uploaded, "unexpected cavity_plan upload in non-prepack case")

    solver_payload = json.loads(client.uploaded[solver_snapshot_key].decode("utf-8"))
    parts = solver_payload.get("parts")
    _assert(isinstance(parts, list), "solver snapshot parts missing")
    parent = next((p for p in parts if p.get("id") == "parent-a"), None)
    _assert(parent is not None, "parent part missing in non-prepack case")
    holes = parent.get("holes_points_mm")
    _assert(isinstance(holes, list) and len(holes) == 1, "non-prepack case should keep parent hole")


def main() -> int:
    prepack_client = _run_case(quality_profile="quality_cavity_prepack")
    _assert_prepack_case(prepack_client)

    non_prepack_client = _run_case(quality_profile="quality_default")
    _assert_non_prepack_case(non_prepack_client)

    print("[smoke_cavity_t4_worker_integration_and_artifacts] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
