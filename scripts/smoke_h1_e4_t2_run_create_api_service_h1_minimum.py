#!/usr/bin/env python3
"""H1-E4-T2 smoke: run create API service (H1 minimum)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services import run_creation as run_creation_module  # noqa: E402
from api.services.run_creation import RunCreationError, create_queued_run_from_project_snapshot  # noqa: E402
from api.services.run_snapshot_builder import RunSnapshotBuilderError  # noqa: E402
from api.supabase_client import SupabaseHTTPError  # noqa: E402


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.projects": [],
            "app.nesting_runs": [],
            "app.nesting_run_snapshots": [],
            "app.run_queue": [],
        }
        self.force_snapshot_hash_duplicate_once = False

    @staticmethod
    def _as_text(value: Any) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _match_filter(value: Any, raw_filter: str) -> bool:
        token = raw_filter.strip()
        text = "" if value is None else str(value)
        if token.startswith("eq."):
            return text == token[3:]
        if token.startswith("neq."):
            return text != token[4:]
        return True

    @staticmethod
    def _apply_order(rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
        ordered = list(rows)
        for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
            key = token.split(".")[0]
            reverse = ".desc" in token
            ordered.sort(key=lambda row: str(row.get(key) or ""), reverse=reverse)
        return ordered

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = [dict(row) for row in self.tables.get(table, [])]
        meta_keys = {"select", "order", "limit", "offset"}

        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._match_filter(row.get(key), raw_filter)]

        order_clause = str(params.get("order") or "").strip()
        if order_clause:
            rows = self._apply_order(rows, order_clause)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = params.get("limit", "")
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]
        return [dict(row) for row in rows]

    def _inject_concurrent_snapshot(self, *, project_id: str, snapshot_hash_sha256: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid4())
        snapshot_id = str(uuid4())
        run_row = {
            "id": run_id,
            "project_id": project_id,
            "requested_by": "00000000-0000-0000-0000-000000000001",
            "status": "queued",
            "run_purpose": "nesting",
            "idempotency_key": None,
            "request_payload_jsonb": {},
            "queued_at": now,
            "created_at": now,
            "updated_at": now,
        }
        snapshot_row = {
            "id": snapshot_id,
            "run_id": run_id,
            "status": "ready",
            "snapshot_version": "h1.v1",
            "snapshot_hash_sha256": snapshot_hash_sha256,
            "project_manifest_jsonb": {"project_id": project_id},
            "technology_manifest_jsonb": {"technology_setup_id": "tech-1"},
            "parts_manifest_jsonb": [{"part_revision_id": "part-1"}],
            "sheets_manifest_jsonb": [{"sheet_revision_id": "sheet-1"}],
            "geometry_manifest_jsonb": [{"geometry_revision_id": "geo-1"}],
            "solver_config_jsonb": {"units": "mm"},
            "manufacturing_manifest_jsonb": {"kerf_mm": 0.2},
            "created_by": run_row["requested_by"],
            "created_at": now,
        }
        queue_row = {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "queue_state": "pending",
            "attempt_no": 0,
            "priority": 100,
            "retry_count": 0,
            "available_at": now,
            "created_at": now,
            "updated_at": now,
        }
        self.tables["app.nesting_runs"].append(run_row)
        self.tables["app.nesting_run_snapshots"].append(snapshot_row)
        self.tables["app.run_queue"].append(queue_row)

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)
        now = datetime.now(timezone.utc).isoformat()

        if table == "app.nesting_runs":
            project_id = self._as_text(row.get("project_id"))
            idempotency_key = row.get("idempotency_key")
            if idempotency_key is not None:
                for existing in self.tables["app.nesting_runs"]:
                    if (
                        self._as_text(existing.get("project_id")) == project_id
                        and self._as_text(existing.get("idempotency_key")) == self._as_text(idempotency_key)
                    ):
                        raise SupabaseHTTPError(
                            "duplicate key value violates unique constraint uq_nesting_runs_project_idempotency_key"
                        )
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.tables["app.nesting_runs"].append(row)
            return dict(row)

        if table == "app.nesting_run_snapshots":
            run_id = self._as_text(row.get("run_id"))
            snapshot_hash = self._as_text(row.get("snapshot_hash_sha256"))
            if self.force_snapshot_hash_duplicate_once:
                self.force_snapshot_hash_duplicate_once = False
                run_rows = [item for item in self.tables["app.nesting_runs"] if self._as_text(item.get("id")) == run_id]
                project_id = self._as_text(run_rows[0].get("project_id")) if run_rows else ""
                if project_id:
                    self._inject_concurrent_snapshot(project_id=project_id, snapshot_hash_sha256=snapshot_hash)
                raise SupabaseHTTPError(
                    "duplicate key value violates unique constraint uq_nesting_run_snapshots_snapshot_hash_sha256"
                )

            for existing in self.tables["app.nesting_run_snapshots"]:
                if self._as_text(existing.get("run_id")) == run_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint nesting_run_snapshots_run_id")
                if snapshot_hash and self._as_text(existing.get("snapshot_hash_sha256")) == snapshot_hash:
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint uq_nesting_run_snapshots_snapshot_hash_sha256"
                    )

            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.tables["app.nesting_run_snapshots"].append(row)
            return dict(row)

        if table == "app.run_queue":
            run_id = self._as_text(row.get("run_id"))
            snapshot_id = self._as_text(row.get("snapshot_id"))
            for existing in self.tables["app.run_queue"]:
                if self._as_text(existing.get("run_id")) == run_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint run_queue_pkey")
                if self._as_text(existing.get("snapshot_id")) == snapshot_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint run_queue_snapshot_id_key")
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.tables["app.run_queue"].append(row)
            return dict(row)

        raise RuntimeError(f"unsupported insert table: {table}")

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        if table != "app.nesting_runs":
            return
        run_id_filter = filters.get("id")
        project_id_filter = filters.get("project_id")
        if run_id_filter is None or project_id_filter is None:
            return
        keep_runs: list[dict[str, Any]] = []
        removed_run_ids: set[str] = set()
        for run in self.tables["app.nesting_runs"]:
            run_id = self._as_text(run.get("id"))
            project_id = self._as_text(run.get("project_id"))
            if self._match_filter(run_id, run_id_filter) and self._match_filter(project_id, project_id_filter):
                removed_run_ids.add(run_id)
                continue
            keep_runs.append(run)
        self.tables["app.nesting_runs"] = keep_runs

        if removed_run_ids:
            self.tables["app.nesting_run_snapshots"] = [
                row
                for row in self.tables["app.nesting_run_snapshots"]
                if self._as_text(row.get("run_id")) not in removed_run_ids
            ]
            self.tables["app.run_queue"] = [
                row for row in self.tables["app.run_queue"] if self._as_text(row.get("run_id")) not in removed_run_ids
            ]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _build_snapshot_payload(snapshot_hash_sha256: str) -> dict[str, Any]:
    return {
        "snapshot_version": "h1.v1",
        "snapshot_hash_sha256": snapshot_hash_sha256,
        "project_manifest_jsonb": {"project_id": "p-1", "version": 1},
        "technology_manifest_jsonb": {"technology_setup_id": "tech-1"},
        "parts_manifest_jsonb": [{"part_revision_id": "part-r1", "required_qty": 4}],
        "sheets_manifest_jsonb": [{"sheet_revision_id": "sheet-r1", "required_qty": 2}],
        "geometry_manifest_jsonb": [{"geometry_revision_id": "geo-r1", "derivative_id": "gd-1"}],
        "solver_config_jsonb": {"units": "mm"},
        "manufacturing_manifest_jsonb": {"kerf_mm": 0.2},
    }


def _expect_error(fn: Any, *, status_code: int, detail_contains: str) -> None:
    try:
        fn()
    except RunCreationError as exc:
        if exc.status_code != status_code:
            raise RuntimeError(f"unexpected status code: {exc.status_code} != {status_code}")
        if detail_contains not in exc.detail:
            raise RuntimeError(f"unexpected error detail: {exc.detail!r}")
        return
    raise RuntimeError("expected RunCreationError")


def main() -> int:
    fake = FakeSupabaseClient()
    owner_user_id = "00000000-0000-0000-0000-000000000001"
    another_user_id = "00000000-0000-0000-0000-000000000099"
    project_id = str(uuid4())
    fake.tables["app.projects"].append({"id": project_id, "owner_user_id": owner_user_id, "lifecycle": "active"})

    original_builder = run_creation_module.build_run_snapshot_payload
    payload_holder: dict[str, Any] = _build_snapshot_payload("a" * 64)

    def fake_builder(**kwargs: Any) -> dict[str, Any]:
        _ = kwargs
        return dict(payload_holder)

    run_creation_module.build_run_snapshot_payload = fake_builder

    try:
        created = create_queued_run_from_project_snapshot(
            supabase=fake,
            access_token="token-u1",
            owner_user_id=owner_user_id,
            project_id=project_id,
            run_purpose="laser",
            idempotency_key="idem-1",
        )
        run_row = created["run"]
        snapshot_row = created["snapshot"]
        queue_row = created["queue"]
        _assert(created["was_deduplicated"] is False, "fresh create should not be deduplicated")
        _assert(created["dedup_reason"] is None, "fresh create should not have dedup reason")
        _assert(run_row["status"] == "queued", "run status should be queued")
        _assert(run_row["run_purpose"] == "laser", "run_purpose should be persisted")
        _assert(snapshot_row["status"] == "ready", "snapshot status should be ready")
        _assert(snapshot_row["snapshot_hash_sha256"] == "a" * 64, "snapshot hash mismatch")
        _assert(queue_row["queue_state"] == "pending", "queue state should be pending")
        _assert(len(fake.tables["app.nesting_runs"]) == 1, "expected one run row after first create")
        _assert(len(fake.tables["app.nesting_run_snapshots"]) == 1, "expected one snapshot row after first create")
        _assert(len(fake.tables["app.run_queue"]) == 1, "expected one queue row after first create")

        dedup_by_key = create_queued_run_from_project_snapshot(
            supabase=fake,
            access_token="token-u1",
            owner_user_id=owner_user_id,
            project_id=project_id,
            run_purpose="laser",
            idempotency_key="idem-1",
        )
        _assert(dedup_by_key["was_deduplicated"] is True, "idempotency call should be deduplicated")
        _assert(dedup_by_key["dedup_reason"] == "idempotency_key", "idempotency dedup reason mismatch")
        _assert(dedup_by_key["run"]["id"] == run_row["id"], "idempotency should return original run")
        _assert(len(fake.tables["app.nesting_runs"]) == 1, "idempotency must not create new run")

        dedup_by_hash = create_queued_run_from_project_snapshot(
            supabase=fake,
            access_token="token-u1",
            owner_user_id=owner_user_id,
            project_id=project_id,
            run_purpose="laser",
            idempotency_key=None,
        )
        _assert(dedup_by_hash["was_deduplicated"] is True, "snapshot-hash call should be deduplicated")
        _assert(dedup_by_hash["dedup_reason"] == "snapshot_hash", "snapshot hash dedup reason mismatch")
        _assert(dedup_by_hash["run"]["id"] == run_row["id"], "snapshot-hash dedup should return original run")
        _assert(len(fake.tables["app.nesting_runs"]) == 1, "snapshot hash dedup must not create new run")

        def builder_error(**kwargs: Any) -> dict[str, Any]:
            _ = kwargs
            raise RunSnapshotBuilderError(status_code=422, detail="snapshot builder failed")

        run_creation_module.build_run_snapshot_payload = builder_error
        runs_before_error = len(fake.tables["app.nesting_runs"])
        _expect_error(
            lambda: create_queued_run_from_project_snapshot(
                supabase=fake,
                access_token="token-u1",
                owner_user_id=owner_user_id,
                project_id=project_id,
                run_purpose="laser",
                idempotency_key="idem-error",
            ),
            status_code=422,
            detail_contains="snapshot builder failed",
        )
        _assert(len(fake.tables["app.nesting_runs"]) == runs_before_error, "builder error must not insert run")

        run_creation_module.build_run_snapshot_payload = fake_builder
        _expect_error(
            lambda: create_queued_run_from_project_snapshot(
                supabase=fake,
                access_token="token-u1",
                owner_user_id=another_user_id,
                project_id=project_id,
                run_purpose="laser",
                idempotency_key="idem-foreign",
            ),
            status_code=404,
            detail_contains="project not found",
        )

        payload_holder = _build_snapshot_payload("b" * 64)
        fake.force_snapshot_hash_duplicate_once = True
        dedup_race = create_queued_run_from_project_snapshot(
            supabase=fake,
            access_token="token-u1",
            owner_user_id=owner_user_id,
            project_id=project_id,
            run_purpose="nesting",
            idempotency_key="idem-race",
        )
        _assert(dedup_race["was_deduplicated"] is True, "snapshot hash race should deduplicate")
        _assert(dedup_race["dedup_reason"] == "snapshot_hash_race", "snapshot hash race reason mismatch")
        _assert(
            all(str(row.get("idempotency_key") or "") != "idem-race" for row in fake.tables["app.nesting_runs"]),
            "snapshot hash race should cleanup transient run",
        )
    finally:
        run_creation_module.build_run_snapshot_payload = original_builder

    print("PASS: H1-E4-T2 run create service smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
