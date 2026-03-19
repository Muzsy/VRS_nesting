from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ManagementQueryFn = Callable[[str], list[dict[str, Any]]]


@dataclass(frozen=True)
class QueueLeaseClaim:
    run_id: str
    snapshot_id: str
    attempt_no: int
    lease_token: str
    lease_expires_at: str
    max_attempts: int

    def as_worker_item(self) -> dict[str, Any]:
        return {
            "id": self.run_id,
            "run_id": self.run_id,
            "snapshot_id": self.snapshot_id,
            "attempts": self.attempt_no,
            "max_attempts": self.max_attempts,
            "lease_token": self.lease_token,
            "lease_expires_at": self.lease_expires_at,
        }


@dataclass(frozen=True)
class QueueLeaseHeartbeat:
    run_id: str
    snapshot_id: str
    attempt_no: int
    lease_token: str
    lease_expires_at: str
    heartbeat_at: str


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _normalize_positive_int(value: int, *, name: str) -> int:
    out = int(value)
    if out <= 0:
        raise ValueError(f"{name} must be > 0")
    return out


def claim_next_queue_lease(
    *,
    query: ManagementQueryFn,
    worker_id: str,
    lease_ttl_seconds: int,
    max_attempts: int = 3,
) -> QueueLeaseClaim | None:
    worker_id_clean = worker_id.strip()
    if not worker_id_clean:
        raise ValueError("worker_id must not be empty")

    lease_ttl_s = _normalize_positive_int(lease_ttl_seconds, name="lease_ttl_seconds")
    max_attempts_clean = _normalize_positive_int(max_attempts, name="max_attempts")

    sql = f"""
with candidate as (
  select q.run_id
  from app.run_queue q
  join app.nesting_runs r on r.id = q.run_id
  where q.available_at <= now()
    and (
      q.queue_state = 'pending'
      or (
        q.queue_state = 'leased'
        and (
          (q.lease_expires_at is not null and q.lease_expires_at <= now())
          or (
            q.lease_expires_at is null
            and q.leased_at is not null
            and q.leased_at < now() - interval '{lease_ttl_s} seconds'
          )
        )
      )
    )
    and r.status::text in ('queued', 'running')
  order by q.priority desc, q.available_at asc, q.created_at asc
  for update skip locked
  limit 1
),
claimed as (
  update app.run_queue q
  set leased_by = {_sql_literal(worker_id_clean)},
      lease_token = gen_random_uuid(),
      leased_at = now(),
      heartbeat_at = now(),
      lease_expires_at = now() + interval '{lease_ttl_s} seconds',
      queue_state = 'leased',
      attempt_no = q.attempt_no + 1,
      attempt_status = 'leased'::app.run_attempt_status,
      updated_at = now()
  from candidate c
  where q.run_id = c.run_id
  returning
    q.run_id,
    q.snapshot_id,
    q.attempt_no,
    q.lease_token::text as lease_token,
    q.lease_expires_at
)
select
  c.run_id,
  c.snapshot_id,
  c.attempt_no,
  c.lease_token,
  c.lease_expires_at,
  {max_attempts_clean}::integer as max_attempts
from claimed c;
"""
    rows = query(sql)
    if not rows:
        return None

    row = rows[0]
    run_id = str(row.get("run_id") or "").strip()
    snapshot_id = str(row.get("snapshot_id") or "").strip()
    lease_token = str(row.get("lease_token") or "").strip()
    lease_expires_at = str(row.get("lease_expires_at") or "").strip()
    attempt_no = int(row.get("attempt_no") or 0)
    max_attempts_row = int(row.get("max_attempts") or max_attempts_clean)
    if not run_id or not snapshot_id or not lease_token or not lease_expires_at:
        raise RuntimeError("claim_next_queue_lease returned incomplete row")
    if attempt_no <= 0:
        raise RuntimeError("claim_next_queue_lease returned invalid attempt_no")

    return QueueLeaseClaim(
        run_id=run_id,
        snapshot_id=snapshot_id,
        attempt_no=attempt_no,
        lease_token=lease_token,
        lease_expires_at=lease_expires_at,
        max_attempts=max_attempts_row,
    )


def heartbeat_queue_lease(
    *,
    query: ManagementQueryFn,
    run_id: str,
    worker_id: str,
    lease_token: str,
    lease_ttl_seconds: int,
) -> QueueLeaseHeartbeat | None:
    run_id_clean = run_id.strip()
    worker_id_clean = worker_id.strip()
    lease_token_clean = lease_token.strip()
    if not run_id_clean:
        raise ValueError("run_id must not be empty")
    if not worker_id_clean:
        raise ValueError("worker_id must not be empty")
    if not lease_token_clean:
        raise ValueError("lease_token must not be empty")

    lease_ttl_s = _normalize_positive_int(lease_ttl_seconds, name="lease_ttl_seconds")

    sql = f"""
update app.run_queue
set heartbeat_at = now(),
    lease_expires_at = now() + interval '{lease_ttl_s} seconds',
    updated_at = now()
where run_id = {_sql_literal(run_id_clean)}
  and queue_state = 'leased'
  and leased_by = {_sql_literal(worker_id_clean)}
  and lease_token = {_sql_literal(lease_token_clean)}::uuid
  and lease_expires_at > now()
returning
  run_id,
  snapshot_id,
  attempt_no,
  lease_token::text as lease_token,
  lease_expires_at,
  heartbeat_at;
"""
    rows = query(sql)
    if not rows:
        return None

    row = rows[0]
    heartbeat = QueueLeaseHeartbeat(
        run_id=str(row.get("run_id") or "").strip(),
        snapshot_id=str(row.get("snapshot_id") or "").strip(),
        attempt_no=int(row.get("attempt_no") or 0),
        lease_token=str(row.get("lease_token") or "").strip(),
        lease_expires_at=str(row.get("lease_expires_at") or "").strip(),
        heartbeat_at=str(row.get("heartbeat_at") or "").strip(),
    )
    if (
        not heartbeat.run_id
        or not heartbeat.snapshot_id
        or not heartbeat.lease_token
        or not heartbeat.lease_expires_at
        or not heartbeat.heartbeat_at
        or heartbeat.attempt_no <= 0
    ):
        raise RuntimeError("heartbeat_queue_lease returned incomplete row")
    return heartbeat
