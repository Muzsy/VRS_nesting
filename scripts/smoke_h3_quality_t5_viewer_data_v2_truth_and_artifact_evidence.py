#!/usr/bin/env python3
"""Smoke for H3 quality task T5: viewer-data v2 truth and artifact evidence."""

from __future__ import annotations

import json
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


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_v1_legacy_still_works() -> None:
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    run_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    user = AuthenticatedUser(id="user_legacy", access_token="token_legacy")

    solver_input_payload = {
        "contract_version": "v1",
        "stocks": [
            {
                "id": "sheet-v1",
                "quantity": 1,
                "width": 1000.0,
                "height": 500.0,
            }
        ],
        "parts": [
            {
                "id": "P1",
                "width": 200.0,
                "height": 100.0,
                "quantity": 1,
            }
        ],
    }
    solver_output_payload = {
        "placements": [
            {
                "instance_id": "P1__0001",
                "part_id": "P1",
                "sheet_index": 0,
                "x": 10.0,
                "y": 20.0,
                "rotation_deg": 90.0,
            }
        ],
        "unplaced": [],
    }

    rows = [
        {
            "id": "legacy_output",
            "artifact_type": "solver_output",
            "filename": "solver_output.json",
            "storage_key": "runs/legacy/artifacts/solver_output.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
        {
            "id": "legacy_input",
            "artifact_type": "solver_input",
            "filename": "solver_input.json",
            "storage_key": "runs/legacy/inputs/solver_input_snapshot.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
    ]
    supabase = _FakeSupabase(
        blobs_by_key={
            "runs/legacy/artifacts/solver_output.json": (json.dumps(solver_output_payload) + "\n").encode("utf-8"),
            "runs/legacy/inputs/solver_input_snapshot.json": (json.dumps(solver_input_payload) + "\n").encode("utf-8"),
        }
    )

    response = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=supabase,
        artifact_rows=rows,
    )

    _assert(response.get("output_artifact_kind") == "solver_output", "v1 should pick solver_output truth")
    _assert(response.get("input_artifact_source") == "artifact", "v1 should read canonical solver_input artifact")
    placements = response.get("placements", [])
    _assert(isinstance(placements, list) and len(placements) == 1, "v1 should have one placement")
    p0 = placements[0]
    _assert(p0.get("instance_id") == "P1__0001", "v1 instance_id changed unexpectedly")
    _assert(float(p0.get("width_mm") or 0.0) == 200.0, "v1 width parse mismatch")
    _assert(float(p0.get("height_mm") or 0.0) == 100.0, "v1 height parse mismatch")

    sheets = response.get("sheets", [])
    _assert(isinstance(sheets, list) and len(sheets) >= 1, "v1 should return sheets")
    sheet0 = sheets[0]
    _assert(float(sheet0.get("width_mm") or 0.0) == 1000.0, "v1 sheet width mismatch")
    _assert(float(sheet0.get("height_mm") or 0.0) == 500.0, "v1 sheet height mismatch")
    _assert(int(sheet0.get("placements_count") or 0) == 1, "v1 placements_count mismatch")


def _assert_v2_truth_and_evidence() -> None:
    project_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    run_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    user = AuthenticatedUser(id="user_v2", access_token="token_v2")

    v2_input_payload = {
        "version": "nesting_engine_v2",
        "seed": 7,
        "time_limit_sec": 60,
        "sheet": {
            "width_mm": 1200.0,
            "height_mm": 600.0,
            "kerf_mm": 1.0,
            "spacing_mm": 2.0,
            "margin_mm": 5.0,
        },
        "parts": [
            {
                "id": "part-v2",
                "quantity": 2,
                "allowed_rotations_deg": [0, 90],
                "outer_points_mm": [[0.0, 0.0], [80.0, 0.0], [80.0, 40.0], [0.0, 40.0]],
                "holes_points_mm": [],
            }
        ],
    }
    v2_output_payload = {
        "version": "nesting_engine_v2",
        "seed": 7,
        "solver_version": "fake-v2",
        "status": "partial",
        "sheets_used": 2,
        "placements": [
            {
                "part_id": "part-v2",
                "instance": 0,
                "sheet": 0,
                "x_mm": 100.0,
                "y_mm": 200.0,
                "rotation_deg": 90,
            }
        ],
        "unplaced": [
            {
                "part_id": "part-v2",
                "instance": 1,
                "reason": "TIME_LIMIT_EXCEEDED",
            }
        ],
        "objective": {
            "sheets_used": 2,
            "utilization_pct": 33.3,
        },
    }
    conflicting_legacy_output_payload = {
        "placements": [
            {
                "instance_id": "wrong-legacy",
                "part_id": "part-v2",
                "sheet_index": 0,
                "x": 0.0,
                "y": 0.0,
                "rotation_deg": 0.0,
            }
        ],
        "unplaced": [],
    }
    engine_meta_payload = {
        "engine_backend": "nesting_engine_v2",
        "engine_contract_version": "nesting_engine_v2",
        "engine_profile": "default",
        "solver_runner_module": "vrs_nesting.runner.nesting_engine_runner",
    }

    rows = [
        {
            "id": "v2_output_primary",
            "artifact_type": "solver_output",
            "filename": "nesting_output.json",
            "storage_key": "runs/v2/artifacts/nesting_output.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
        {
            "id": "v2_output_legacy",
            "artifact_type": "solver_output",
            "filename": "solver_output.json",
            "storage_key": "runs/v2/artifacts/solver_output.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
        {
            "id": "v2_input",
            "artifact_type": "solver_input",
            "filename": "solver_input.json",
            "storage_key": "runs/v2/inputs/solver_input_snapshot.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
        {
            "id": "v2_engine_meta",
            "artifact_type": "engine_meta",
            "filename": "engine_meta.json",
            "storage_key": "runs/v2/artifacts/engine_meta.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        },
    ]
    supabase = _FakeSupabase(
        blobs_by_key={
            "runs/v2/artifacts/nesting_output.json": (json.dumps(v2_output_payload) + "\n").encode("utf-8"),
            "runs/v2/artifacts/solver_output.json": (json.dumps(conflicting_legacy_output_payload) + "\n").encode("utf-8"),
            "runs/v2/inputs/solver_input_snapshot.json": (json.dumps(v2_input_payload) + "\n").encode("utf-8"),
            "runs/v2/artifacts/engine_meta.json": (json.dumps(engine_meta_payload) + "\n").encode("utf-8"),
        }
    )

    response_first = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=supabase,
        artifact_rows=rows,
    )
    response_second = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=supabase,
        artifact_rows=rows,
    )

    _assert(response_first == response_second, "viewer-data v2 response must be deterministic")
    _assert(response_first.get("engine_backend") == "nesting_engine_v2", "missing engine_backend evidence")
    _assert(
        response_first.get("engine_contract_version") == "nesting_engine_v2",
        "missing engine_contract_version evidence",
    )
    _assert(response_first.get("engine_profile") == "default", "missing engine_profile evidence")
    _assert(response_first.get("output_artifact_kind") == "nesting_output", "v2 output truth selection mismatch")
    _assert(response_first.get("output_artifact_filename") == "nesting_output.json", "v2 output filename mismatch")

    placements = response_first.get("placements", [])
    _assert(isinstance(placements, list) and len(placements) == 1, "v2 should return one placement")
    p0 = placements[0]
    _assert(p0.get("instance_id") == "part-v2:0", "v2 instance_id should be part_id:instance")
    _assert(float(p0.get("x") or 0.0) == 100.0, "v2 x parse mismatch")
    _assert(float(p0.get("y") or 0.0) == 200.0, "v2 y parse mismatch")
    _assert(float(p0.get("width_mm") or 0.0) == 80.0, "v2 part bbox width mismatch")
    _assert(float(p0.get("height_mm") or 0.0) == 40.0, "v2 part bbox height mismatch")

    unplaced = response_first.get("unplaced", [])
    _assert(isinstance(unplaced, list) and len(unplaced) == 1, "v2 should return one unplaced instance")
    _assert(unplaced[0].get("instance_id") == "part-v2:1", "v2 unplaced instance_id mismatch")

    sheets = response_first.get("sheets", [])
    _assert(isinstance(sheets, list) and len(sheets) == 2, "v2 sheets should follow sheets_used=2")
    for idx, sheet in enumerate(sheets):
        _assert(int(sheet.get("sheet_index", -1)) == idx, f"v2 sheet index mismatch at {idx}")
        _assert(float(sheet.get("width_mm") or 0.0) == 1200.0, f"v2 sheet width mismatch at {idx}")
        _assert(float(sheet.get("height_mm") or 0.0) == 600.0, f"v2 sheet height mismatch at {idx}")
    _assert(int(sheets[0].get("placements_count") or 0) == 1, "v2 sheet0 placement count mismatch")
    _assert(int(sheets[1].get("placements_count") or 0) == 0, "v2 sheet1 placement count mismatch")


def _assert_snapshot_fallback_still_works() -> None:
    project_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    run_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    user = AuthenticatedUser(id="user_fb", access_token="token_fb")

    solver_input_payload = {
        "contract_version": "v1",
        "stocks": [
            {
                "id": "sheet-fallback",
                "quantity": 1,
                "outer_points": [[0.0, 0.0], [900.0, 0.0], [900.0, 400.0], [0.0, 400.0]],
            }
        ],
        "parts": [
            {
                "id": "PFB",
                "width": 100.0,
                "height": 50.0,
                "quantity": 1,
            }
        ],
    }
    solver_output_payload = {
        "placements": [
            {
                "instance_id": "PFB__0001",
                "part_id": "PFB",
                "sheet_index": 0,
                "x": 1.0,
                "y": 2.0,
                "rotation_deg": 0.0,
            }
        ],
        "unplaced": [],
    }

    snapshot_key = f"runs/{run_id}/inputs/solver_input_snapshot.json"
    rows = [
        {
            "id": "fallback_output",
            "artifact_type": "solver_output",
            "filename": "solver_output.json",
            "storage_key": "runs/fallback/artifacts/solver_output.json",
            "storage_bucket": "artifacts",
            "sheet_index": None,
        }
    ]
    supabase = _FakeSupabase(
        blobs_by_key={
            "runs/fallback/artifacts/solver_output.json": (json.dumps(solver_output_payload) + "\n").encode("utf-8"),
            snapshot_key: (json.dumps(solver_input_payload) + "\n").encode("utf-8"),
        }
    )

    first = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=supabase,
        artifact_rows=rows,
    )
    second = _run_viewer_data_case(
        run_id=run_id,
        project_id=project_id,
        user=user,
        supabase=supabase,
        artifact_rows=rows,
    )

    _assert(first == second, "snapshot fallback path must be deterministic")
    _assert(first.get("input_artifact_source") == "snapshot_fallback", "fallback source evidence mismatch")
    _assert(snapshot_key in supabase.requested_keys, "snapshot fallback key was not requested")


def main() -> int:
    _assert_v1_legacy_still_works()
    _assert_v2_truth_and_evidence()
    _assert_snapshot_fallback_still_works()
    print("PASS smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
