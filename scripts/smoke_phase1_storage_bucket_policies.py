#!/usr/bin/env python3
"""Smoke check for Phase 1 storage bucket + policy state."""

from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def _resolve_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if value:
        return value
    for dotfile in (ROOT / ".env.local", ROOT / ".env"):
        value = _load_dotenv(dotfile).get(key, "").strip()
        if value:
            return value
    return ""


def _build_connection_candidates() -> list[tuple[str, dict[str, str], str]]:
    candidates: list[tuple[str, dict[str, str], str]] = []

    database_url = _resolve_env("DATABASE_URL")
    if database_url:
        candidates.append((database_url, dict(os.environ), "DATABASE_URL"))

    pooler_url = _resolve_env("SUPABASE_POOLER_URL")
    if pooler_url:
        pooler_env = dict(os.environ)
        db_password = _resolve_env("SUPABASE_DB_PASSWORD")
        if db_password and "PGPASSWORD" not in pooler_env:
            pooler_env["PGPASSWORD"] = db_password
        candidates.append((pooler_url, pooler_env, "SUPABASE_POOLER_URL"))

    project_ref = _resolve_env("SUPABASE_PROJECT_REF")
    db_password = _resolve_env("SUPABASE_DB_PASSWORD")
    if project_ref and db_password:
        conn = f"host=db.{project_ref}.supabase.co port=5432 dbname=postgres user=postgres sslmode=require"
        candidates.append((conn, {**os.environ, "PGPASSWORD": db_password}, "SUPABASE_PROJECT_REF+SUPABASE_DB_PASSWORD"))

    if not candidates:
        raise RuntimeError(
            "missing connection config: set DATABASE_URL or SUPABASE_POOLER_URL or SUPABASE_PROJECT_REF+SUPABASE_DB_PASSWORD"
        )

    return candidates


def _run_psql(conn: str, sql: str, *, env: dict[str, str]) -> str:
    proc = subprocess.run(
        ["psql", conn, "-v", "ON_ERROR_STOP=1", "-X", "-t", "-A", "-c", sql],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "psql failed")
    return proc.stdout.strip()


def _run_psql_with_fallback(candidates: list[tuple[str, dict[str, str], str]], sql: str) -> tuple[str, str]:
    errors: list[str] = []
    for conn, env, source in candidates:
        try:
            return _run_psql(conn, sql, env=env), source
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: {exc}")
    raise RuntimeError("all psql connection attempts failed: " + " | ".join(errors))


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> int:
    candidates = _build_connection_candidates()

    bucket_sql = "select id, public::text from storage.buckets where id='vrs-nesting' limit 1;"
    bucket_out, source = _run_psql_with_fallback(candidates, bucket_sql)
    if not bucket_out.strip():
        raise RuntimeError("missing vrs-nesting bucket")

    bucket_id, is_public = bucket_out.strip().split("|", 1)
    if bucket_id != "vrs-nesting":
        raise RuntimeError(f"unexpected bucket id: {bucket_id}")
    if is_public.strip().lower() != "false":
        raise RuntimeError("bucket must be private (public=false)")

    policy_sql = (
        "select coalesce(json_agg(json_build_object("
        "'policyname', policyname,"
        "'cmd', cmd,"
        "'qual', coalesce(qual, ''),"
        "'with_check', coalesce(with_check, '')"
        ") order by policyname)::text, '[]') "
        "from pg_policies "
        "where schemaname='storage' and tablename='objects' "
        "and policyname in ('vrs_nesting_owner_select','vrs_nesting_owner_insert','vrs_nesting_owner_update','vrs_nesting_owner_delete');"
    )
    policy_out, _ = _run_psql_with_fallback(candidates, policy_sql)
    rows = json.loads(policy_out.strip() or "[]")
    if len(rows) != 4:
        raise RuntimeError(f"expected 4 storage policies, got {len(rows)}")

    expected_cmd = {
        "vrs_nesting_owner_select": "SELECT",
        "vrs_nesting_owner_insert": "INSERT",
        "vrs_nesting_owner_update": "UPDATE",
        "vrs_nesting_owner_delete": "DELETE",
    }

    required_tokens = [
        "bucket_id",
        "vrs-nesting",
        "split_part(",
        "'users'",
        "'projects'",
        "'files'",
        "'runs'",
        "'artifacts'",
        "projects p",
        "runs r",
        "auth.uid()",
    ]

    for row in rows:
        policyname = str(row.get("policyname", "")).strip()
        cmd = str(row.get("cmd", "")).strip()
        qual = str(row.get("qual", ""))
        with_check = str(row.get("with_check", ""))
        want_cmd = expected_cmd.get(policyname)
        if want_cmd is None:
            raise RuntimeError(f"unexpected policy name: {policyname}")
        if cmd.strip().upper() != want_cmd:
            raise RuntimeError(f"policy {policyname} has cmd={cmd}, expected {want_cmd}")

        merged = _normalize(f"{qual} {with_check}")
        for token in required_tokens:
            if _normalize(token) not in merged:
                raise RuntimeError(f"policy {policyname} missing token: {token}")

    print("[OK] Phase 1 storage bucket+policy smoke passed")
    print(" source:", source)
    print(" bucket: vrs-nesting (private)")
    print(" policies:", ", ".join(sorted(expected_cmd.keys())))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
