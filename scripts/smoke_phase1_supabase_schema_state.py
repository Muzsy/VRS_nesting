#!/usr/bin/env python3
"""Smoke check for Phase 1 Supabase schema + RLS state."""

from __future__ import annotations

import os
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


def main() -> int:
    candidates = _build_connection_candidates()

    required_tables = [
        "users",
        "projects",
        "project_files",
        "run_configs",
        "runs",
        "run_artifacts",
        "run_queue",
    ]

    table_sql = (
        "select tablename from pg_tables "
        "where schemaname='public' and tablename in ('users','projects','project_files','run_configs','runs','run_artifacts','run_queue') "
        "order by tablename;"
    )
    table_out, table_source = _run_psql_with_fallback(candidates, table_sql)
    found_tables = [line.strip() for line in table_out.splitlines() if line.strip()]

    missing = [table for table in required_tables if table not in found_tables]
    if missing:
        raise RuntimeError(f"missing phase1 tables: {missing}")

    rls_sql = (
        "select relname, relrowsecurity from pg_class "
        "where relname in ('users','projects','project_files','run_configs','runs','run_artifacts','run_queue') "
        "order by relname;"
    )
    rls_out, _ = _run_psql_with_fallback(candidates, rls_sql)
    rows = [line.strip() for line in rls_out.splitlines() if line.strip()]

    for row in rows:
        relname, flag = row.split("|", 1)
        if flag.strip().lower() != "t":
            raise RuntimeError(f"RLS not enabled on table: {relname}")

    print("[OK] Phase 1 Supabase schema+RLS smoke passed")
    print(" source:", table_source)
    print(" tables:", ", ".join(required_tables))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
