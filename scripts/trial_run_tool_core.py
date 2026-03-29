#!/usr/bin/env python3
"""Core orchestrator for local-only trial-run tool.

This module is intentionally GUI-agnostic. It executes the authenticated
web-platform run chain and writes a reproducible evidence directory under
`tmp/runs/...`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit
import json
import re
import subprocess
import time
from uuid import uuid4


_JSON_INDENT = 2
_JSON_SORT_KEYS = True


class TrialRunToolError(RuntimeError):
    """Raised when an orchestrator step fails."""


@dataclass(frozen=True)
class TrialRunConfig:
    dxf_dir: Path
    bearer_token: str
    token_source: str
    api_base_url: str = "http://127.0.0.1:8000/v1"
    sheet_width: float = 3000.0
    sheet_height: float = 1500.0
    existing_project_id: str | None = None
    project_name: str | None = None
    project_description: str | None = None
    default_qty: int = 1
    per_file_qty: dict[str, int] | None = None
    output_base_dir: Path = Path("tmp/runs")
    auto_start_platform: bool = False
    health_timeout_s: float = 30.0
    poll_interval_s: float = 1.0
    run_poll_timeout_s: float = 300.0
    geometry_poll_timeout_s: float = 60.0
    request_timeout_s: float = 30.0
    supabase_url: str | None = None
    supabase_anon_key: str | None = None


@dataclass(frozen=True)
class TrialRunResult:
    success: bool
    run_dir: Path
    summary_path: Path
    project_id: str | None
    run_id: str | None
    final_run_status: str | None
    error_message: str | None


@dataclass(frozen=True)
class _HttpRequest:
    method: str
    url: str
    headers: dict[str, str] | None = None
    json_body: Any = None
    data: bytes | str | None = None
    params: dict[str, str] | None = None
    timeout: float = 30.0
    allow_redirects: bool = True


class HttpTransport:
    def request(self, req: _HttpRequest) -> Any:  # pragma: no cover - interface
        raise NotImplementedError


class RequestsTransport(HttpTransport):
    """Default HTTP transport backed by requests."""

    def __init__(self) -> None:
        import requests

        self._session = requests.Session()

    def request(self, req: _HttpRequest) -> Any:
        kwargs: dict[str, Any] = {
            "method": req.method,
            "url": req.url,
            "headers": req.headers,
            "timeout": req.timeout,
            "allow_redirects": req.allow_redirects,
            "params": req.params,
        }
        if req.json_body is not None:
            kwargs["json"] = req.json_body
        if req.data is not None:
            kwargs["data"] = req.data
        return self._session.request(**kwargs)


class _RunRecorder:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.log_path = run_dir / "run.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("", encoding="utf-8")

    def log(self, message: str) -> None:
        stamp = _now_iso()
        line = f"[{stamp}] {message}"
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def write_json(self, name: str, payload: Any) -> None:
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=_JSON_INDENT, sort_keys=_JSON_SORT_KEYS) + "\n",
            encoding="utf-8",
        )

    def write_text(self, name: str, payload: str) -> None:
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_compact_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-._")
    return cleaned or "run"


def _normalize_api_base_url(raw: str) -> str:
    base = raw.strip().rstrip("/")
    if not base:
        raise TrialRunToolError("api_base_url must not be empty")
    if base.endswith("/v1"):
        return base
    return f"{base}/v1"


def _health_url_from_api_base(api_base_url: str) -> str:
    if api_base_url.endswith("/v1"):
        return f"{api_base_url[:-3]}/health"
    return f"{api_base_url}/health"


def _token_meta(token: str, source: str) -> dict[str, Any]:
    tail = token[-4:] if len(token) >= 4 else token
    return {
        "source": source,
        "length": len(token),
        "tail": tail,
        "present": bool(token.strip()),
        "redacted": f"***{tail}" if tail else "***",
    }


def _parse_json_response(response: Any, *, where: str) -> Any:
    try:
        return response.json()
    except Exception as exc:  # noqa: BLE001
        text = str(getattr(response, "text", ""))
        raise TrialRunToolError(f"{where}: invalid JSON response: {text[:300]}") from exc


def _response_excerpt(response: Any) -> str:
    text = str(getattr(response, "text", ""))
    if text:
        return text[:500]
    content = getattr(response, "content", b"")
    if isinstance(content, bytes):
        return content[:500].decode("utf-8", errors="replace")
    return str(content)[:500]


def _request_json(
    *,
    transport: HttpTransport,
    method: str,
    url: str,
    where: str,
    expected: set[int],
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    params: dict[str, str] | None = None,
    timeout: float,
) -> Any:
    response = transport.request(
        _HttpRequest(
            method=method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params,
            timeout=timeout,
        )
    )
    status_code = int(getattr(response, "status_code", 0))
    if status_code not in expected:
        raise TrialRunToolError(f"{where}: status={status_code} body={_response_excerpt(response)}")
    if status_code == 204:
        return {}
    return _parse_json_response(response, where=where)


def _request_bytes(
    *,
    transport: HttpTransport,
    method: str,
    url: str,
    where: str,
    expected: set[int],
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float,
    allow_redirects: bool = True,
) -> bytes:
    response = transport.request(
        _HttpRequest(
            method=method,
            url=url,
            headers=headers,
            data=data,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
    )
    status_code = int(getattr(response, "status_code", 0))
    if status_code not in expected:
        raise TrialRunToolError(f"{where}: status={status_code} body={_response_excerpt(response)}")
    content = getattr(response, "content", b"")
    if isinstance(content, bytes):
        return content
    if content is None:
        return b""
    return str(content).encode("utf-8")


def _request_upload_blob(
    *,
    transport: HttpTransport,
    upload_url: str,
    payload: bytes,
    timeout: float,
) -> dict[str, Any]:
    last_error = ""
    for method in ("PUT", "POST"):
        response = transport.request(
            _HttpRequest(
                method=method,
                url=upload_url,
                headers={"Content-Type": "application/dxf"},
                data=payload,
                timeout=timeout,
            )
        )
        status_code = int(getattr(response, "status_code", 0))
        if status_code in {200, 201}:
            return {"method": method, "status_code": status_code}
        last_error = f"method={method} status={status_code} body={_response_excerpt(response)}"
    raise TrialRunToolError(f"signed upload failed: {last_error}")


def _safe_filename(name: str, fallback: str) -> str:
    candidate = Path(name).name.strip()
    if not candidate:
        return fallback
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", candidate)


def _normalize_project_name(config: TrialRunConfig, run_slug: str) -> str:
    if config.project_name and config.project_name.strip():
        return config.project_name.strip()
    return f"Trial run {run_slug}"


def _resolve_qty(dxf_path: Path, default_qty: int, overrides: dict[str, int]) -> int:
    for key in (dxf_path.name, dxf_path.stem):
        if key in overrides:
            return overrides[key]
    return default_qty


def _collect_dxf_files(dxf_dir: Path) -> list[Path]:
    if not dxf_dir.is_dir():
        raise TrialRunToolError(f"DXF directory not found: {dxf_dir}")
    files = sorted(path for path in dxf_dir.iterdir() if path.is_file() and path.suffix.lower() == ".dxf")
    if not files:
        raise TrialRunToolError(f"no .dxf files found in: {dxf_dir}")
    return files


def _postgrest_headers(*, bearer_token: str, anon_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer_token}",
        "apikey": anon_key,
        "Content-Type": "application/json",
        "Accept-Profile": "app",
        "Content-Profile": "app",
    }


def _query_geometry_revision(
    *,
    transport: HttpTransport,
    supabase_url: str,
    supabase_anon_key: str,
    bearer_token: str,
    project_id: str,
    file_id: str,
    timeout: float,
) -> dict[str, Any] | None:
    url = f"{supabase_url.rstrip('/')}/rest/v1/geometry_revisions"
    payload = _request_json(
        transport=transport,
        method="GET",
        url=url,
        where=f"postgrest geometry_revisions for file_id={file_id}",
        expected={200},
        headers=_postgrest_headers(bearer_token=bearer_token, anon_key=supabase_anon_key),
        params={
            "select": "id,status,project_id,source_file_object_id,created_at,updated_at",
            "project_id": f"eq.{project_id}",
            "source_file_object_id": f"eq.{file_id}",
            "order": "created_at.desc",
            "limit": "1",
        },
        timeout=timeout,
    )
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if isinstance(first, dict):
        return first
    return None


def _poll_geometry_revision(
    *,
    transport: HttpTransport,
    recorder: _RunRecorder,
    config: TrialRunConfig,
    project_id: str,
    file_id: str,
    file_name: str,
) -> dict[str, Any]:
    supabase_url = (config.supabase_url or "").strip()
    supabase_anon_key = (config.supabase_anon_key or "").strip()
    if not supabase_url or not supabase_anon_key:
        raise TrialRunToolError(
            "geometry polling requires SUPABASE_URL and SUPABASE_ANON_KEY (CLI args or env)."
        )

    deadline = time.monotonic() + config.geometry_poll_timeout_s
    last_row: dict[str, Any] | None = None
    while time.monotonic() <= deadline:
        row = _query_geometry_revision(
            transport=transport,
            supabase_url=supabase_url,
            supabase_anon_key=supabase_anon_key,
            bearer_token=config.bearer_token,
            project_id=project_id,
            file_id=file_id,
            timeout=config.request_timeout_s,
        )
        if row is None:
            time.sleep(config.poll_interval_s)
            continue

        last_row = row
        status_value = str(row.get("status", "")).strip().lower()
        if status_value == "validated":
            recorder.log(f"geometry validated file={file_name} geometry_revision_id={row.get('id')}")
            return row
        if status_value == "rejected":
            raise TrialRunToolError(
                f"geometry import rejected file={file_name} geometry_revision_id={row.get('id')}"
            )
        time.sleep(config.poll_interval_s)

    raise TrialRunToolError(
        "geometry polling timeout "
        f"file={file_name} last_row={json.dumps(last_row, ensure_ascii=False, sort_keys=True) if last_row else 'none'}"
    )


def _start_platform_if_requested(config: TrialRunConfig, recorder: _RunRecorder) -> dict[str, Any]:
    if not config.auto_start_platform:
        return {"attempted": False, "started": False}

    root = Path(__file__).resolve().parents[1]
    cmd = [str(root / "scripts" / "run_web_platform.sh"), "start"]
    recorder.log(f"platform start attempt command={' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout_tail = (proc.stdout or "")[-1000:]
    stderr_tail = (proc.stderr or "")[-1000:]
    started = proc.returncode == 0
    recorder.log(f"platform start returncode={proc.returncode}")
    return {
        "attempted": True,
        "started": started,
        "returncode": int(proc.returncode),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _ensure_api_health(
    *,
    transport: HttpTransport,
    recorder: _RunRecorder,
    config: TrialRunConfig,
) -> dict[str, Any]:
    health_url = _health_url_from_api_base(config.api_base_url)
    health_record: dict[str, Any] = {
        "health_url": health_url,
        "checked_at": _now_iso(),
        "auto_start_platform": config.auto_start_platform,
        "initial_ok": False,
        "response": None,
        "platform_start": {"attempted": False, "started": False},
    }

    try:
        payload = _request_json(
            transport=transport,
            method="GET",
            url=health_url,
            where="GET /health",
            expected={200},
            timeout=config.request_timeout_s,
        )
        health_record["initial_ok"] = True
        health_record["response"] = payload
        recorder.log("api health check passed without auto-start")
        return health_record
    except Exception as exc:  # noqa: BLE001
        health_record["initial_error"] = str(exc)

    health_record["platform_start"] = _start_platform_if_requested(config, recorder)
    if not config.auto_start_platform:
        raise TrialRunToolError(f"API health check failed: {health_record.get('initial_error', '')}")

    deadline = time.monotonic() + config.health_timeout_s
    while time.monotonic() <= deadline:
        try:
            payload = _request_json(
                transport=transport,
                method="GET",
                url=health_url,
                where="GET /health retry",
                expected={200},
                timeout=config.request_timeout_s,
            )
            health_record["response"] = payload
            health_record["ready_after_auto_start"] = True
            recorder.log("api health check passed after auto-start")
            return health_record
        except Exception:  # noqa: BLE001
            time.sleep(0.5)

    raise TrialRunToolError("API health check did not recover after platform auto-start")


def _initialize_run_placeholders(recorder: _RunRecorder) -> None:
    placeholders: dict[str, Any] = {
        "inputs_redacted.json": {"status": "pending"},
        "api_health.json": {"status": "pending"},
        "created_project.json": {"status": "pending"},
        "uploaded_files.json": {"status": "pending", "items": []},
        "geometry_revisions.json": {"status": "pending", "items": []},
        "created_parts.json": {"status": "pending", "items": []},
        "created_sheet.json": {"status": "pending"},
        "project_part_requirements.json": {"status": "pending", "items": []},
        "project_sheet_input.json": {"status": "pending"},
        "created_run.json": {"status": "pending"},
        "run_poll_history.json": {"status": "pending", "items": []},
        "final_run.json": {"status": "pending"},
        "run_artifacts.json": {"status": "pending", "items": []},
        "viewer_data.json": {"status": "pending"},
        "downloaded_artifact_urls.json": {"status": "pending", "items": [], "errors": []},
    }
    for name, payload in placeholders.items():
        recorder.write_json(name, payload)


def _prepare_run_dir(config: TrialRunConfig) -> Path:
    output_base = config.output_base_dir.resolve()
    output_base.mkdir(parents=True, exist_ok=True)
    key = config.existing_project_id or config.dxf_dir.name
    run_slug = f"{_utc_compact_ts()}_{_slugify(key)}_{uuid4().hex[:8]}"
    run_dir = output_base / run_slug
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _build_summary_markdown(
    *,
    success: bool,
    run_dir: Path,
    project_id: str | None,
    run_id: str | None,
    final_status: str | None,
    uploaded_count: int,
    part_count: int,
    downloaded_count: int,
    token_meta: dict[str, Any],
    warnings: list[str],
    error_message: str | None,
) -> str:
    lines: list[str] = []
    lines.append("# Trial run summary")
    lines.append("")
    lines.append(f"- status: {'SUCCESS' if success else 'FAILED'}")
    lines.append(f"- generated_at_utc: {_now_iso()}")
    lines.append(f"- run_dir: {run_dir}")
    lines.append(f"- project_id: {project_id or ''}")
    lines.append(f"- run_id: {run_id or ''}")
    lines.append(f"- final_run_status: {final_status or ''}")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- uploaded_files: {uploaded_count}")
    lines.append(f"- created_parts: {part_count}")
    lines.append(f"- downloaded_artifacts: {downloaded_count}")
    lines.append("")
    lines.append("## Token")
    lines.append("")
    lines.append(f"- source: {token_meta.get('source', '')}")
    lines.append(f"- present: {token_meta.get('present', False)}")
    lines.append(f"- length: {token_meta.get('length', 0)}")
    lines.append(f"- tail: {token_meta.get('tail', '')}")
    lines.append(f"- redacted: {token_meta.get('redacted', '***')}")
    lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for item in warnings:
            lines.append(f"- {item}")
        lines.append("")

    if error_message:
        lines.append("## Error")
        lines.append("")
        lines.append(f"- {error_message}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_qty_overrides(raw_items: list[str]) -> dict[str, int]:
    """Parse `name=qty` entries into a validated mapping."""

    out: dict[str, int] = {}
    for raw in raw_items:
        if "=" not in raw:
            raise TrialRunToolError(f"invalid qty override (expected name=qty): {raw}")
        name, qty_text = raw.split("=", 1)
        key = name.strip()
        if not key:
            raise TrialRunToolError(f"invalid qty override key: {raw}")
        try:
            qty = int(qty_text.strip())
        except ValueError as exc:
            raise TrialRunToolError(f"invalid qty override qty: {raw}") from exc
        if qty <= 0:
            raise TrialRunToolError(f"qty override must be > 0: {raw}")
        out[key] = qty
    return out


def run_trial(config: TrialRunConfig, *, transport: HttpTransport | None = None) -> TrialRunResult:
    """Execute the end-to-end trial-run tool chain.

    This function is deterministic in side-effects: all runtime evidence is written
    under one run directory and never in repository-tracked locations.
    """

    normalized_config = TrialRunConfig(
        dxf_dir=config.dxf_dir.resolve(),
        bearer_token=config.bearer_token.strip(),
        token_source=config.token_source,
        api_base_url=_normalize_api_base_url(config.api_base_url),
        sheet_width=float(config.sheet_width),
        sheet_height=float(config.sheet_height),
        existing_project_id=(config.existing_project_id.strip() if config.existing_project_id else None),
        project_name=config.project_name,
        project_description=config.project_description,
        default_qty=int(config.default_qty),
        per_file_qty=dict(config.per_file_qty or {}),
        output_base_dir=config.output_base_dir,
        auto_start_platform=bool(config.auto_start_platform),
        health_timeout_s=float(config.health_timeout_s),
        poll_interval_s=float(config.poll_interval_s),
        run_poll_timeout_s=float(config.run_poll_timeout_s),
        geometry_poll_timeout_s=float(config.geometry_poll_timeout_s),
        request_timeout_s=float(config.request_timeout_s),
        supabase_url=(config.supabase_url.strip() if config.supabase_url else None),
        supabase_anon_key=(config.supabase_anon_key.strip() if config.supabase_anon_key else None),
    )

    if normalized_config.default_qty <= 0:
        raise TrialRunToolError("default_qty must be > 0")
    if normalized_config.sheet_width <= 0 or normalized_config.sheet_height <= 0:
        raise TrialRunToolError("sheet_width and sheet_height must be > 0")
    if not normalized_config.bearer_token:
        raise TrialRunToolError("bearer token is required")

    run_dir = _prepare_run_dir(normalized_config)
    recorder = _RunRecorder(run_dir=run_dir)
    _initialize_run_placeholders(recorder)

    http = transport or RequestsTransport()
    token_meta = _token_meta(normalized_config.bearer_token, normalized_config.token_source)

    step = "initialization"
    project_id: str | None = None
    run_id: str | None = None
    final_run_status: str | None = None
    error_message: str | None = None
    warnings: list[str] = []

    uploaded_items: list[dict[str, Any]] = []
    geometry_items: list[dict[str, Any]] = []
    created_parts: list[dict[str, Any]] = []
    part_requirements: list[dict[str, Any]] = []
    downloaded_items: list[dict[str, Any]] = []
    download_errors: list[dict[str, Any]] = []

    auth_headers = {
        "Authorization": f"Bearer {normalized_config.bearer_token}",
        "Content-Type": "application/json",
    }

    dxf_files = _collect_dxf_files(normalized_config.dxf_dir)
    recorder.log(f"run_dir={run_dir}")
    recorder.log(f"dxf_files={len(dxf_files)}")

    recorder.write_json(
        "inputs_redacted.json",
        {
            "created_at": _now_iso(),
            "dxf_dir": str(normalized_config.dxf_dir),
            "api_base_url": normalized_config.api_base_url,
            "sheet_width": normalized_config.sheet_width,
            "sheet_height": normalized_config.sheet_height,
            "existing_project_id": normalized_config.existing_project_id,
            "project_name": normalized_config.project_name,
            "default_qty": normalized_config.default_qty,
            "per_file_qty": normalized_config.per_file_qty,
            "output_base_dir": str(normalized_config.output_base_dir),
            "auto_start_platform": normalized_config.auto_start_platform,
            "supabase_url_present": bool(normalized_config.supabase_url),
            "supabase_anon_key_present": bool(normalized_config.supabase_anon_key),
            "token": token_meta,
            "dxf_files": [path.name for path in dxf_files],
        },
    )

    try:
        step = "health-check"
        api_health = _ensure_api_health(transport=http, recorder=recorder, config=normalized_config)
        recorder.write_json("api_health.json", api_health)

        step = "project-resolve"
        if normalized_config.existing_project_id:
            payload = _request_json(
                transport=http,
                method="GET",
                url=f"{normalized_config.api_base_url}/projects/{normalized_config.existing_project_id}",
                where="GET project",
                expected={200},
                headers=auth_headers,
                timeout=normalized_config.request_timeout_s,
            )
            if not isinstance(payload, dict):
                raise TrialRunToolError("existing project payload is not an object")
            project_id = str(payload.get("id", "")).strip() or normalized_config.existing_project_id
            recorder.write_json(
                "created_project.json",
                {"status": "ok", "mode": "existing", "project": payload},
            )
        else:
            create_payload = {
                "name": _normalize_project_name(normalized_config, run_dir.name),
                "description": (normalized_config.project_description or "trial-run tool execution"),
            }
            payload = _request_json(
                transport=http,
                method="POST",
                url=f"{normalized_config.api_base_url}/projects",
                where="POST /projects",
                expected={200},
                headers=auth_headers,
                json_body=create_payload,
                timeout=normalized_config.request_timeout_s,
            )
            if not isinstance(payload, dict):
                raise TrialRunToolError("project creation payload is not an object")
            project_id = str(payload.get("id", "")).strip()
            if not project_id:
                raise TrialRunToolError("project creation returned empty id")
            recorder.write_json(
                "created_project.json",
                {"status": "ok", "mode": "created", "project": payload},
            )
        recorder.log(f"project_id={project_id}")

        step = "files-upload"
        for index, dxf_path in enumerate(dxf_files, start=1):
            blob = dxf_path.read_bytes()
            upload_payload = _request_json(
                transport=http,
                method="POST",
                url=f"{normalized_config.api_base_url}/projects/{project_id}/files/upload-url",
                where=f"POST upload-url file={dxf_path.name}",
                expected={200},
                headers=auth_headers,
                json_body={
                    "filename": dxf_path.name,
                    "content_type": "application/dxf",
                    "size_bytes": len(blob),
                    "file_kind": "source_dxf",
                },
                timeout=normalized_config.request_timeout_s,
            )
            if not isinstance(upload_payload, dict):
                raise TrialRunToolError(f"upload-url payload invalid for file={dxf_path.name}")

            file_id = str(upload_payload.get("file_id", "")).strip()
            storage_path = str(upload_payload.get("storage_path") or upload_payload.get("storage_key") or "").strip()
            upload_url = str(upload_payload.get("upload_url", "")).strip()
            if not file_id or not storage_path or not upload_url:
                raise TrialRunToolError(f"upload-url payload missing fields for file={dxf_path.name}")

            upload_result = _request_upload_blob(
                transport=http,
                upload_url=upload_url,
                payload=blob,
                timeout=normalized_config.request_timeout_s,
            )

            complete_payload = _request_json(
                transport=http,
                method="POST",
                url=f"{normalized_config.api_base_url}/projects/{project_id}/files",
                where=f"POST file-complete file={dxf_path.name}",
                expected={200},
                headers=auth_headers,
                json_body={
                    "file_id": file_id,
                    "storage_path": storage_path,
                    "file_kind": "source_dxf",
                },
                timeout=normalized_config.request_timeout_s,
            )

            item = {
                "index": index,
                "file_name": dxf_path.name,
                "file_id": file_id,
                "storage_path": storage_path,
                "size_bytes": len(blob),
                "upload": {
                    "method": upload_result["method"],
                    "status_code": upload_result["status_code"],
                    "upload_url_redacted": _strip_url_query(upload_url),
                },
                "complete_response": complete_payload,
            }
            uploaded_items.append(item)
            recorder.log(f"uploaded file={dxf_path.name} file_id={file_id}")

        recorder.write_json("uploaded_files.json", {"status": "ok", "items": uploaded_items})

        step = "geometry-poll"
        for item in uploaded_items:
            row = _poll_geometry_revision(
                transport=http,
                recorder=recorder,
                config=normalized_config,
                project_id=project_id,
                file_id=str(item.get("file_id", "")),
                file_name=str(item.get("file_name", "")),
            )
            geometry_id = str(row.get("id", "")).strip()
            if not geometry_id:
                raise TrialRunToolError(f"geometry row missing id for file={item.get('file_name')}")
            geometry_item = {
                "file_id": item.get("file_id"),
                "file_name": item.get("file_name"),
                "geometry_revision": row,
            }
            geometry_items.append(geometry_item)

        recorder.write_json("geometry_revisions.json", {"status": "ok", "items": geometry_items})

        step = "parts-and-requirements"
        per_file_qty = normalized_config.per_file_qty or {}
        for index, geom_item in enumerate(geometry_items, start=1):
            file_name = str(geom_item.get("file_name", "part.dxf"))
            path_stub = Path(file_name)
            qty = _resolve_qty(path_stub, normalized_config.default_qty, per_file_qty)
            code = f"TRIAL-{index:03d}-{_slugify(path_stub.stem).upper()}"[:120]
            name = path_stub.stem[:240] or f"Part {index}"

            create_part_payload = _request_json(
                transport=http,
                method="POST",
                url=f"{normalized_config.api_base_url}/projects/{project_id}/parts",
                where=f"POST /parts file={file_name}",
                expected={201},
                headers=auth_headers,
                json_body={
                    "code": code,
                    "name": name,
                    "geometry_revision_id": str(geom_item["geometry_revision"]["id"]),
                    "source_label": file_name,
                },
                timeout=normalized_config.request_timeout_s,
            )
            if not isinstance(create_part_payload, dict):
                raise TrialRunToolError(f"part creation payload invalid file={file_name}")
            part_revision_id = str(create_part_payload.get("part_revision_id", "")).strip()
            if not part_revision_id:
                raise TrialRunToolError(f"part creation returned empty part_revision_id file={file_name}")

            requirement_payload = _request_json(
                transport=http,
                method="POST",
                url=f"{normalized_config.api_base_url}/projects/{project_id}/part-requirements",
                where=f"POST /part-requirements file={file_name}",
                expected={201},
                headers=auth_headers,
                json_body={
                    "part_revision_id": part_revision_id,
                    "required_qty": qty,
                    "placement_priority": 50,
                    "placement_policy": "normal",
                    "is_active": True,
                },
                timeout=normalized_config.request_timeout_s,
            )
            created_parts.append(
                {
                    "file_name": file_name,
                    "qty": qty,
                    "part": create_part_payload,
                }
            )
            part_requirements.append(
                {
                    "file_name": file_name,
                    "part_revision_id": part_revision_id,
                    "requirement": requirement_payload,
                }
            )
            recorder.log(f"created part file={file_name} part_revision_id={part_revision_id} qty={qty}")

        recorder.write_json("created_parts.json", {"status": "ok", "items": created_parts})
        recorder.write_json("project_part_requirements.json", {"status": "ok", "items": part_requirements})

        step = "sheet-and-input"
        sheet_payload = _request_json(
            transport=http,
            method="POST",
            url=f"{normalized_config.api_base_url}/sheets",
            where="POST /sheets",
            expected={201},
            headers=auth_headers,
            json_body={
                "code": f"TRIAL-SHEET-{_slugify(run_dir.name)[:80].upper()}",
                "name": f"Trial Sheet {run_dir.name}",
                "width_mm": normalized_config.sheet_width,
                "height_mm": normalized_config.sheet_height,
            },
            timeout=normalized_config.request_timeout_s,
        )
        if not isinstance(sheet_payload, dict):
            raise TrialRunToolError("sheet creation payload invalid")
        sheet_revision_id = str(sheet_payload.get("sheet_revision_id", "")).strip()
        if not sheet_revision_id:
            raise TrialRunToolError("sheet creation returned empty sheet_revision_id")

        sheet_input_payload = _request_json(
            transport=http,
            method="POST",
            url=f"{normalized_config.api_base_url}/projects/{project_id}/sheet-inputs",
            where="POST /sheet-inputs",
            expected={201},
            headers=auth_headers,
            json_body={
                "sheet_revision_id": sheet_revision_id,
                "required_qty": 1,
                "is_active": True,
                "is_default": True,
                "placement_priority": 10,
            },
            timeout=normalized_config.request_timeout_s,
        )
        recorder.write_json("created_sheet.json", {"status": "ok", "sheet": sheet_payload})
        recorder.write_json("project_sheet_input.json", {"status": "ok", "sheet_input": sheet_input_payload})

        step = "run-create"
        run_payload = _request_json(
            transport=http,
            method="POST",
            url=f"{normalized_config.api_base_url}/projects/{project_id}/runs",
            where="POST /runs",
            expected={200},
            headers=auth_headers,
            json_body={"run_purpose": "nesting"},
            timeout=normalized_config.request_timeout_s,
        )
        if not isinstance(run_payload, dict):
            raise TrialRunToolError("run creation payload invalid")
        run_id = str(run_payload.get("id", "")).strip()
        if not run_id:
            raise TrialRunToolError("run creation returned empty id")
        recorder.write_json("created_run.json", {"status": "ok", "run": run_payload})
        recorder.log(f"created run run_id={run_id}")

        step = "run-poll"
        poll_deadline = time.monotonic() + normalized_config.run_poll_timeout_s
        poll_history: list[dict[str, Any]] = []
        final_run_payload: dict[str, Any] | None = None
        terminal = {"done", "failed", "cancelled"}
        while time.monotonic() <= poll_deadline:
            run_details = _request_json(
                transport=http,
                method="GET",
                url=f"{normalized_config.api_base_url}/projects/{project_id}/runs/{run_id}",
                where="GET /runs/{run_id}",
                expected={200},
                headers=auth_headers,
                timeout=normalized_config.request_timeout_s,
            )
            if not isinstance(run_details, dict):
                raise TrialRunToolError("run details payload invalid")
            status_value = str(run_details.get("status", "")).strip().lower()
            poll_history.append(
                {
                    "ts": _now_iso(),
                    "status": status_value,
                    "run": run_details,
                }
            )
            if status_value in terminal:
                final_run_payload = run_details
                final_run_status = status_value
                break
            time.sleep(normalized_config.poll_interval_s)

        if final_run_payload is None:
            raise TrialRunToolError("run polling timeout before terminal state")

        recorder.write_json("run_poll_history.json", {"status": "ok", "items": poll_history})
        recorder.write_json("final_run.json", {"status": "ok", "run": final_run_payload})

        step = "artifacts-list"
        artifacts_payload = _request_json(
            transport=http,
            method="GET",
            url=f"{normalized_config.api_base_url}/projects/{project_id}/runs/{run_id}/artifacts",
            where="GET /artifacts",
            expected={200},
            headers=auth_headers,
            timeout=normalized_config.request_timeout_s,
        )
        if not isinstance(artifacts_payload, dict):
            raise TrialRunToolError("artifacts payload invalid")
        artifact_items_raw = artifacts_payload.get("items")
        artifact_items = artifact_items_raw if isinstance(artifact_items_raw, list) else []
        recorder.write_json("run_artifacts.json", {"status": "ok", "items": artifact_items})

        step = "viewer-data"
        viewer_payload = _request_json(
            transport=http,
            method="GET",
            url=f"{normalized_config.api_base_url}/projects/{project_id}/runs/{run_id}/viewer-data",
            where="GET /viewer-data",
            expected={200},
            headers=auth_headers,
            timeout=normalized_config.request_timeout_s,
        )
        recorder.write_json("viewer_data.json", {"status": "ok", "viewer_data": viewer_payload})

        step = "artifact-download"
        target_types = {
            "sheet_svg",
            "sheet_dxf",
            "solver_output",
            "run_log",
            "solver_stdout",
            "solver_stderr",
            "runner_meta",
        }
        used_names: set[str] = set()
        for item in artifact_items:
            if not isinstance(item, dict):
                continue
            artifact_type = str(item.get("artifact_type", "")).strip()
            artifact_id = str(item.get("id", "")).strip()
            if artifact_type not in target_types or not artifact_id:
                continue

            try:
                artifact_url_payload = _request_json(
                    transport=http,
                    method="GET",
                    url=f"{normalized_config.api_base_url}/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/url",
                    where=f"GET artifact url artifact_id={artifact_id}",
                    expected={200},
                    headers=auth_headers,
                    timeout=normalized_config.request_timeout_s,
                )
                if not isinstance(artifact_url_payload, dict):
                    raise TrialRunToolError("artifact url payload invalid")
                signed_url = str(artifact_url_payload.get("download_url", "")).strip()
                if not signed_url:
                    raise TrialRunToolError("artifact url missing download_url")

                file_name = _safe_filename(
                    str(item.get("filename", "")),
                    fallback=f"{artifact_type}_{artifact_id}",
                )
                if file_name in used_names:
                    file_name = f"{Path(file_name).stem}_{artifact_id}{Path(file_name).suffix}"
                used_names.add(file_name)

                blob = _request_bytes(
                    transport=http,
                    method="GET",
                    url=signed_url,
                    where=f"download artifact artifact_id={artifact_id}",
                    expected={200},
                    timeout=normalized_config.request_timeout_s,
                )
                local_path = run_dir / file_name
                local_path.write_bytes(blob)

                downloaded_items.append(
                    {
                        "artifact_id": artifact_id,
                        "artifact_type": artifact_type,
                        "filename": file_name,
                        "local_path": str(local_path),
                        "download_url_redacted": _strip_url_query(signed_url),
                        "expires_at": artifact_url_payload.get("expires_at"),
                        "size_bytes": len(blob),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                download_errors.append(
                    {
                        "artifact_id": artifact_id,
                        "artifact_type": artifact_type,
                        "error": str(exc),
                    }
                )
                recorder.log(f"artifact download warning artifact_id={artifact_id} error={exc}")

        if download_errors:
            warnings.append(f"artifact download warnings: {len(download_errors)}")

        recorder.write_json(
            "downloaded_artifact_urls.json",
            {"status": "ok", "items": downloaded_items, "errors": download_errors},
        )

        success = final_run_status == "done"
        if not success:
            warnings.append(f"terminal run status is {final_run_status}")

    except Exception as exc:  # noqa: BLE001
        success = False
        error_message = f"step={step}: {exc}"
        recorder.log(f"ERROR {error_message}")

        recorder.write_json(
            "downloaded_artifact_urls.json",
            {
                "status": "error",
                "items": downloaded_items,
                "errors": download_errors,
                "error": error_message,
            },
        )
    else:
        error_message = None

    summary = _build_summary_markdown(
        success=success,
        run_dir=run_dir,
        project_id=project_id,
        run_id=run_id,
        final_status=final_run_status,
        uploaded_count=len(uploaded_items),
        part_count=len(created_parts),
        downloaded_count=len(downloaded_items),
        token_meta=token_meta,
        warnings=warnings,
        error_message=error_message,
    )
    recorder.write_text("summary.md", summary)

    return TrialRunResult(
        success=success,
        run_dir=run_dir,
        summary_path=run_dir / "summary.md",
        project_id=project_id,
        run_id=run_id,
        final_run_status=final_run_status,
        error_message=error_message,
    )


def _strip_url_query(url: str) -> str:
    parts: SplitResult = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


__all__ = [
    "HttpTransport",
    "RequestsTransport",
    "TrialRunConfig",
    "TrialRunResult",
    "TrialRunToolError",
    "parse_qty_overrides",
    "run_trial",
]
