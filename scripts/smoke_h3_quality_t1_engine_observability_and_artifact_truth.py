#!/usr/bin/env python3
"""Smoke for H3 quality task: artifact truth, viewer fallback, trial summary evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser  # noqa: E402
import api.routes.runs as runs_route  # noqa: E402
from api.supabase_client import SupabaseHTTPError  # noqa: E402


class _FakeSupabase:
    def __init__(self, blobs_by_key: dict[str, bytes]) -> None:
        self._blobs = blobs_by_key
        self.requested_keys: list[str] = []

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int = 300,
    ) -> dict[str, Any]:
        del access_token, bucket, expires_in
        self.requested_keys.append(object_key)
        if object_key not in self._blobs:
            raise SupabaseHTTPError(f"missing blob for object_key={object_key}")
        return {"download_url": f"signed://{object_key}"}

    def download_signed_object(self, *, signed_url: str) -> bytes:
        key = str(signed_url).replace("signed://", "", 1)
        if key not in self._blobs:
            raise SupabaseHTTPError(f"missing blob for signed_url={signed_url}")
        return self._blobs[key]


def _assert_contains(text: str, needle: str, *, what: str) -> None:
    if needle not in text:
        raise RuntimeError(f"{what} missing expected snippet: {needle}")


def _assert_worker_canonical_truth() -> None:
    worker_text = (ROOT / "worker" / "main.py").read_text(encoding="utf-8")
    _assert_contains(
        worker_text,
        'solver_input_storage_key = f"runs/{run_id}/inputs/solver_input_snapshot.json"',
        what="worker canonical input registration",
    )
    _assert_contains(worker_text, 'artifact_type="solver_input"', what="worker canonical input registration")
    _assert_contains(worker_text, 'filename="solver_input.json"', what="worker canonical input registration")
    _assert_contains(worker_text, '"legacy_artifact_type": "engine_meta"', what="worker engine meta registration")
    _assert_contains(worker_text, '"engine_backend": engine_backend', what="worker engine meta payload")
    _assert_contains(
        worker_text,
        '"requested_engine_profile": profile_resolution.requested_engine_profile',
        what="worker engine meta payload",
    )
    _assert_contains(
        worker_text,
        '"effective_engine_profile": profile_resolution.effective_engine_profile',
        what="worker engine meta payload",
    )
    _assert_contains(
        worker_text,
        '"nesting_engine_cli_args": list(profile_resolution.nesting_engine_cli_args)',
        what="worker engine meta payload",
    )


def _as_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return dict(model.model_dump())
    if hasattr(model, "dict"):
        return dict(model.dict())
    raise RuntimeError("unexpected model type")


def _run_viewer_data_case(
    *,
    run_id: UUID,
    project_id: UUID,
    user: AuthenticatedUser,
    supabase: _FakeSupabase,
    artifact_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    settings = SimpleNamespace(storage_bucket="artifacts", signed_url_ttl_s=120)

    old_ensure = runs_route._ensure_project_access
    old_fetch_run = runs_route._fetch_run_row
    old_fetch_artifacts = runs_route._fetch_run_artifacts
    try:
        runs_route._ensure_project_access = lambda **kwargs: None  # type: ignore[assignment]
        runs_route._fetch_run_row = lambda **kwargs: {"status": "done", "sheet_count": 0}  # type: ignore[assignment]
        runs_route._fetch_run_artifacts = lambda **kwargs: artifact_rows  # type: ignore[assignment]

        response = runs_route.get_viewer_data(
            project_id=project_id,
            run_id=run_id,
            user=user,
            supabase=supabase,  # type: ignore[arg-type]
            settings=settings,  # type: ignore[arg-type]
        )
    finally:
        runs_route._ensure_project_access = old_ensure  # type: ignore[assignment]
        runs_route._fetch_run_row = old_fetch_run  # type: ignore[assignment]
        runs_route._fetch_run_artifacts = old_fetch_artifacts  # type: ignore[assignment]

    return _as_dict(response)


def _assert_viewer_canonical_and_fallback() -> None:
    project_id = UUID("11111111-1111-1111-1111-111111111111")
    run_id = UUID("22222222-2222-2222-2222-222222222222")
    user = AuthenticatedUser(id="user_1", access_token="token_1")

    solver_input_payload = {
        "contract_version": "v1",
        "stocks": [
            {
                "id": "SHEET_A",
                "quantity": 1,
                "outer_points": [[0, 0], [1000, 0], [1000, 500], [0, 500]],
                "holes_points": [],
            }
        ],
        "parts": [{"id": "P1", "width": 200, "height": 100, "quantity": 1}],
    }
    solver_output_payload = {
        "placements": [
            {"instance_id": "P1#1", "part_id": "P1", "sheet_index": 0, "x": 0, "y": 0, "rotation_deg": 0}
        ],
        "unplaced": [],
    }

    canonical_solver_input_key = "runs/r1/inputs/solver_input_snapshot.json"
    solver_output_key = "runs/r1/out/solver_output.json"
    fallback_snapshot_key = f"runs/{run_id}/inputs/solver_input_snapshot.json"

    canonical_rows = [
        {
            "id": "a_solver_output",
            "artifact_type": "solver_output",
            "filename": "solver_output.json",
            "storage_key": solver_output_key,
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
        {
            "id": "a_solver_input",
            "artifact_type": "solver_input",
            "filename": "solver_input.json",
            "storage_key": canonical_solver_input_key,
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
    ]
    canonical_supabase = _FakeSupabase(
        blobs_by_key={
            solver_output_key: (json.dumps(solver_output_payload) + "\n").encode("utf-8"),
            canonical_solver_input_key: (json.dumps(solver_input_payload) + "\n").encode("utf-8"),
        }
    )
    canonical = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=canonical_supabase,
        artifact_rows=canonical_rows,
    )
    if fallback_snapshot_key in canonical_supabase.requested_keys:
        raise RuntimeError("viewer fetched snapshot fallback despite canonical solver_input artifact presence")
    sheets = canonical.get("sheets", [])
    if not isinstance(sheets, list) or not sheets:
        raise RuntimeError("viewer returned no sheets in canonical case")
    sheet0 = sheets[0]
    if float(sheet0.get("width_mm") or 0.0) != 1000.0 or float(sheet0.get("height_mm") or 0.0) != 500.0:
        raise RuntimeError(f"viewer canonical sheet size mismatch: {sheet0}")

    fallback_rows = [
        {
            "id": "b_solver_output",
            "artifact_type": "solver_output",
            "filename": "solver_output.json",
            "storage_key": solver_output_key,
            "storage_bucket": "artifacts",
            "sheet_index": None,
        }
    ]
    fallback_supabase = _FakeSupabase(
        blobs_by_key={
            solver_output_key: (json.dumps(solver_output_payload) + "\n").encode("utf-8"),
            fallback_snapshot_key: (json.dumps(solver_input_payload) + "\n").encode("utf-8"),
        }
    )
    fallback_first = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=fallback_supabase,
        artifact_rows=fallback_rows,
    )
    fallback_second = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=fallback_supabase,
        artifact_rows=fallback_rows,
    )
    if fallback_snapshot_key not in fallback_supabase.requested_keys:
        raise RuntimeError("viewer did not use snapshot fallback when solver_input artifact was missing")
    fallback_sheets_1 = fallback_first.get("sheets", [])
    fallback_sheets_2 = fallback_second.get("sheets", [])
    if fallback_sheets_1 != fallback_sheets_2:
        raise RuntimeError("viewer fallback behavior is not deterministic across repeated calls")
    if not fallback_sheets_1:
        raise RuntimeError("viewer fallback returned no sheets")
    fb0 = fallback_sheets_1[0]
    if float(fb0.get("width_mm") or 0.0) != 1000.0 or float(fb0.get("height_mm") or 0.0) != 500.0:
        raise RuntimeError(f"viewer fallback sheet size mismatch: {fb0}")


def _assert_trial_summary_quality_fields() -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "smoke_trial_run_tool_cli_core.py")]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "trial smoke failed while validating summary quality fields; "
            f"exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


def main() -> int:
    _assert_worker_canonical_truth()
    _assert_viewer_canonical_and_fallback()
    _assert_trial_summary_quality_fields()
    print("PASS smoke_h3_quality_t1_engine_observability_and_artifact_truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
