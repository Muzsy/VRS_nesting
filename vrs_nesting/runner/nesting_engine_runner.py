#!/usr/bin/env python3
"""Deterministic nesting_engine runner with stdin/stdout contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from vrs_nesting.run_artifacts.run_dir import create_run_dir


class NestingEngineRunnerError(RuntimeError):
    """Base runner error."""


class NestingEngineBinaryNotFoundError(NestingEngineRunnerError):
    """Raised when nesting_engine binary cannot be resolved."""


class NestingEngineNonZeroExitError(NestingEngineRunnerError):
    """Raised when nesting_engine exits with non-zero status."""


class NestingEngineOutputParseError(NestingEngineRunnerError):
    """Raised when nesting_engine stdout is not valid JSON output."""


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_nesting_engine_bin(explicit_bin: str | None = None) -> str:
    candidates: list[str] = []
    if explicit_bin:
        candidates.append(explicit_bin)
    env_bin = os.environ.get("NESTING_ENGINE_BIN")
    if env_bin:
        candidates.append(env_bin)
    candidates.append("nesting_engine")

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return str(Path(resolved).resolve())
        candidate_path = Path(candidate)
        if candidate_path.is_file() and os.access(candidate_path, os.X_OK):
            return str(candidate_path.resolve())
    raise NestingEngineBinaryNotFoundError(
        "nesting_engine binary not found. Use --nesting-engine-bin or set NESTING_ENGINE_BIN."
    )


def run_nesting_engine(
    input_path: str,
    *,
    seed: int,
    time_limit_sec: int,
    run_root: str = "runs",
    nesting_engine_bin: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    input_json = Path(input_path).resolve()
    if not input_json.is_file():
        raise NestingEngineRunnerError(f"Input JSON not found: {input_json}")

    input_data: dict[str, Any]
    try:
        input_data = json.loads(input_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise NestingEngineRunnerError(f"Input JSON parse failed: {input_json}: {exc}") from exc
    if not isinstance(input_data, dict):
        raise NestingEngineRunnerError("Input JSON top-level object required")

    input_data["seed"] = int(seed)
    input_data["time_limit_sec"] = int(time_limit_sec)
    input_payload = json.dumps(input_data, separators=(",", ":"), ensure_ascii=False)
    input_bytes = input_payload.encode("utf-8")

    run_ctx = create_run_dir(run_root=run_root)
    run_dir = run_ctx.run_dir
    input_snapshot_path = run_dir / "nesting_input.json"
    input_snapshot_path.write_text(json.dumps(input_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_path = run_dir / "nesting_output.json"
    stdout_log = run_dir / "solver_stdout.log"
    stderr_log = run_dir / "solver_stderr.log"
    meta_path = run_dir / "runner_meta.json"

    bin_path = resolve_nesting_engine_bin(nesting_engine_bin)
    cmd = [bin_path, "nest"]
    _eprint(f"[nesting-engine-runner] run_dir={run_dir}")
    _eprint(f"[nesting-engine-runner] cmd={' '.join(cmd)}")

    started_at = _utc_now_iso()
    started = monotonic()
    try:
        proc = subprocess.run(
            cmd,
            input=input_payload,
            capture_output=True,
            text=True,
            timeout=max(1.0, float(time_limit_sec) + 5.0),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise NestingEngineNonZeroExitError(
            f"nesting_engine timed out after {time_limit_sec + 5}s"
        ) from exc

    elapsed_sec = round(monotonic() - started, 3)
    ended_at = _utc_now_iso()

    stdout_log.write_text(proc.stdout, encoding="utf-8")
    stderr_log.write_text(proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        meta = {
            "run_id": run_ctx.run_id,
            "run_dir": str(run_dir),
            "return_code": int(proc.returncode),
            "started_at_utc": started_at,
            "ended_at_utc": ended_at,
            "elapsed_sec": elapsed_sec,
            "input_sha256": _sha256_bytes(input_bytes),
            "output_sha256": "",
            "determinism_hash": "",
            "solver_version": "",
        }
        _write_json(meta_path, meta)
        raise NestingEngineNonZeroExitError(
            f"nesting_engine exited with {proc.returncode}. run_dir={run_dir}"
        )

    try:
        out_data = json.loads(proc.stdout)
    except Exception as exc:  # noqa: BLE001
        raise NestingEngineOutputParseError(f"nesting_engine stdout parse failed: {exc}") from exc
    if not isinstance(out_data, dict):
        raise NestingEngineOutputParseError("nesting_engine output top-level object required")

    output_path.write_text(json.dumps(out_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    meta = {
        "run_id": run_ctx.run_id,
        "run_dir": str(run_dir),
        "solver_version": str(out_data.get("solver_version", "")),
        "input_sha256": _sha256_file(input_snapshot_path),
        "output_sha256": _sha256_file(output_path),
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "elapsed_sec": elapsed_sec,
        "return_code": int(proc.returncode),
        "determinism_hash": str(out_data.get("meta", {}).get("determinism_hash", "")),
    }
    _write_json(meta_path, meta)
    return run_dir, meta


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run nesting_engine and store artifacts in runs/<run_id>/")
    parser.add_argument("--input", required=True, help="Path to io_contract_v2 input JSON")
    parser.add_argument("--seed", type=int, required=True, help="Deterministic seed")
    parser.add_argument("--time-limit", type=int, required=True, help="Time limit in seconds")
    parser.add_argument("--run-root", default="runs", help="Root directory for run artifacts")
    parser.add_argument("--nesting-engine-bin", default=None, help="Explicit nesting_engine binary path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        run_dir, _meta = run_nesting_engine(
            args.input,
            seed=args.seed,
            time_limit_sec=args.time_limit,
            run_root=args.run_root,
            nesting_engine_bin=args.nesting_engine_bin,
        )
    except NestingEngineRunnerError as exc:
        _eprint(f"ERROR: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        _eprint(f"ERROR: Unexpected runner error: {exc}")
        return 2
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
