#!/usr/bin/env python3
"""Deterministic Sparrow runner with per-run artifacts under runs/<run_id>."""

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
from typing import Any, cast

from vrs_nesting.config.runtime import resolve_sparrow_bin_name, sparrow_runtime_from_env
from vrs_nesting.run_artifacts.run_dir import create_run_dir

class SparrowRunnerError(RuntimeError):
    """Base runner error."""

    code = "E_SPARROW_RUNNER"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class SparrowBinaryNotFoundError(SparrowRunnerError):
    """Raised when Sparrow binary cannot be resolved."""

    code = "E_SPARROW_BIN_NOT_FOUND"


class SparrowNonZeroExitError(SparrowRunnerError):
    """Raised when Sparrow exits with non-zero status."""

    code = "E_SPARROW_NON_ZERO_EXIT"


class SparrowTimeoutError(SparrowRunnerError):
    """Raised when Sparrow exceeds runner timeout."""

    code = "E_SPARROW_TIMEOUT"


class SparrowOutputNotFoundError(SparrowRunnerError):
    """Raised when expected output json is missing."""

    code = "E_SPARROW_OUTPUT_NOT_FOUND"


class SparrowOutputParseError(SparrowRunnerError):
    """Raised when output json cannot be parsed."""

    code = "E_SPARROW_OUTPUT_PARSE"


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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SparrowOutputParseError(f"JSON parse error: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SparrowOutputParseError(f"Top-level JSON object required: {path}")
    return cast(dict[str, Any], payload)


def resolve_sparrow_bin(explicit_bin: str | None = None) -> str:
    candidates: list[str] = []
    config_bin = resolve_sparrow_bin_name(explicit_bin=explicit_bin)
    if config_bin:
        candidates.append(config_bin)
    if "sparrow" not in candidates:
        candidates.append("sparrow")

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return str(Path(resolved).resolve())

        cand_path = Path(candidate)
        if cand_path.is_file() and os.access(cand_path, os.X_OK):
            return str(cand_path.resolve())

    raise SparrowBinaryNotFoundError(
        "Sparrow binary not found. Provide --sparrow-bin explicitly, or set SPARROW_BIN."
    )


def _discover_final_json(run_dir: Path, snapshot_json: Path, input_json: Path) -> Path:
    output_dir = run_dir / "output"
    if not output_dir.is_dir():
        raise SparrowOutputNotFoundError(f"Missing output directory: {output_dir}")

    in_data = _read_json(snapshot_json)
    candidates: list[Path] = []

    if isinstance(in_data.get("name"), str) and in_data["name"].strip():
        candidates.append(output_dir / f"final_{in_data['name'].strip()}.json")

    stem = input_json.stem
    if stem:
        candidates.append(output_dir / f"final_{stem}.json")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    all_final = sorted(output_dir.glob("final_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if all_final:
        return all_final[0].resolve()

    raise SparrowOutputNotFoundError(f"final_*.json not found in output directory: {output_dir}")


def _discover_final_svg(run_dir: Path, final_json: Path) -> str:
    explicit = final_json.with_suffix(".svg")
    if explicit.is_file():
        return str(explicit.resolve())

    output_dir = run_dir / "output"
    all_svg = sorted(output_dir.glob("final_*.svg"), key=lambda p: p.stat().st_mtime, reverse=True)
    if all_svg:
        return str(all_svg[0].resolve())
    return ""


def _extract_metrics(final_json: Path) -> tuple[float | None, float | None, int | None]:
    data = _read_json(final_json)
    sol = data.get("solution") if isinstance(data, dict) else None
    if not isinstance(sol, dict):
        return None, None, None

    strip_width_raw = sol.get("strip_width")
    density_raw = sol.get("density")
    layout = sol.get("layout")
    placed_items = layout.get("placed_items") if isinstance(layout, dict) else None

    strip_width: float | None = None
    density: float | None = None
    placed_count: int | None = None

    if isinstance(strip_width_raw, (int, float)):
        strip_width = float(strip_width_raw)
    if isinstance(density_raw, (int, float)):
        density = float(density_raw)
    if isinstance(placed_items, list):
        placed_count = len(placed_items)

    return strip_width, density, placed_count


def _run_sparrow_with_snapshot(
    *,
    input_json: Path,
    snapshot_json: Path,
    run_dir: Path,
    seed: int,
    time_limit: int,
    sparrow_bin: str | None,
) -> tuple[Path, dict[str, Any]]:
    bin_path = resolve_sparrow_bin(sparrow_bin)

    stdout_log = run_dir / "sparrow_stdout.log"
    stderr_log = run_dir / "sparrow_stderr.log"
    meta_path = run_dir / "runner_meta.json"

    cmd = [bin_path, "-i", str(snapshot_json), "-t", str(int(time_limit)), "-s", str(int(seed))]
    started = _utc_now_iso()
    started_mono = monotonic()
    timeout_grace = float(os.environ.get("SPARROW_TIMEOUT_GRACE_S", "10.0"))
    effective_timeout = max(1.0, float(int(time_limit)) + timeout_grace)

    _eprint(f"[runner] run_dir={run_dir}")
    _eprint(f"[runner] cmd={' '.join(cmd)}")

    timed_out = False
    return_code = 0
    with stdout_log.open("w", encoding="utf-8") as out_handle, stderr_log.open("w", encoding="utf-8") as err_handle:
        try:
            proc = subprocess.run(
                cmd,
                cwd=run_dir,
                stdout=out_handle,
                stderr=err_handle,
                text=True,
                check=False,
                timeout=effective_timeout,
            )
            return_code = int(proc.returncode)
        except subprocess.TimeoutExpired:
            timed_out = True
            return_code = 124

    duration = round(monotonic() - started_mono, 3)
    ended = _utc_now_iso()

    meta: dict[str, Any] = {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "input_snapshot_path": str(snapshot_json.resolve()),
        "stdout_log_path": str(stdout_log.resolve()),
        "stderr_log_path": str(stderr_log.resolve()),
        "cmd": cmd,
        "seed": int(seed),
        "time_limit": int(time_limit),
        "effective_timeout_s": effective_timeout,
        "sparrow_bin": bin_path,
        "input_sha256": _sha256_file(snapshot_json),
        "started_at_utc": started,
        "ended_at_utc": ended,
        "duration_sec": duration,
        "return_code": return_code,
        "final_json_path": "",
        "final_svg_path": "",
        "strip_width": None,
        "density": None,
        "placed_count": None,
    }

    if timed_out:
        _write_json(meta_path, meta)
        raise SparrowTimeoutError(
            f"Sparrow process timed out after {effective_timeout:.3f}s (time_limit={time_limit}). run_dir={run_dir}"
        )

    if return_code != 0:
        _write_json(meta_path, meta)
        raise SparrowNonZeroExitError(
            f"Sparrow process failed with non-zero exit code (exit={return_code}). run_dir={run_dir}"
        )

    final_json = _discover_final_json(run_dir, snapshot_json, input_json)
    final_svg = _discover_final_svg(run_dir, final_json)
    strip_width, density, placed_count = _extract_metrics(final_json)

    meta["final_json_path"] = str(final_json)
    meta["final_svg_path"] = final_svg
    meta["strip_width"] = strip_width
    meta["density"] = density
    meta["placed_count"] = placed_count

    _write_json(meta_path, meta)
    return run_dir, meta


def run_sparrow(
    input_path: str,
    *,
    seed: int,
    time_limit: int,
    run_root: str = "runs",
    sparrow_bin: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    input_json = Path(input_path).resolve()
    if not input_json.is_file():
        raise SparrowRunnerError(f"Input JSON not found: {input_json}", code="E_SPARROW_INPUT_NOT_FOUND")

    try:
        run_dir = create_run_dir(run_root=run_root).run_dir
    except Exception as exc:  # noqa: BLE001
        raise SparrowRunnerError("Failed to allocate unique run_id.", code="E_SPARROW_RUN_ID_ALLOC") from exc
    snapshot_json = run_dir / "instance.json"
    shutil.copy2(input_json, snapshot_json)
    return _run_sparrow_with_snapshot(
        input_json=input_json,
        snapshot_json=snapshot_json,
        run_dir=run_dir,
        seed=seed,
        time_limit=time_limit,
        sparrow_bin=sparrow_bin,
    )


def run_sparrow_in_dir(
    input_path: str,
    *,
    run_dir: str | Path,
    seed: int,
    time_limit: int,
    sparrow_bin: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    input_json = Path(input_path).resolve()
    if not input_json.is_file():
        raise SparrowRunnerError(f"Input JSON not found: {input_json}", code="E_SPARROW_INPUT_NOT_FOUND")

    target_dir = Path(run_dir).resolve()
    if not target_dir.is_dir():
        raise SparrowRunnerError(f"run_dir not found: {target_dir}", code="E_SPARROW_RUN_DIR_NOT_FOUND")

    snapshot_json = target_dir / "instance.json"
    if snapshot_json.resolve() != input_json:
        shutil.copy2(input_json, snapshot_json)
    return _run_sparrow_with_snapshot(
        input_json=input_json,
        snapshot_json=snapshot_json,
        run_dir=target_dir,
        seed=seed,
        time_limit=time_limit,
        sparrow_bin=sparrow_bin,
    )


def _default_seed() -> int:
    return sparrow_runtime_from_env().seed


def _default_time_limit() -> int:
    return sparrow_runtime_from_env().time_limit_s


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Sparrow and store artifacts in runs/<run_id>/")
    parser.add_argument("--input", required=True, help="Path to Sparrow input JSON")
    parser.add_argument("--seed", type=int, default=_default_seed(), help="Sparrow seed (default: env SPARROW_SEED or 0)")
    parser.add_argument(
        "--time-limit",
        type=int,
        default=_default_time_limit(),
        help="Sparrow time limit in seconds (default: env SPARROW_TIME_LIMIT_S or 60)",
    )
    parser.add_argument("--run-root", default="runs", help="Root directory for run artifacts (default: runs)")
    parser.add_argument("--sparrow-bin", default=None, help="Explicit Sparrow binary path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_dir, _meta = run_sparrow(
            args.input,
            seed=args.seed,
            time_limit=args.time_limit,
            run_root=args.run_root,
            sparrow_bin=args.sparrow_bin,
        )
    except SparrowRunnerError as exc:
        _eprint(f"ERROR: {exc.code}: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        _eprint(f"ERROR: E_SPARROW_UNEXPECTED: {exc}")
        return 2

    # Script integration requires stdout to contain only run_dir.
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
