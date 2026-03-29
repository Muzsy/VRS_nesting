#!/usr/bin/env python3
"""Headless smoke for trial_run_tool_core using fake transport."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.trial_run_tool_core import HttpTransport, TrialRunConfig, TrialRunToolError, _HttpRequest, run_trial  # noqa: E402


@dataclass
class _FakeResponse:
    status_code: int
    payload: Any = None
    content: bytes = b""
    headers: dict[str, str] | None = None

    @property
    def text(self) -> str:
        if isinstance(self.payload, (dict, list)):
            return json.dumps(self.payload, ensure_ascii=False)
        if isinstance(self.payload, str):
            return self.payload
        if self.content:
            return self.content.decode("utf-8", errors="replace")
        return ""

    def json(self) -> Any:
        if self.payload is None:
            raise ValueError("no json payload")
        if isinstance(self.payload, (dict, list)):
            return self.payload
        raise ValueError("payload is not json")


class _FakeTransport(HttpTransport):
    def __init__(self) -> None:
        self._upload_index = 0
        self._run_poll_count = 0
        self._uploads: dict[str, dict[str, Any]] = {}
        self._download_blobs: dict[str, bytes] = {
            "a_sheet_svg": b"<svg>sheet</svg>",
            "a_sheet_dxf": b"0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n",
            "a_solver_output": b'{"placements": []}\n',
            "a_run_log": b"run line 1\nrun line 2\n",
            "a_runner_meta": b'{"worker": "fake"}\n',
            "a_solver_stderr": b"stderr line\n",
        }

    def request(self, req: _HttpRequest) -> _FakeResponse:
        parsed = urlsplit(req.url)
        path = parsed.path
        host = parsed.netloc
        method = req.method.upper()

        if host == "localhost:8000" and path == "/health" and method == "GET":
            return _FakeResponse(status_code=200, payload={"status": "ok"})

        if host == "upload.local" and method in {"PUT", "POST"}:
            return _FakeResponse(status_code=200, payload={"ok": True})

        if host == "download.local" and method == "GET":
            artifact_id = path.strip("/")
            blob = self._download_blobs.get(artifact_id)
            if blob is None:
                return _FakeResponse(status_code=404, payload={"error": "not found"})
            return _FakeResponse(status_code=200, payload=None, content=blob)

        if host == "example.supabase.co" and path == "/rest/v1/geometry_revisions" and method == "GET":
            params = req.params or {}
            file_token = str(params.get("source_file_object_id", ""))
            file_id = file_token[3:] if file_token.startswith("eq.") else file_token
            if file_id not in self._uploads:
                return _FakeResponse(status_code=200, payload=[])
            return _FakeResponse(
                status_code=200,
                payload=[
                    {
                        "id": f"geom_{file_id}",
                        "status": "validated",
                        "project_id": "project_1",
                        "source_file_object_id": file_id,
                        "created_at": "2026-03-29T12:00:00Z",
                    }
                ],
            )

        if host == "localhost:8000" and path == "/v1/projects" and method == "POST":
            return _FakeResponse(
                status_code=200,
                payload={
                    "id": "project_1",
                    "name": "Trial project",
                    "description": "",
                    "owner_user_id": "user_1",
                    "lifecycle": "active",
                },
            )

        if host == "localhost:8000" and path.startswith("/v1/projects/project_1/files/upload-url") and method == "POST":
            self._upload_index += 1
            file_id = f"file_{self._upload_index}"
            payload = req.json_body or {}
            filename = str(payload.get("filename", f"part_{self._upload_index}.dxf"))
            storage_path = f"projects/project_1/files/{file_id}/{filename}"
            self._uploads[file_id] = {"filename": filename, "storage_path": storage_path}
            return _FakeResponse(
                status_code=200,
                payload={
                    "upload_url": f"https://upload.local/{file_id}",
                    "file_id": file_id,
                    "storage_path": storage_path,
                    "expires_at": "2026-03-29T12:05:00Z",
                },
            )

        if host == "localhost:8000" and path.startswith("/v1/projects/project_1/files") and method == "POST":
            payload = req.json_body or {}
            file_id = str(payload.get("file_id", ""))
            upload = self._uploads.get(file_id)
            if not upload:
                return _FakeResponse(status_code=400, payload={"detail": "unknown file"})
            return _FakeResponse(
                status_code=200,
                payload={
                    "id": file_id,
                    "project_id": "project_1",
                    "storage_path": upload["storage_path"],
                    "file_name": upload["filename"],
                    "file_kind": "source_dxf",
                },
            )

        if host == "localhost:8000" and path.startswith("/v1/projects/project_1/parts") and method == "POST":
            payload = req.json_body or {}
            geometry_revision_id = str(payload.get("geometry_revision_id", ""))
            if not geometry_revision_id:
                return _FakeResponse(status_code=400, payload={"detail": "missing geometry id"})
            part_index = len([key for key in self._uploads])
            return _FakeResponse(
                status_code=201,
                payload={
                    "part_definition_id": f"pdef_{part_index}",
                    "part_revision_id": f"prev_{geometry_revision_id}",
                    "revision_no": 1,
                    "lifecycle": "approved",
                    "code": payload.get("code", ""),
                    "name": payload.get("name", ""),
                    "source_geometry_revision_id": geometry_revision_id,
                    "selected_nesting_derivative_id": f"nd_{geometry_revision_id}",
                    "was_existing_definition": False,
                },
            )

        if host == "localhost:8000" and path.startswith("/v1/projects/project_1/part-requirements") and method == "POST":
            payload = req.json_body or {}
            return _FakeResponse(
                status_code=201,
                payload={
                    "project_part_requirement_id": f"req_{payload.get('part_revision_id')}",
                    "project_id": "project_1",
                    "part_revision_id": payload.get("part_revision_id", ""),
                    "required_qty": payload.get("required_qty", 1),
                },
            )

        if host == "localhost:8000" and path == "/v1/sheets" and method == "POST":
            return _FakeResponse(
                status_code=201,
                payload={
                    "sheet_definition_id": "sdef_1",
                    "sheet_revision_id": "srev_1",
                    "revision_no": 1,
                    "lifecycle": "approved",
                    "code": "TRIAL-SHEET",
                    "name": "Trial Sheet",
                },
            )

        if host == "localhost:8000" and path.startswith("/v1/projects/project_1/sheet-inputs") and method == "POST":
            payload = req.json_body or {}
            return _FakeResponse(
                status_code=201,
                payload={
                    "project_sheet_input_id": "psi_1",
                    "project_id": "project_1",
                    "sheet_revision_id": payload.get("sheet_revision_id", ""),
                    "required_qty": payload.get("required_qty", 1),
                },
            )

        if host == "localhost:8000" and path == "/v1/projects/project_1/runs" and method == "POST":
            return _FakeResponse(status_code=200, payload={"id": "run_1", "status": "queued", "project_id": "project_1"})

        if host == "localhost:8000" and path == "/v1/projects/project_1/runs/run_1" and method == "GET":
            self._run_poll_count += 1
            status = "running" if self._run_poll_count < 2 else "done"
            return _FakeResponse(status_code=200, payload={"id": "run_1", "project_id": "project_1", "status": status})

        if host == "localhost:8000" and path == "/v1/projects/project_1/runs/run_1/artifacts" and method == "GET":
            return _FakeResponse(
                status_code=200,
                payload={
                    "items": [
                        {"id": "a_sheet_svg", "artifact_type": "sheet_svg", "filename": "sheet_001.svg"},
                        {"id": "a_sheet_dxf", "artifact_type": "sheet_dxf", "filename": "sheet_001.dxf"},
                        {"id": "a_solver_output", "artifact_type": "solver_output", "filename": "solver_output.json"},
                        {"id": "a_run_log", "artifact_type": "run_log", "filename": "run.log"},
                        {"id": "a_runner_meta", "artifact_type": "runner_meta", "filename": "runner_meta.json"},
                        {"id": "a_solver_stderr", "artifact_type": "solver_stderr", "filename": "solver_stderr.log"},
                    ]
                },
            )

        if host == "localhost:8000" and path == "/v1/projects/project_1/runs/run_1/viewer-data" and method == "GET":
            return _FakeResponse(status_code=200, payload={"run_id": "run_1", "status": "done", "sheet_count": 1, "sheets": []})

        if (
            host == "localhost:8000"
            and path.startswith("/v1/projects/project_1/runs/run_1/artifacts/")
            and path.endswith("/url")
            and method == "GET"
        ):
            artifact_id = path.split("/")[-2]
            return _FakeResponse(
                status_code=200,
                payload={
                    "artifact_id": artifact_id,
                    "filename": f"{artifact_id}.bin",
                    "download_url": f"https://download.local/{artifact_id}?sig=fake",
                    "expires_at": "2026-03-29T12:10:00Z",
                },
            )

        return _FakeResponse(status_code=404, payload={"detail": f"unhandled route: {method} {req.url}"})


def _assert_exists(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"expected file missing: {path}")


def main() -> int:
    with TemporaryDirectory(prefix="smoke_trial_run_tool_") as tmp:
        root = Path(tmp)
        dxf_dir = root / "dxf"
        out_dir = root / "runs"
        dxf_dir.mkdir(parents=True, exist_ok=True)

        (dxf_dir / "part_a.dxf").write_text("0\nEOF\n", encoding="utf-8")
        (dxf_dir / "part_b.dxf").write_text("0\nEOF\n", encoding="utf-8")

        cfg = TrialRunConfig(
            dxf_dir=dxf_dir,
            bearer_token="trial-secret-token-12345",
            token_source="argv",
            api_base_url="http://localhost:8000/v1",
            sheet_width=2000.0,
            sheet_height=1000.0,
            default_qty=2,
            per_file_qty={"part_b.dxf": 3},
            output_base_dir=out_dir,
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
            poll_interval_s=0.01,
            run_poll_timeout_s=2.0,
            geometry_poll_timeout_s=2.0,
        )

        result = run_trial(cfg, transport=_FakeTransport())
        if not result.success:
            raise RuntimeError(f"trial run smoke failed: {result.error_message}")

        expected_files = [
            "run.log",
            "inputs_redacted.json",
            "api_health.json",
            "created_project.json",
            "uploaded_files.json",
            "geometry_revisions.json",
            "created_parts.json",
            "created_sheet.json",
            "project_part_requirements.json",
            "project_sheet_input.json",
            "created_run.json",
            "run_poll_history.json",
            "final_run.json",
            "run_artifacts.json",
            "viewer_data.json",
            "downloaded_artifact_urls.json",
            "summary.md",
            "sheet_001.svg",
            "sheet_001.dxf",
        ]
        for rel in expected_files:
            _assert_exists(result.run_dir / rel)

        inputs_text = (result.run_dir / "inputs_redacted.json").read_text(encoding="utf-8")
        if "trial-secret-token-12345" in inputs_text:
            raise RuntimeError("token leaked in inputs_redacted.json")

        summary_text = (result.run_dir / "summary.md").read_text(encoding="utf-8")
        if "SUCCESS" not in summary_text:
            raise RuntimeError("summary.md missing SUCCESS marker")

        downloads = json.loads((result.run_dir / "downloaded_artifact_urls.json").read_text(encoding="utf-8"))
        if not isinstance(downloads, dict):
            raise RuntimeError("downloaded_artifact_urls.json invalid format")
        download_items = downloads.get("items")
        if not isinstance(download_items, list) or len(download_items) < 4:
            raise RuntimeError("downloaded_artifact_urls.json does not contain expected downloads")

        print("PASS smoke_trial_run_tool_cli_core")
        print(f"run_dir={result.run_dir}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TrialRunToolError as exc:
        print(f"FAIL smoke_trial_run_tool_cli_core: {exc}", file=sys.stderr)
        raise
