#!/usr/bin/env python3
"""Deterministic VRS solver runner with per-run artifacts under runs/<run_id>."""

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


class VrsSolverRunnerError(RuntimeError):
    """Base runner error."""


class VrsSolverBinaryNotFoundError(VrsSolverRunnerError):
    """Raised when the solver binary cannot be resolved."""


class VrsSolverNonZeroExitError(VrsSolverRunnerError):
    """Raised when solver exits with non-zero code."""


class VrsSolverOutputNotFoundError(VrsSolverRunnerError):
    """Raised when solver_output.json is missing."""


class VrsSolverOutputParseError(VrsSolverRunnerError):
    """Raised when solver_output.json is invalid JSON."""


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise VrsSolverOutputParseError(f"JSON parse error: {path}: {exc}") from exc

    if not isinstance(loaded, dict):
        raise VrsSolverOutputParseError(f"Top-level JSON object required: {path}")
    return loaded


def resolve_solver_bin(explicit_bin: str | None = None) -> str:
    candidates: list[str] = []
    if explicit_bin:
        candidates.append(explicit_bin)

    env_bin = os.environ.get("VRS_SOLVER_BIN", "").strip()
    if env_bin and env_bin not in candidates:
        candidates.append(env_bin)

    if "vrs_solver" not in candidates:
        candidates.append("vrs_solver")

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return str(Path(resolved).resolve())

        candidate_path = Path(candidate)
        if candidate_path.is_file() and os.access(candidate_path, os.X_OK):
            return str(candidate_path.resolve())

    raise VrsSolverBinaryNotFoundError(
        "Solver binary not found. Use --solver-bin or set VRS_SOLVER_BIN environment variable."
    )


def _validate_contract_fields(input_json: Path, output_json: Path) -> None:
    inp = _read_json(input_json)
    out = _read_json(output_json)

    if inp.get("contract_version") != "v1":
        raise VrsSolverOutputParseError("solver_input.json contract_version must be v1")
    if out.get("contract_version") != "v1":
        raise VrsSolverOutputParseError("solver_output.json contract_version must be v1")


def run_solver(
    input_path: str,
    *,
    seed: int,
    time_limit_s: int,
    run_root: str = "runs",
    solver_bin: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    input_json = Path(input_path).resolve()
    if not input_json.is_file():
        raise VrsSolverRunnerError(f"Input JSON not found: {input_json}")

    bin_path = resolve_solver_bin(solver_bin)

    run_ctx = create_run_dir(run_root=run_root)
    run_dir = run_ctx.run_dir
    snapshot_path = run_dir / "solver_input.json"
    output_path = run_dir / "solver_output.json"
    stdout_log = run_dir / "solver_stdout.log"
    stderr_log = run_dir / "solver_stderr.log"
    meta_path = run_dir / "runner_meta.json"

    shutil.copy2(input_json, snapshot_path)

    cmd = [
        bin_path,
        "--input",
        str(snapshot_path),
        "--output",
        str(output_path),
        "--seed",
        str(int(seed)),
        "--time-limit",
        str(int(time_limit_s)),
    ]

    started = _utc_now_iso()
    started_mono = monotonic()

    _eprint(f"[vrs-runner] run_dir={run_dir}")
    _eprint(f"[vrs-runner] cmd={' '.join(cmd)}")

    with stdout_log.open("w", encoding="utf-8") as out_handle, stderr_log.open("w", encoding="utf-8") as err_handle:
        proc = subprocess.run(
            cmd,
            cwd=run_dir,
            stdout=out_handle,
            stderr=err_handle,
            text=True,
            check=False,
        )

    duration_sec = round(monotonic() - started_mono, 3)
    ended = _utc_now_iso()

    meta: dict[str, Any] = {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "solver_bin": bin_path,
        "cmd": cmd,
        "seed": int(seed),
        "time_limit_s": int(time_limit_s),
        "input_snapshot_path": str(snapshot_path.resolve()),
        "output_path": str(output_path.resolve()),
        "stdout_log_path": str(stdout_log.resolve()),
        "stderr_log_path": str(stderr_log.resolve()),
        "input_sha256": _sha256_file(snapshot_path),
        "output_sha256": "",
        "started_at_utc": started,
        "ended_at_utc": ended,
        "duration_sec": duration_sec,
        "return_code": proc.returncode,
    }

    if proc.returncode != 0:
        _write_json(meta_path, meta)
        raise VrsSolverNonZeroExitError(
            f"Solver process failed (exit={proc.returncode}). run_dir={run_dir}"
        )

    if not output_path.is_file():
        _write_json(meta_path, meta)
        raise VrsSolverOutputNotFoundError(f"Missing solver output: {output_path}")

    _validate_contract_fields(snapshot_path, output_path)
    meta["output_sha256"] = _sha256_file(output_path)
    _write_json(meta_path, meta)
    return run_dir, meta


def _default_seed() -> int:
    return int(os.environ.get("VRS_SOLVER_SEED", "0"))


def _default_time_limit() -> int:
    return int(os.environ.get("VRS_SOLVER_TIME_LIMIT_S", "60"))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run VRS solver and store artifacts in runs/<run_id>/")
    parser.add_argument("--input", required=True, help="Path to solver input JSON")
    parser.add_argument("--seed", type=int, default=_default_seed(), help="Solver seed")
    parser.add_argument("--time-limit", type=int, default=_default_time_limit(), help="Time limit in seconds")
    parser.add_argument("--run-root", default="runs", help="Root directory for run artifacts")
    parser.add_argument("--solver-bin", default=None, help="Explicit solver binary path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_dir, _meta = run_solver(
            args.input,
            seed=args.seed,
            time_limit_s=args.time_limit,
            run_root=args.run_root,
            solver_bin=args.solver_bin,
        )
    except VrsSolverRunnerError as exc:
        _eprint(f"ERROR: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        _eprint(f"ERROR: Unexpected runner error: {exc}")
        return 2

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
