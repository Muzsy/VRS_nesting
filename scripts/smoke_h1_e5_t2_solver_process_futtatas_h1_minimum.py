#!/usr/bin/env python3
"""H1-E5-T2 smoke: canonical solver process path in worker."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import worker.main as worker_main  # noqa: E402


def _base_snapshot() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {"project_id": "p1", "project_name": "Project One"},
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
        },
    }


class FakeClient:
    def __init__(self, *, snapshot: dict[str, Any], run_status: str, heartbeat_ok: bool) -> None:
        self._snapshot = snapshot
        self._run_status = run_status
        self._heartbeat_ok = heartbeat_ok
        self.marked_running = 0
        self.uploaded_inputs: list[str] = []
        self.snapshot_hashes: list[str] = []
        self.registered_artifacts: list[dict[str, Any]] = []
        self.replaced_projection: list[dict[str, Any]] = []
        self.done_calls: list[dict[str, Any]] = []
        self.failed_calls: list[dict[str, Any]] = []
        self.cancelled_calls: list[dict[str, Any]] = []
        self.requeue_calls: list[dict[str, Any]] = []

    def mark_run_running(self, run_id: str) -> None:
        self.marked_running += 1

    def fetch_run_snapshot(self, run_id: str) -> dict[str, Any]:
        row = dict(self._snapshot)
        row["snapshot_status"] = "ready"
        return row

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        self.uploaded_inputs.append(object_key)

    def set_run_input_snapshot_hash(self, *, run_id: str, snapshot_hash: str) -> None:
        self.snapshot_hashes.append(snapshot_hash)

    def register_run_artifact_raw(self, **kwargs: Any) -> None:
        self.registered_artifacts.append(dict(kwargs))

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
        return self._run_status

    def heartbeat_queue_item(self, *, queue_id: str, worker_id: str, lease_token: str) -> bool:
        return self._heartbeat_ok

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
    def __init__(self, *, cmd: list[str], scenario: str, run_dir: Path) -> None:
        self.cmd = cmd
        self._scenario = scenario
        self._run_dir = run_dir
        self.returncode: int | None = None
        self._poll_calls = 0

    def _ensure_success_output(self) -> None:
        self._run_dir.mkdir(parents=True, exist_ok=True)
        output = {
            "contract_version": "v1",
            "status": "ok",
            "placements": [
                {
                    "instance_id": "inst-1",
                    "part_id": "part-rev-1",
                    "sheet_index": 0,
                    "x": 10.0,
                    "y": 20.0,
                    "rotation_deg": 0,
                }
            ],
            "unplaced": [
                {
                    "instance_id": "inst-2",
                    "part_id": "part-rev-1",
                    "reason": "PART_NEVER_FITS_STOCK",
                }
            ],
        }
        (self._run_dir / "solver_output.json").write_text(
            worker_main.json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def poll(self) -> int | None:
        if self.returncode is not None:
            return self.returncode

        if self._scenario == "success":
            if self._poll_calls == 0:
                self._poll_calls += 1
                return None
            self._ensure_success_output()
            self.returncode = 0
            return self.returncode

        if self._scenario == "failure":
            if self._poll_calls == 0:
                self._poll_calls += 1
                return None
            self.returncode = 2
            return self.returncode

        if self._scenario in {"cancel", "lease_lost", "timeout"}:
            return None

        raise RuntimeError(f"unknown scenario: {self._scenario}")

    def terminate(self) -> None:
        if self.returncode is None:
            self.returncode = -15

    def kill(self) -> None:
        if self.returncode is None:
            self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        if self.returncode is None:
            if self._scenario == "success":
                self._ensure_success_output()
                self.returncode = 0
            elif self._scenario == "failure":
                self.returncode = 2
            else:
                self.returncode = -15

        if self.returncode == 0:
            return (f"{self._run_dir}\n", "")
        return ("", "runner failed")


class PopenFactory:
    def __init__(self, *, scenario: str) -> None:
        self._scenario = scenario
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], stdout: Any, stderr: Any, text: bool) -> FakePopen:
        self.calls.append(list(cmd))
        run_dir = Path(".")
        if "--run-dir" in cmd:
            idx = cmd.index("--run-dir")
            if idx + 1 < len(cmd):
                run_dir = Path(cmd[idx + 1]).resolve()
        return FakePopen(cmd=list(cmd), scenario=self._scenario, run_dir=run_dir)


class SteppingMonotonic:
    def __init__(self, *, start: float = 0.0, step: float = 31.0) -> None:
        self._value = start
        self._step = step

    def __call__(self) -> float:
        self._value += self._step
        return self._value


def _settings(temp_root: Path) -> worker_main.WorkerSettings:
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
    )


def _assert_runner_cmd(call: list[str]) -> None:
    joined = " ".join(call)
    if "vrs_nesting.runner.vrs_solver_runner" not in joined:
        raise RuntimeError(f"runner module not called: {joined}")
    if "dxf-run" in joined:
        raise RuntimeError(f"legacy dxf-run command detected: {joined}")


def _run_case(*, scenario: str, expected_exception: type[BaseException] | None, run_status: str, heartbeat_ok: bool) -> FakeClient:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"smoke_h1_e5_t2_{scenario}_"))
    try:
        settings = _settings(temp_dir)
        run_id = f"run-{scenario}"
        popen_factory = PopenFactory(scenario=scenario)
        client = FakeClient(snapshot=_base_snapshot(), run_status=run_status, heartbeat_ok=heartbeat_ok)

        item = {
            "id": f"queue-{scenario}",
            "run_id": run_id,
            "lease_token": "lease-token",
            "attempts": 1,
            "max_attempts": 1,
        }

        monotonic_patch = patch.object(worker_main.time, "monotonic", side_effect=SteppingMonotonic())
        if scenario != "timeout":
            monotonic_patch = patch.object(worker_main.time, "monotonic", wraps=worker_main.time.monotonic)

        with (
            patch.object(worker_main.subprocess, "Popen", side_effect=popen_factory),
            patch.object(worker_main.time, "sleep", return_value=None),
            patch.object(worker_main, "_upload_run_artifacts", return_value=None),
            patch.object(worker_main, "persist_sheet_svg_artifacts", return_value=[]),
            patch.object(worker_main, "persist_sheet_dxf_artifacts", return_value=[]),
            patch.object(worker_main, "_sync_run_log_artifact", return_value=0),
            monotonic_patch,
        ):
            caught: BaseException | None = None
            try:
                worker_main._process_queue_item(client, settings, item)
            except BaseException as exc:  # noqa: BLE001
                caught = exc

        if expected_exception is None:
            if caught is not None:
                raise RuntimeError(f"{scenario}: unexpected exception {type(caught).__name__}: {caught}")
        else:
            if not isinstance(caught, expected_exception):
                raise RuntimeError(
                    f"{scenario}: expected {expected_exception.__name__}, got {type(caught).__name__ if caught else 'None'}"
                )

        if not popen_factory.calls:
            raise RuntimeError(f"{scenario}: runner command not executed")
        _assert_runner_cmd(popen_factory.calls[0])
        return client
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    success = _run_case(scenario="success", expected_exception=None, run_status="running", heartbeat_ok=True)
    if len(success.done_calls) != 1:
        raise RuntimeError("success case: expected one complete_run_done_and_dequeue call")
    done = success.done_calls[0]
    if done["placements_count"] != 1 or done["unplaced_count"] != 1 or done["sheet_count"] != 1:
        raise RuntimeError(f"success metrics mismatch: {done}")

    failure = _run_case(scenario="failure", expected_exception=worker_main.WorkerError, run_status="running", heartbeat_ok=True)
    if len(failure.failed_calls) != 1:
        raise RuntimeError("failure case: expected failed completion")

    timeout_case = _run_case(
        scenario="timeout",
        expected_exception=worker_main.WorkerTimeoutError,
        run_status="running",
        heartbeat_ok=True,
    )
    if len(timeout_case.failed_calls) != 1:
        raise RuntimeError("timeout case: expected failed completion")

    cancel_case = _run_case(
        scenario="cancel",
        expected_exception=worker_main.WorkerCancelledError,
        run_status="cancelled",
        heartbeat_ok=True,
    )
    if len(cancel_case.cancelled_calls) != 1:
        raise RuntimeError("cancel case: expected cancelled completion")

    lease_case = _run_case(
        scenario="lease_lost",
        expected_exception=worker_main.WorkerLeaseLostError,
        run_status="running",
        heartbeat_ok=False,
    )
    if lease_case.done_calls or lease_case.failed_calls or lease_case.cancelled_calls or lease_case.requeue_calls:
        raise RuntimeError("lease_lost case: terminal state should not be written")

    print("PASS: H1-E5-T2 solver process canonical worker path smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
