#!/usr/bin/env python3
"""H1-E4-T3 smoke: queue lease mechanika (H1 minimum)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.queue_lease import claim_next_queue_lease, heartbeat_queue_lease  # noqa: E402


class FakeQueueDB:
    def __init__(self) -> None:
        self.now = datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc)
        self.runs: dict[str, dict[str, Any]] = {}
        self.run_queue: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _extract(pattern: str, sql: str) -> str:
        match = re.search(pattern, sql, flags=re.IGNORECASE)
        if not match:
            raise RuntimeError(f"missing SQL token for pattern: {pattern}")
        return str(match.group(1))

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=int(seconds))

    def add_queue_item(
        self,
        *,
        run_id: str,
        snapshot_id: str,
        run_status: str,
        queue_state: str = "pending",
        priority: int = 100,
        attempt_no: int = 0,
        lease_expires_at: datetime | None = None,
    ) -> None:
        now = self.now
        self.runs[run_id] = {"id": run_id, "status": run_status}
        self.run_queue[run_id] = {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "queue_state": queue_state,
            "attempt_no": int(attempt_no),
            "attempt_status": None,
            "priority": int(priority),
            "available_at": now,
            "leased_by": None,
            "lease_token": None,
            "leased_at": None,
            "lease_expires_at": lease_expires_at,
            "heartbeat_at": None,
            "created_at": now,
            "updated_at": now,
        }

    def _iso(self, value: datetime | None) -> str:
        if value is None:
            return ""
        return value.isoformat()

    def _claim(self, sql: str) -> list[dict[str, Any]]:
        worker_id = self._extract(r"leased_by\s*=\s*'([^']+)'", sql)
        lease_ttl_s = int(self._extract(r"interval\s*'(\d+)\s+seconds'", sql))
        max_attempts = int(self._extract(r"(\d+)::integer\s+as\s+max_attempts", sql))

        eligible: list[dict[str, Any]] = []
        for row in self.run_queue.values():
            run_status = str(self.runs.get(str(row["run_id"]), {}).get("status") or "").strip().lower()
            if run_status not in {"queued", "running"}:
                continue
            if row["available_at"] > self.now:
                continue

            queue_state = str(row["queue_state"])
            if queue_state == "pending":
                eligible.append(row)
                continue

            if queue_state == "leased":
                lease_expires_at = row.get("lease_expires_at")
                if isinstance(lease_expires_at, datetime) and lease_expires_at <= self.now:
                    eligible.append(row)

        if not eligible:
            return []

        eligible.sort(
            key=lambda row: (
                -int(row.get("priority") or 0),
                self._iso(row.get("available_at")),
                self._iso(row.get("created_at")),
            )
        )
        picked = eligible[0]
        picked["queue_state"] = "leased"
        picked["attempt_no"] = int(picked.get("attempt_no") or 0) + 1
        picked["attempt_status"] = "leased"
        picked["leased_by"] = worker_id
        picked["lease_token"] = str(uuid4())
        picked["leased_at"] = self.now
        picked["heartbeat_at"] = self.now
        picked["lease_expires_at"] = self.now + timedelta(seconds=lease_ttl_s)
        picked["updated_at"] = self.now

        return [
            {
                "run_id": picked["run_id"],
                "snapshot_id": picked["snapshot_id"],
                "attempt_no": picked["attempt_no"],
                "lease_token": picked["lease_token"],
                "lease_expires_at": self._iso(picked["lease_expires_at"]),
                "max_attempts": max_attempts,
            }
        ]

    def _heartbeat(self, sql: str) -> list[dict[str, Any]]:
        run_id = self._extract(r"where\s+run_id\s*=\s*'([^']+)'", sql)
        worker_id = self._extract(r"leased_by\s*=\s*'([^']+)'", sql)
        lease_token = self._extract(r"lease_token\s*=\s*'([^']+)'\s*::uuid", sql)
        lease_ttl_s = int(self._extract(r"interval\s*'(\d+)\s+seconds'", sql))

        row = self.run_queue.get(run_id)
        if row is None:
            return []
        if str(row.get("queue_state")) != "leased":
            return []
        if str(row.get("leased_by") or "") != worker_id:
            return []
        if str(row.get("lease_token") or "") != lease_token:
            return []
        lease_expires_at = row.get("lease_expires_at")
        if not isinstance(lease_expires_at, datetime) or lease_expires_at <= self.now:
            return []

        row["heartbeat_at"] = self.now
        row["lease_expires_at"] = self.now + timedelta(seconds=lease_ttl_s)
        row["updated_at"] = self.now
        return [
            {
                "run_id": row["run_id"],
                "snapshot_id": row["snapshot_id"],
                "attempt_no": row["attempt_no"],
                "lease_token": row["lease_token"],
                "lease_expires_at": self._iso(row["lease_expires_at"]),
                "heartbeat_at": self._iso(row["heartbeat_at"]),
            }
        ]

    def management_query(self, sql: str) -> list[dict[str, Any]]:
        normalized = " ".join(sql.strip().split())
        if "with candidate as" in normalized and "for update skip locked" in normalized:
            return self._claim(sql)
        if "update app.run_queue" in normalized and "set heartbeat_at = now()" in normalized:
            return self._heartbeat(sql)
        raise RuntimeError(f"unsupported SQL branch in fake db: {normalized[:160]}")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    fake = FakeQueueDB()
    run_id = str(uuid4())
    snapshot_id = str(uuid4())
    fake.add_queue_item(run_id=run_id, snapshot_id=snapshot_id, run_status="queued")

    claim_a = claim_next_queue_lease(
        query=fake.management_query,
        worker_id="worker-a",
        lease_ttl_seconds=120,
        max_attempts=3,
    )
    _assert(claim_a is not None, "pending queue item should be claimable")
    _assert(claim_a.run_id == run_id, "claimed run_id mismatch")
    _assert(claim_a.snapshot_id == snapshot_id, "claimed snapshot_id mismatch")
    _assert(bool(claim_a.lease_token), "claim should contain lease_token")
    _assert(bool(claim_a.lease_expires_at), "claim should contain lease_expires_at")
    _assert(claim_a.attempt_no == 1, "first claim should set attempt_no=1")

    claim_b_while_leased = claim_next_queue_lease(
        query=fake.management_query,
        worker_id="worker-b",
        lease_ttl_seconds=120,
        max_attempts=3,
    )
    _assert(claim_b_while_leased is None, "active lease must block second claim")

    bad_token_hb = heartbeat_queue_lease(
        query=fake.management_query,
        run_id=run_id,
        worker_id="worker-a",
        lease_token=str(uuid4()),
        lease_ttl_seconds=120,
    )
    _assert(bad_token_hb is None, "heartbeat with wrong token must fail")

    wrong_worker_hb = heartbeat_queue_lease(
        query=fake.management_query,
        run_id=run_id,
        worker_id="worker-b",
        lease_token=claim_a.lease_token,
        lease_ttl_seconds=120,
    )
    _assert(wrong_worker_hb is None, "heartbeat with wrong worker must fail")

    good_hb = heartbeat_queue_lease(
        query=fake.management_query,
        run_id=run_id,
        worker_id="worker-a",
        lease_token=claim_a.lease_token,
        lease_ttl_seconds=120,
    )
    _assert(good_hb is not None, "heartbeat with correct token should succeed")
    _assert(good_hb.attempt_no == 1, "heartbeat must keep attempt_no")

    fake.advance(121)
    claim_b_after_expiry = claim_next_queue_lease(
        query=fake.management_query,
        worker_id="worker-b",
        lease_ttl_seconds=120,
        max_attempts=3,
    )
    _assert(claim_b_after_expiry is not None, "expired lease should be reclaimable")
    _assert(claim_b_after_expiry.attempt_no == 2, "reclaim should increment attempt_no")
    _assert(claim_b_after_expiry.lease_token != claim_a.lease_token, "reclaim must rotate lease_token")

    lost_lease_hb = heartbeat_queue_lease(
        query=fake.management_query,
        run_id=run_id,
        worker_id="worker-a",
        lease_token=claim_a.lease_token,
        lease_ttl_seconds=120,
    )
    _assert(lost_lease_hb is None, "old owner/token heartbeat must fail after reclaim")

    claim_third_while_b_leased = claim_next_queue_lease(
        query=fake.management_query,
        worker_id="worker-c",
        lease_ttl_seconds=120,
        max_attempts=3,
    )
    _assert(claim_third_while_b_leased is None, "reclaimed active lease must block third worker")

    print("PASS: H1-E4-T3 queue lease smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
