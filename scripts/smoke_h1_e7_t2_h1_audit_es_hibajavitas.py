#!/usr/bin/env python3
"""H1-E7-T2 regression smoke: H1 audit evidence + route fixes."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser
from api.config import Settings
from api.routes import runs as runs_route


@dataclass(frozen=True)
class TaskEvidence:
    code: str
    report_relpath: str


H1_TASK_EVIDENCE: tuple[TaskEvidence, ...] = (
    TaskEvidence("H1-E1-T1", "codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md"),
    TaskEvidence("H1-E1-T2", "codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md"),
    TaskEvidence("H1-E2-T1", "codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md"),
    TaskEvidence("H1-E2-T2", "codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md"),
    TaskEvidence("H1-E2-T3", "codex/reports/web_platform/h1_e2_t3_validation_report_generator.md"),
    TaskEvidence("H1-E2-T4", "codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md"),
    TaskEvidence("H1-E3-T1", "codex/reports/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md"),
    TaskEvidence("H1-E3-T2", "codex/reports/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md"),
    TaskEvidence("H1-E3-T3", "codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md"),
    TaskEvidence("H1-E3-T4", "codex/reports/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md"),
    TaskEvidence("H1-E4-T1", "codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md"),
    TaskEvidence("H1-E4-T2", "codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md"),
    TaskEvidence("H1-E4-T3", "codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md"),
    TaskEvidence("H1-E5-T1", "codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md"),
    TaskEvidence("H1-E5-T2", "codex/reports/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md"),
    TaskEvidence("H1-E5-T3", "codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md"),
    TaskEvidence("H1-E6-T1", "codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md"),
    TaskEvidence("H1-E6-T2", "codex/reports/web_platform/h1_e6_t2_sheet_svg_generator_h1_minimum.md"),
    TaskEvidence("H1-E6-T3", "codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md"),
    TaskEvidence("H1-E7-T1", "codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md"),
)


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _assert_h1_task_evidence_chain() -> None:
    missing_reports: list[str] = []
    missing_verify: list[str] = []
    invalid_report_headers: list[str] = []

    for evidence in H1_TASK_EVIDENCE:
        report_path = ROOT / evidence.report_relpath
        verify_path = report_path.with_suffix(".verify.log")
        if not report_path.is_file():
            missing_reports.append(evidence.code)
            continue
        if not verify_path.is_file():
            missing_verify.append(evidence.code)
        report_header = _first_nonempty_line(report_path.read_text(encoding="utf-8", errors="ignore")).upper()
        if not report_header.startswith("PASS"):
            invalid_report_headers.append(f"{evidence.code}:{report_header or '<empty>'}")

    if missing_reports:
        raise RuntimeError(f"missing H1 reports: {', '.join(missing_reports)}")
    if missing_verify:
        raise RuntimeError(f"missing H1 verify logs: {', '.join(missing_verify)}")
    if invalid_report_headers:
        raise RuntimeError(f"H1 reports without PASS* header: {', '.join(invalid_report_headers)}")


class FakeSupabaseClient:
    def __init__(self, *, project_id: str, owner_user_id: str, run_id: str, run_log_artifact_id: str) -> None:
        self.project_id = project_id
        self.owner_user_id = owner_user_id
        self.run_id = run_id
        self.run_log_artifact_id = run_log_artifact_id
        self.projects: list[dict[str, Any]] = [
            {"id": project_id, "owner_user_id": owner_user_id},
        ]
        self.runs: list[dict[str, Any]] = [
            {
                "id": run_id,
                "project_id": project_id,
                "status": "done",
                "requested_by": owner_user_id,
                "placements_count": 1,
                "unplaced_count": 0,
                "sheet_count": 1,
            }
        ]
        self.run_artifacts: list[dict[str, Any]] = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "run_id": run_id,
                "artifact_kind": "log",
                "storage_path": f"projects/{project_id}/runs/{run_id}/log/stderr.log",
                "metadata_jsonb": {
                    "legacy_artifact_type": "solver_stderr",
                    "filename": "solver_stderr.log",
                },
                "created_at": "2026-03-20T10:00:02+00:00",
            },
            {
                "id": run_log_artifact_id,
                "run_id": run_id,
                "artifact_kind": "log",
                "storage_path": f"projects/{project_id}/runs/{run_id}/log/run.log",
                "metadata_jsonb": {
                    "legacy_artifact_type": "run_log",
                    "filename": "run.log",
                },
                "created_at": "2026-03-20T10:00:01+00:00",
            },
        ]
        self.storage_blobs: dict[str, bytes] = {
            f"projects/{project_id}/runs/{run_id}/log/stderr.log": b"stderr-line-1\nstderr-line-2\n",
            f"projects/{project_id}/runs/{run_id}/log/run.log": b"run-line-1\nrun-line-2\n",
        }

    @staticmethod
    def _eq_match(value: Any, raw_filter: str) -> bool:
        if not raw_filter.startswith("eq."):
            return True
        return str(value) == raw_filter[3:]

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        _ = access_token
        rows: list[dict[str, Any]]
        if table == "app.projects":
            rows = deepcopy(self.projects)
        elif table == "app.nesting_runs":
            rows = deepcopy(self.runs)
        elif table == "app.run_artifacts":
            rows = deepcopy(self.run_artifacts)
        else:
            rows = []

        for key, raw_filter in params.items():
            if key in {"select", "order", "limit", "offset"}:
                continue
            rows = [row for row in rows if self._eq_match(row.get(key), raw_filter)]

        order_clause = params.get("order", "")
        for order_token in reversed([item.strip() for item in order_clause.split(",") if item.strip()]):
            key = order_token.split(".", 1)[0]
            reverse = order_token.endswith(".desc")
            rows.sort(key=lambda item: str(item.get(key) or ""), reverse=reverse)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = params.get("limit")
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]
        return [deepcopy(row) for row in rows]

    def create_signed_download_url(
        self,
        *,
        access_token: str,
        bucket: str,
        object_key: str,
        expires_in: int = 300,
    ) -> dict[str, Any]:
        _ = (access_token, expires_in)
        return {
            "download_url": f"signed://{bucket}/{object_key}",
            "expires_at": "2026-03-20T10:01:00+00:00",
        }

    def download_signed_object(self, *, signed_url: str) -> bytes:
        parsed = urlparse(signed_url)
        key = parsed.path.lstrip("/")
        if key not in self.storage_blobs:
            raise RuntimeError(f"missing fake blob for {key}")
        return self.storage_blobs[key]


def _make_settings() -> Settings:
    return Settings(
        supabase_url="https://fake.supabase.local",
        supabase_anon_key="fake-anon",
        supabase_project_ref="fake-ref",
        supabase_db_password="fake-password",
        database_url="postgres://fake",
        storage_bucket="source-files",
        max_dxf_size_mb=50,
        rate_limit_window_s=60,
        rate_limit_runs_per_window=10,
        rate_limit_bundles_per_window=4,
        rate_limit_upload_urls_per_window=100,
        signed_url_ttl_s=300,
        enable_security_headers=False,
        allowed_origins=("http://localhost:5173",),
    )


def _assert_runs_route_regression_fixes() -> None:
    owner_user_id = "00000000-0000-0000-0000-000000000001"
    project_id = "22222222-2222-2222-2222-222222222222"
    run_id = "33333333-3333-3333-3333-333333333333"
    run_log_artifact_id = "44444444-4444-4444-4444-444444444444"
    fake = FakeSupabaseClient(
        project_id=project_id,
        owner_user_id=owner_user_id,
        run_id=run_id,
        run_log_artifact_id=run_log_artifact_id,
    )
    user = AuthenticatedUser(id=owner_user_id, email="u1@example.com", access_token="token-u1")
    settings = _make_settings()

    original_get_settings = runs_route.get_settings

    def _forbidden_get_settings() -> Settings:
        raise RuntimeError("get_settings() must not be called inside route handler")

    runs_route.get_settings = _forbidden_get_settings
    try:
        run_log = runs_route.get_run_log(
            project_id=UUID(project_id),
            run_id=UUID(run_id),
            offset=0,
            lines=10,
            user=user,
            supabase=fake,  # type: ignore[arg-type]
            settings=settings,
        )
        if [line.text for line in run_log.lines] != ["run-line-1", "run-line-2"]:
            raise RuntimeError("get_run_log did not prefer run.log artifact")

        artifact = runs_route.get_artifact_url(
            project_id=UUID(project_id),
            run_id=UUID(run_id),
            artifact_id=UUID(run_log_artifact_id),
            user=user,
            supabase=fake,  # type: ignore[arg-type]
            settings=settings,
        )
        if not artifact.download_url.endswith("/projects/22222222-2222-2222-2222-222222222222/runs/33333333-3333-3333-3333-333333333333/log/run.log"):
            raise RuntimeError("artifact url does not point to expected run.log object")
    finally:
        runs_route.get_settings = original_get_settings


def _assert_h1_e7_t1_pilot_smoke() -> dict[str, Any]:
    pilot_script = ROOT / "scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py"
    proc = subprocess.run(
        [sys.executable, str(pilot_script)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "H1-E7-T1 pilot smoke failed:\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )

    stdout = proc.stdout
    json_start = stdout.find("{")
    json_end = stdout.rfind("}")
    if json_start < 0 or json_end <= json_start:
        raise RuntimeError("H1-E7-T1 pilot smoke output missing JSON summary")
    summary = json.loads(stdout[json_start : json_end + 1])
    if summary.get("run_status") != "done":
        raise RuntimeError(f"pilot run_status mismatch: {summary.get('run_status')!r}")
    artifact_kinds = summary.get("artifact_kinds")
    if not isinstance(artifact_kinds, list):
        raise RuntimeError("pilot artifact_kinds missing")
    expected_kinds = {"solver_output", "sheet_svg", "sheet_dxf"}
    if not expected_kinds.issubset(set(str(item) for item in artifact_kinds)):
        raise RuntimeError(f"pilot artifact kinds missing expected entries: {expected_kinds} vs {artifact_kinds}")
    return summary


def main() -> int:
    _assert_h1_task_evidence_chain()
    _assert_runs_route_regression_fixes()
    pilot_summary = _assert_h1_e7_t1_pilot_smoke()
    print(
        json.dumps(
            {
                "h1_task_count": len(H1_TASK_EVIDENCE),
                "pilot_run_id": pilot_summary.get("run_id"),
                "pilot_status": pilot_summary.get("run_status"),
                "pilot_artifact_kinds": pilot_summary.get("artifact_kinds"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    print("PASS: H1-E7-T2 H1 audit + regression smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
