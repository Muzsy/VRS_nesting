#!/usr/bin/env python3
"""H3-Quality-T4 smoke: worker dual-engine runtime bridge."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import worker.main as worker_main  # noqa: E402


def _base_snapshot() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {
            "project_id": "p1",
            "project_name": "Project One",
        },
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-1",
                "part_revision_id": "part-rev-1",
                "part_definition_id": "part-def-1",
                "part_code": "PART-001",
                "required_qty": 2,
                "placement_priority": 10,
                "selected_nesting_derivative_id": "deriv-1",
                "source_geometry_revision_id": "geo-rev-1",
            }
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-input-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-001",
                "required_qty": 1,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 1200.0,
                "height_mm": 800.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "deriv-1",
                "polygon": {
                    "outer_ring": [[0.0, 0.0], [300.0, 0.0], [300.0, 200.0], [0.0, 200.0]],
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 300.0,
                    "max_y": 200.0,
                    "width": 300.0,
                    "height": 200.0,
                },
            }
        ],
        "solver_config_jsonb": {
            "seed": 7,
            "time_limit_s": 2,
            "rotation_step_deg": 90,
            "allow_free_rotation": False,
            "kerf_mm": 0.2,
            "spacing_mm": 0.4,
            "margin_mm": 2.0,
        },
    }


class FakeClient:
    def __init__(self, *, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot
        self._run_status = "running"

        self.marked_running = 0
        self.uploaded_objects: dict[str, bytes] = {}
        self.snapshot_hashes: list[str] = []
        self.inserted_artifacts: list[dict[str, Any]] = []
        self.registered_raw_artifacts: list[dict[str, Any]] = []
        self.replaced_projection: list[dict[str, Any]] = []

        self.done_calls: list[dict[str, Any]] = []
        self.failed_calls: list[dict[str, Any]] = []
        self.requeue_calls: list[dict[str, Any]] = []
        self.cancelled_calls: list[dict[str, Any]] = []

    def mark_run_running(self, run_id: str) -> None:
        _ = run_id
        self.marked_running += 1

    def fetch_run_snapshot(self, run_id: str) -> dict[str, Any]:
        _ = run_id
        row = dict(self._snapshot)
        row["snapshot_status"] = "ready"
        return row

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        key = f"{bucket}:{object_key}"
        self.uploaded_objects[key] = payload

    def set_run_input_snapshot_hash(self, *, run_id: str, snapshot_hash: str) -> None:
        _ = run_id
        self.snapshot_hashes.append(snapshot_hash)

    def insert_run_artifact(self, **kwargs: Any) -> None:
        self.inserted_artifacts.append(dict(kwargs))

    def register_run_artifact_raw(self, **kwargs: Any) -> None:
        self.registered_raw_artifacts.append(dict(kwargs))

    def replace_run_projection(
        self,
        *,
        run_id: str,
        sheets: list[dict[str, Any]],
        placements: list[dict[str, Any]],
        unplaced: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> None:
        self.replaced_projection.append(
            {
                "run_id": run_id,
                "sheets": list(sheets),
                "placements": list(placements),
                "unplaced": list(unplaced),
                "metrics": dict(metrics),
            }
        )

    def fetch_viewer_outline_derivatives(self, *, geometry_revision_ids: list[str]) -> dict[str, dict[str, Any]]:
        _ = geometry_revision_ids
        return {}

    def fetch_nesting_canonical_derivatives(self, *, geometry_revision_ids: list[str]) -> dict[str, dict[str, Any]]:
        _ = geometry_revision_ids
        return {}

    def fetch_run_status(self, run_id: str) -> str:
        _ = run_id
        return self._run_status

    def heartbeat_queue_item(self, *, queue_id: str, worker_id: str, lease_token: str) -> bool:
        _ = (queue_id, worker_id, lease_token)
        return True

    def complete_run_done_and_dequeue(
        self,
        *,
        run_id: str,
        solver_exit_code: int,
        placements_count: int,
        unplaced_count: int,
        sheet_count: int,
    ) -> None:
        self.done_calls.append(
            {
                "run_id": run_id,
                "solver_exit_code": solver_exit_code,
                "placements_count": placements_count,
                "unplaced_count": unplaced_count,
                "sheet_count": sheet_count,
            }
        )

    def complete_run_failed_and_dequeue(self, *, run_id: str, message: str) -> None:
        self.failed_calls.append({"run_id": run_id, "message": message})

    def requeue_run_with_delay(self, *, run_id: str, message: str, retry_delay_s: int) -> None:
        self.requeue_calls.append({"run_id": run_id, "message": message, "retry_delay_s": retry_delay_s})

    def complete_run_cancelled_and_dequeue(self, *, run_id: str, message: str) -> None:
        self.cancelled_calls.append({"run_id": run_id, "message": message})


class FakePopen:
    def __init__(self, *, cmd: list[str]) -> None:
        self.cmd = list(cmd)
        self.returncode: int | None = None
        self._poll_calls = 0
        self._run_dir = self._resolve_run_dir(self.cmd)

    @staticmethod
    def _resolve_run_dir(cmd: list[str]) -> Path:
        joined = " ".join(cmd)
        if "vrs_nesting.runner.vrs_solver_runner" in joined:
            if "--run-dir" not in cmd:
                raise RuntimeError("v1 runner command missing --run-dir")
            idx = cmd.index("--run-dir")
            return Path(cmd[idx + 1]).resolve()
        if "vrs_nesting.runner.nesting_engine_runner" in joined:
            if "--run-root" not in cmd:
                raise RuntimeError("v2 runner command missing --run-root")
            idx = cmd.index("--run-root")
            run_root = Path(cmd[idx + 1]).resolve()
            return run_root / "fake-nesting-v2-run"
        raise RuntimeError(f"unknown runner command: {joined}")

    def _write_success_output(self) -> None:
        self._run_dir.mkdir(parents=True, exist_ok=True)
        (self._run_dir / "solver_stdout.log").write_text("stdout\n", encoding="utf-8")
        (self._run_dir / "solver_stderr.log").write_text("", encoding="utf-8")
        (self._run_dir / "runner_meta.json").write_text(
            json.dumps({"return_code": 0}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (self._run_dir / "run.log").write_text("run summary\n", encoding="utf-8")

        joined = " ".join(self.cmd)
        if "vrs_nesting.runner.vrs_solver_runner" in joined:
            solver_output = {
                "contract_version": "v1",
                "status": "ok",
                "placements": [
                    {
                        "instance_id": "part-rev-1:0",
                        "part_id": "part-rev-1",
                        "sheet_index": 0,
                        "x": 10.0,
                        "y": 20.0,
                        "rotation_deg": 0,
                    }
                ],
                "unplaced": [
                    {
                        "instance_id": "part-rev-1:1",
                        "part_id": "part-rev-1",
                        "reason": "TIME_LIMIT_EXCEEDED",
                    }
                ],
            }
            (self._run_dir / "solver_output.json").write_text(
                json.dumps(solver_output, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return

        nesting_output = {
            "version": "nesting_engine_v2",
            "seed": 7,
            "solver_version": "fake-v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "part-rev-1",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 10.0,
                    "y_mm": 20.0,
                    "rotation_deg": 0,
                }
            ],
            "unplaced": [
                {
                    "part_id": "part-rev-1",
                    "instance": 1,
                    "reason": "TIME_LIMIT_EXCEEDED",
                }
            ],
            "objective": {
                "sheets_used": 1,
                "utilization_pct": 12.5,
                "remnant_value_ppm": 500000,
                "remnant_area_score_ppm": 200000,
                "remnant_compactness_score_ppm": 200000,
                "remnant_min_width_score_ppm": 100000,
            },
            "meta": {
                "determinism_hash": "fake-hash",
            },
        }
        (self._run_dir / "nesting_output.json").write_text(
            json.dumps(nesting_output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def poll(self) -> int | None:
        if self.returncode is not None:
            return self.returncode
        if self._poll_calls == 0:
            self._poll_calls += 1
            return None
        self._write_success_output()
        self.returncode = 0
        return self.returncode

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
        return self.returncode

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        _ = timeout
        if self.returncode is None:
            self._write_success_output()
            self.returncode = 0
        return (f"{self._run_dir}\n", "")


class PopenFactory:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], stdout: Any, stderr: Any, text: bool) -> FakePopen:
        _ = (stdout, stderr, text)
        self.calls.append(list(cmd))
        return FakePopen(cmd=cmd)


def _settings(temp_root: Path, *, backend: str) -> worker_main.WorkerSettings:
    return worker_main.WorkerSettings(
        supabase_url="https://example.supabase.co",
        supabase_project_ref="proj",
        supabase_access_token="token",
        supabase_service_role_key="service",
        storage_bucket="vrs-nesting",
        worker_id="worker-smoke",
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
        engine_backend=backend,
    )


def _decode_uploaded_json(client: FakeClient, *, bucket: str, object_key: str) -> dict[str, Any]:
    raw = client.uploaded_objects.get(f"{bucket}:{object_key}")
    if raw is None:
        raise RuntimeError(f"missing uploaded object: {bucket}:{object_key}")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"uploaded payload is not json object: {object_key}")
    return payload


def _run_success_case(*, backend: str) -> tuple[FakeClient, PopenFactory, str]:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"smoke_h3_t4_{backend}_"))
    try:
        run_id = f"run-{backend}"
        settings = _settings(temp_dir, backend=backend)
        client = FakeClient(snapshot=_base_snapshot())
        popen_factory = PopenFactory()

        item = {
            "id": f"queue-{backend}",
            "run_id": run_id,
            "lease_token": "lease-token",
            "attempts": 1,
            "max_attempts": 1,
        }

        with (
            patch.object(worker_main.subprocess, "Popen", side_effect=popen_factory),
            patch.object(worker_main.time, "sleep", return_value=None),
            patch.object(worker_main, "persist_sheet_svg_artifacts", return_value=[]),
            patch.object(worker_main, "persist_sheet_dxf_artifacts", return_value=[]),
            patch.object(worker_main, "_sync_run_log_artifact", return_value=0),
            patch.object(worker_main, "_upload_run_artifacts", return_value=None),
        ):
            worker_main._process_queue_item(client, settings, item)

        if len(client.done_calls) != 1:
            raise RuntimeError(f"backend={backend}: expected done call")
        if len(client.replaced_projection) != 1:
            raise RuntimeError(f"backend={backend}: projection was not replaced")
        if len(popen_factory.calls) != 1:
            raise RuntimeError(f"backend={backend}: expected one subprocess call")

        runner_cmd = " ".join(popen_factory.calls[0])
        return client, popen_factory, runner_cmd
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _assert_v1_default_path() -> None:
    if worker_main._resolve_worker_engine_backend("") != worker_main.ENGINE_BACKEND_SPARROW_V1:
        raise RuntimeError("default backend resolution mismatch")

    client, _factory, runner_cmd = _run_success_case(backend=worker_main.ENGINE_BACKEND_SPARROW_V1)

    if "vrs_nesting.runner.vrs_solver_runner" not in runner_cmd:
        raise RuntimeError(f"v1 default runner mismatch: {runner_cmd}")

    solver_input = _decode_uploaded_json(
        client,
        bucket="vrs-nesting",
        object_key="runs/run-sparrow_v1/inputs/solver_input_snapshot.json",
    )
    if solver_input.get("contract_version") != "v1":
        raise RuntimeError("v1 canonical solver_input contract mismatch")

    engine_meta = _decode_uploaded_json(
        client,
        bucket="vrs-nesting",
        object_key="runs/run-sparrow_v1/artifacts/engine_meta.json",
    )
    if engine_meta.get("engine_backend") != "sparrow_v1":
        raise RuntimeError(f"v1 engine_meta backend mismatch: {engine_meta}")
    if engine_meta.get("solver_runner_module") != "vrs_nesting.runner.vrs_solver_runner":
        raise RuntimeError(f"v1 engine_meta runner mismatch: {engine_meta}")


def _assert_v2_runtime_path() -> None:
    client, _factory, runner_cmd = _run_success_case(backend=worker_main.ENGINE_BACKEND_NESTING_V2)

    if "vrs_nesting.runner.nesting_engine_runner" not in runner_cmd:
        raise RuntimeError(f"v2 runner mismatch: {runner_cmd}")

    solver_input = _decode_uploaded_json(
        client,
        bucket="vrs-nesting",
        object_key="runs/run-nesting_engine_v2/inputs/solver_input_snapshot.json",
    )
    if solver_input.get("version") != "nesting_engine_v2":
        raise RuntimeError("v2 canonical solver_input version mismatch")

    engine_meta = _decode_uploaded_json(
        client,
        bucket="vrs-nesting",
        object_key="runs/run-nesting_engine_v2/artifacts/engine_meta.json",
    )
    if engine_meta.get("engine_backend") != "nesting_engine_v2":
        raise RuntimeError(f"v2 engine_meta backend mismatch: {engine_meta}")
    if engine_meta.get("solver_runner_module") != "vrs_nesting.runner.nesting_engine_runner":
        raise RuntimeError(f"v2 engine_meta runner mismatch: {engine_meta}")

    projection = client.replaced_projection[0]
    if len(projection["placements"]) != 1 or len(projection["unplaced"]) != 1:
        raise RuntimeError(f"v2 projection rows mismatch: {projection}")


def _assert_invalid_backend_failfast() -> None:
    try:
        worker_main._resolve_worker_engine_backend("invalid_backend")
    except worker_main.WorkerSettingsError:
        pass
    else:
        raise RuntimeError("invalid backend env value should fail fast")

    temp_dir = Path(tempfile.mkdtemp(prefix="smoke_h3_t4_invalid_"))
    try:
        run_id = "run-invalid"
        settings = _settings(temp_dir, backend="invalid_backend")
        client = FakeClient(snapshot=_base_snapshot())

        item = {
            "id": "queue-invalid",
            "run_id": run_id,
            "lease_token": "lease-token",
            "attempts": 1,
            "max_attempts": 1,
        }

        with (
            patch.object(worker_main.time, "sleep", return_value=None),
            patch.object(worker_main, "persist_sheet_svg_artifacts", return_value=[]),
            patch.object(worker_main, "persist_sheet_dxf_artifacts", return_value=[]),
            patch.object(worker_main, "_sync_run_log_artifact", return_value=0),
            patch.object(worker_main, "_upload_run_artifacts", return_value=None),
        ):
            try:
                worker_main._process_queue_item(client, settings, item)
            except worker_main.WorkerError as exc:
                if "unsupported worker engine backend" not in str(exc):
                    raise RuntimeError(f"unexpected invalid backend error: {exc}") from exc
            else:
                raise RuntimeError("invalid backend should raise WorkerError")

        if len(client.failed_calls) != 1:
            raise RuntimeError("invalid backend should mark run as failed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    _assert_v1_default_path()
    _assert_v2_runtime_path()
    _assert_invalid_backend_failfast()

    print("PASS: H3-Quality-T4 worker dual-engine runtime bridge smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
