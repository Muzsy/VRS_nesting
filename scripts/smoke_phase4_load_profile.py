#!/usr/bin/env python3
"""Phase 4 load profile smoke (in-process ASGI with mocked backend)."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser, get_current_user
from api.config import Settings
from api.deps import get_settings, get_supabase_client
from api.main import create_app


USER_ID = "00000000-0000-0000-0000-000000000001"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"
RUN_CONFIG_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID_FOR_VIEWER = "33333333-3333-3333-3333-333333333333"


def _eq(value: str) -> str:
    return value[3:] if value.startswith("eq.") else value


@dataclass
class _Result:
    ok: bool
    status: int
    latency_ms: float
    payload: dict[str, Any] | None = None


class FakeSupabaseClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: list[dict[str, Any]] = [
            {
                "id": RUN_ID_FOR_VIEWER,
                "project_id": PROJECT_ID,
                "run_config_id": RUN_CONFIG_ID,
                "triggered_by": USER_ID,
                "status": "done",
                "queued_at": "2026-02-19T00:00:00Z",
                "started_at": "2026-02-19T00:00:01Z",
                "finished_at": "2026-02-19T00:00:02Z",
                "duration_sec": 1.0,
                "solver_exit_code": 0,
                "error_message": None,
                "placements_count": 10,
                "unplaced_count": 0,
                "sheet_count": 1,
            }
        ]
        self._quota_usage = 0

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:  # noqa: ARG002
        if table == "projects":
            project_id = _eq(params.get("id", ""))
            owner_id = _eq(params.get("owner_id", USER_ID))
            if project_id == PROJECT_ID and owner_id == USER_ID:
                return [{"id": PROJECT_ID}]
            return []

        if table == "run_configs":
            run_config_id = _eq(params.get("id", ""))
            project_id = _eq(params.get("project_id", ""))
            if run_config_id == RUN_CONFIG_ID and project_id == PROJECT_ID:
                return [{"id": RUN_CONFIG_ID}]
            return []

        if table == "runs":
            run_id = params.get("id")
            project_id = params.get("project_id")
            with self._lock:
                rows = list(self._runs)
            if run_id:
                rows = [row for row in rows if row["id"] == _eq(run_id)]
            if project_id:
                rows = [row for row in rows if row["project_id"] == _eq(project_id)]
            return rows

        if table == "run_artifacts":
            run_id = _eq(params.get("run_id", ""))
            if run_id == RUN_ID_FOR_VIEWER:
                return []
            return []

        return []

    def execute_rpc(self, *, function_name: str, access_token: str, payload: dict[str, Any]) -> Any:  # noqa: ARG002
        if function_name != "enqueue_run_with_quota":
            raise RuntimeError(f"unexpected function_name={function_name}")
        project_id = str(payload.get("p_project_id", ""))
        triggered_by = str(payload.get("p_triggered_by", ""))
        run_config_id = str(payload.get("p_run_config_id", ""))
        if project_id != PROJECT_ID or triggered_by != USER_ID:
            raise RuntimeError("project/user mismatch")

        with self._lock:
            if self._quota_usage >= 1000:
                raise RuntimeError("quota_exceeded")
            self._quota_usage += 1
            run_id = f"run-load-{self._quota_usage:04d}"
            run = {
                "id": run_id,
                "project_id": PROJECT_ID,
                "run_config_id": run_config_id or RUN_CONFIG_ID,
                "triggered_by": USER_ID,
                "status": "queued",
                "queued_at": "2026-02-19T00:00:00Z",
                "started_at": None,
                "finished_at": None,
                "duration_sec": None,
                "solver_exit_code": None,
                "error_message": None,
                "placements_count": None,
                "unplaced_count": None,
                "sheet_count": None,
            }
            self._runs.append(run)
            return run

    def create_signed_download_url(self, *, access_token: str, bucket: str, object_key: str, expires_in: int) -> dict[str, str]:  # noqa: ARG002
        return {
            "download_url": f"https://example.invalid/{bucket}/{object_key}",
            "expires_at": "2026-12-31T23:59:59Z",
        }

    def download_signed_object(self, *, signed_url: str) -> bytes:  # noqa: ARG002
        return b"{}"

    def create_signed_upload_url(self, *, access_token: str, bucket: str, object_key: str, expires_in: int) -> dict[str, str]:  # noqa: ARG002
        return {
            "upload_url": f"https://example.invalid/upload/{bucket}/{object_key}",
            "expires_at": "2026-12-31T23:59:59Z",
        }

    def upload_signed_object_from_file(self, *, signed_url: str, file_path: str, content_type: str) -> None:  # noqa: ARG002
        return None

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        return payload

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:  # noqa: ARG002
        return []

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:  # noqa: ARG002
        return None

    def remove_object(self, *, access_token: str, bucket: str, object_key: str) -> None:  # noqa: ARG002
        return None


def _build_settings() -> Settings:
    return Settings(
        supabase_url="https://example.invalid",
        supabase_anon_key="anon",
        supabase_project_ref="proj",
        supabase_db_password="",
        database_url="",
        storage_bucket="vrs-nesting",
        max_dxf_size_mb=50,
        rate_limit_window_s=60,
        rate_limit_runs_per_window=1000,
        rate_limit_bundles_per_window=1000,
        rate_limit_upload_urls_per_window=1000,
        signed_url_ttl_s=300,
        enable_security_headers=True,
        allowed_origins=("http://localhost:5173",),
    )


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    idx = max(0, min(len(values) - 1, int(round((p / 100.0) * (len(values) - 1)))))
    ordered = sorted(values)
    return ordered[idx]


async def _request_with_latency(client: httpx.AsyncClient, method: str, path: str, json_payload: dict[str, Any] | None = None) -> _Result:
    started = time.perf_counter()
    response = await client.request(method=method, url=path, json=json_payload, headers={"Authorization": "Bearer fake-token"})
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    payload: dict[str, Any] | None = None
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:  # noqa: BLE001
            payload = None
    return _Result(ok=response.status_code < 400, status=response.status_code, latency_ms=elapsed_ms, payload=payload)


async def _run_profile(concurrent_runs: int, concurrent_viewers: int) -> tuple[list[_Result], list[_Result]]:
    app = create_app()
    fake_client = FakeSupabaseClient()
    settings = _build_settings()
    auth_user = AuthenticatedUser(id=USER_ID, email="load@test.local", access_token="fake-token")

    app.dependency_overrides[get_supabase_client] = lambda: fake_client
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_current_user] = lambda: auth_user

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        run_tasks = [
            _request_with_latency(
                client,
                "POST",
                f"/v1/projects/{PROJECT_ID}/runs",
                {"run_config_id": RUN_CONFIG_ID},
            )
            for _ in range(concurrent_runs)
        ]
        run_results = await asyncio.gather(*run_tasks)

        viewer_tasks = [
            _request_with_latency(
                client,
                "GET",
                f"/v1/projects/{PROJECT_ID}/runs/{RUN_ID_FOR_VIEWER}/viewer-data",
            )
            for _ in range(concurrent_viewers)
        ]
        viewer_results = await asyncio.gather(*viewer_tasks)

    app.dependency_overrides.clear()
    return run_results, viewer_results


def _summarize(results: list[_Result]) -> dict[str, float]:
    latencies = [item.latency_ms for item in results]
    ok_count = sum(1 for item in results if item.ok)
    total = len(results)
    err_rate = 0.0 if total == 0 else ((total - ok_count) / total) * 100.0
    return {
        "count": float(total),
        "ok": float(ok_count),
        "error_rate_pct": round(err_rate, 3),
        "p50_ms": round(_percentile(latencies, 50), 3),
        "p95_ms": round(_percentile(latencies, 95), 3),
        "max_ms": round(max(latencies) if latencies else 0.0, 3),
        "avg_ms": round(statistics.mean(latencies) if latencies else 0.0, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 load profile smoke")
    parser.add_argument("--runs", type=int, default=10, help="concurrent POST /runs calls")
    parser.add_argument("--viewers", type=int, default=50, help="concurrent viewer-data calls")
    args = parser.parse_args()

    run_results, viewer_results = asyncio.run(_run_profile(concurrent_runs=args.runs, concurrent_viewers=args.viewers))
    run_summary = _summarize(run_results)
    viewer_summary = _summarize(viewer_results)
    run_ids = [str(item.payload.get("id", "")) for item in run_results if item.payload and item.payload.get("id")]
    unique_run_ids = len(set(run_ids))
    duplicate_count = len(run_ids) - unique_run_ids

    print("[OK] Phase 4 load profile smoke completed")
    print(f" runs: {run_summary}")
    print(f" run_ids: total={len(run_ids)} unique={unique_run_ids} duplicates={duplicate_count}")
    print(f" viewers: {viewer_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
