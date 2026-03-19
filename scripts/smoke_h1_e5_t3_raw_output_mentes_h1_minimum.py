#!/usr/bin/env python3
"""H1-E5-T3 smoke: canonical raw artifact persistence boundary."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.raw_output_artifacts import persist_raw_output_artifacts, persisted_raw_artifacts_json


class FakeRawArtifactGateway:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.rows: dict[tuple[str, str], dict[str, str]] = {}

    def upload_object(self, *, bucket: str, object_key: str, payload: bytes) -> None:
        self.uploaded[f"{bucket}:{object_key}"] = payload

    def register_artifact(
        self,
        *,
        run_id: str,
        artifact_kind: str,
        storage_bucket: str,
        storage_path: str,
        metadata_json: dict,
    ) -> None:
        self.rows[(run_id, storage_path)] = {
            "artifact_kind": artifact_kind,
            "storage_bucket": storage_bucket,
            "legacy_artifact_type": str(metadata_json.get("legacy_artifact_type") or ""),
        }


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _expected_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_path_prefix(path: str, *, project_id: str, run_id: str) -> None:
    expected_prefix = f"projects/{project_id}/runs/{run_id}/"
    if not path.startswith(expected_prefix):
        raise RuntimeError(f"invalid canonical prefix: {path}")


def _assert_contains(records: list, filename: str) -> dict:
    for item in records:
        if item.filename == filename:
            return {
                "artifact_kind": item.artifact_kind,
                "storage_path": item.storage_path,
                "content_sha256": item.content_sha256,
            }
    raise RuntimeError(f"missing artifact record: {filename}")


def _prepare_success_run_dir(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    _write(run_dir / "solver_stdout.log", "solver stdout line\n")
    _write(run_dir / "solver_stderr.log", "")
    _write(
        run_dir / "solver_output.json",
        json.dumps(
            {
                "contract_version": "v1",
                "status": "ok",
                "placements": [],
                "unplaced": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    _write(run_dir / "runner_meta.json", json.dumps({"return_code": 0}, ensure_ascii=False) + "\n")
    _write(run_dir / "run.log", "runner summary\n")


def _prepare_failure_run_dir(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    _write(run_dir / "solver_stdout.log", "partial stdout\n")
    _write(run_dir / "solver_stderr.log", "solver failed\n")
    _write(run_dir / "runner_meta.json", json.dumps({"return_code": 2}, ensure_ascii=False) + "\n")
    _write(run_dir / "run.log", "failed summary\n")


def _prepare_timeout_run_dir(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    _write(run_dir / "solver_stderr.log", "timeout\n")
    _write(run_dir / "runner_meta.json", json.dumps({"return_code": 124}, ensure_ascii=False) + "\n")
    _write(run_dir / "run.log", "timed out\n")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="smoke_h1_e5_t3_"))
    try:
        project_id = "project-123"

        success_gateway = FakeRawArtifactGateway()
        success_run_id = "run-success"
        success_dir = tmp / success_run_id
        _prepare_success_run_dir(success_dir)

        first = persist_raw_output_artifacts(
            run_dir=success_dir,
            project_id=project_id,
            run_id=success_run_id,
            storage_bucket="run-artifacts",
            upload_object=success_gateway.upload_object,
            register_artifact=success_gateway.register_artifact,
        )
        second = persist_raw_output_artifacts(
            run_dir=success_dir,
            project_id=project_id,
            run_id=success_run_id,
            storage_bucket="run-artifacts",
            upload_object=success_gateway.upload_object,
            register_artifact=success_gateway.register_artifact,
        )

        if persisted_raw_artifacts_json(first) != persisted_raw_artifacts_json(second):
            raise RuntimeError("idempotent hash/path mismatch on repeated persistence")

        if len(first) != 5:
            raise RuntimeError(f"success branch should persist 5 raw artifacts, got {len(first)}")

        solver_output = _assert_contains(first, "solver_output.json")
        if solver_output["artifact_kind"] != "solver_output":
            raise RuntimeError(f"solver_output kind mismatch: {solver_output}")
        _assert_path_prefix(solver_output["storage_path"], project_id=project_id, run_id=success_run_id)
        if not solver_output["storage_path"].endswith(".json"):
            raise RuntimeError(f"solver_output extension mismatch: {solver_output['storage_path']}")
        if solver_output["content_sha256"] != _expected_hash(success_dir / "solver_output.json"):
            raise RuntimeError("solver_output sha mismatch")

        run_log = _assert_contains(first, "run.log")
        if run_log["artifact_kind"] != "log":
            raise RuntimeError(f"run.log kind mismatch: {run_log}")
        _assert_path_prefix(run_log["storage_path"], project_id=project_id, run_id=success_run_id)

        for item in first:
            _assert_path_prefix(item.storage_path, project_id=project_id, run_id=success_run_id)

        failure_gateway = FakeRawArtifactGateway()
        failure_run_id = "run-failure"
        failure_dir = tmp / failure_run_id
        _prepare_failure_run_dir(failure_dir)
        failure_records = persist_raw_output_artifacts(
            run_dir=failure_dir,
            project_id=project_id,
            run_id=failure_run_id,
            storage_bucket="run-artifacts",
            upload_object=failure_gateway.upload_object,
            register_artifact=failure_gateway.register_artifact,
        )
        if any(item.filename == "solver_output.json" for item in failure_records):
            raise RuntimeError("failure branch should not persist missing solver_output.json")
        if len(failure_records) < 3:
            raise RuntimeError("failure branch should keep raw evidence (stdout/stderr/meta/run.log)")

        timeout_gateway = FakeRawArtifactGateway()
        timeout_run_id = "run-timeout"
        timeout_dir = tmp / timeout_run_id
        _prepare_timeout_run_dir(timeout_dir)
        timeout_records = persist_raw_output_artifacts(
            run_dir=timeout_dir,
            project_id=project_id,
            run_id=timeout_run_id,
            storage_bucket="run-artifacts",
            upload_object=timeout_gateway.upload_object,
            register_artifact=timeout_gateway.register_artifact,
        )
        if len(timeout_records) < 2:
            raise RuntimeError("timeout branch should keep raw evidence (stderr/meta/log)")

        print("PASS: H1-E5-T3 canonical raw output persistence smoke")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
