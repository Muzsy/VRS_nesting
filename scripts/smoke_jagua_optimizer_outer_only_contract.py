#!/usr/bin/env python3
"""JG-03 outer-only contract smoke: positive outer-only + negative holed part + legacy regression."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_nesting_solution.py"
RUN_ROOT = ROOT / "runs"

PHASE1_PROFILE = "jagua_optimizer_phase1_outer_only"
EXPECTED_UNSUPPORTED_REASON = "UNSUPPORTED_PART_HOLES_PHASE1"

POSITIVE_FIXTURE = {
    "contract_version": "v1",
    "project_name": "jg03_smoke_positive_outer_only",
    "seed": 0,
    "time_limit_s": 60,
    "solver_profile": PHASE1_PROFILE,
    "stocks": [{"id": "SHEET_A", "quantity": 1, "width": 200, "height": 200}],
    "parts": [
        {"id": "PART_A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]},
        {"id": "PART_B", "width": 80, "height": 30, "quantity": 1, "allowed_rotations_deg": [0, 90]},
    ],
}

NEGATIVE_HOLED_FIXTURE = {
    "contract_version": "v1",
    "project_name": "jg03_smoke_negative_holed",
    "seed": 0,
    "time_limit_s": 60,
    "solver_profile": PHASE1_PROFILE,
    "stocks": [{"id": "SHEET_A", "quantity": 1, "width": 200, "height": 200}],
    "parts": [
        {
            "id": "PART_HOLED",
            "width": 50,
            "height": 50,
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "holes_points": [[[10, 10], [20, 10], [20, 20], [10, 20]]],
        }
    ],
}

LEGACY_FIXTURE = {
    "contract_version": "v1",
    "project_name": "jg03_smoke_legacy_regression",
    "seed": 0,
    "time_limit_s": 60,
    "stocks": [
        {
            "id": "SHEET_A",
            "quantity": 2,
            "outer_points": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "holes_points": [[[70, 70], [80, 70], [80, 80], [70, 80]]],
        }
    ],
    "parts": [
        {"id": "PART_A", "width": 70, "height": 60, "quantity": 2, "allowed_rotations_deg": [0]},
        {"id": "PART_B", "width": 120, "height": 20, "quantity": 1, "allowed_rotations_deg": [0]},
    ],
}


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _solver_bin() -> str:
    if SOLVER_BIN.is_file() and os.access(SOLVER_BIN, os.X_OK):
        return str(SOLVER_BIN)
    _fail(
        f"Solver binary not found or not executable: {SOLVER_BIN}\n"
        "Run: cargo build --release --manifest-path rust/vrs_solver/Cargo.toml"
    )


def _run_vrs_runner(input_payload: dict) -> tuple[Path, dict]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir="/tmp"
    ) as f:
        json.dump(input_payload, f)
        tmp_input = f.name
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "vrs_nesting.runner.vrs_solver_runner",
                "--input",
                tmp_input,
                "--solver-bin",
                _solver_bin(),
                "--seed",
                "0",
                "--time-limit",
                "60",
                "--run-root",
                str(RUN_ROOT),
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        if result.returncode != 0:
            _fail(
                f"Runner exited {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )
        run_dir = Path(result.stdout.strip())
        meta_path = run_dir / "runner_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return run_dir, meta
    finally:
        os.unlink(tmp_input)


def _run_validator(run_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        _fail(f"Exact validator failed for {run_dir}:\n{result.stdout}\n{result.stderr}")


def test_positive_outer_only() -> None:
    print("\n[1/3] Positive outer-only fixture (Phase 1 profile, no holes)")
    run_dir, meta = _run_vrs_runner(POSITIVE_FIXTURE)

    output = json.loads((run_dir / "solver_output.json").read_text(encoding="utf-8"))
    status = output.get("status")
    if status not in {"ok", "partial"}:
        _fail(f"Expected ok/partial, got: {status}")
    _ok(f"status={status}")

    if output.get("unsupported_reason") is not None:
        _fail(f"unsupported_reason must be absent for ok/partial output, got: {output.get('unsupported_reason')}")
    _ok("unsupported_reason absent (correct for layout output)")

    _run_validator(run_dir)
    _ok("Exact validator PASS on positive layout")


def test_negative_holed_part() -> None:
    print("\n[2/3] Negative holed-part fixture (Phase 1 profile + holes_points)")
    run_dir, meta = _run_vrs_runner(NEGATIVE_HOLED_FIXTURE)

    output = json.loads((run_dir / "solver_output.json").read_text(encoding="utf-8"))
    status = output.get("status")
    if status != "unsupported":
        _fail(f"Expected status='unsupported', got: {status}")
    _ok(f"status=unsupported (correct)")

    reason = output.get("unsupported_reason")
    if reason != EXPECTED_UNSUPPORTED_REASON:
        _fail(f"Expected reason={EXPECTED_UNSUPPORTED_REASON!r}, got: {reason!r}")
    _ok(f"unsupported_reason={reason} (correct)")

    if output.get("placements"):
        _fail("placements must be empty for unsupported output")
    _ok("placements=[] (no silent layout acceptance)")

    meta_reason = meta.get("unsupported_reason")
    if meta_reason != EXPECTED_UNSUPPORTED_REASON:
        _fail(f"runner_meta.json unsupported_reason mismatch: {meta_reason!r}")
    _ok(f"runner_meta.json unsupported_reason={meta_reason}")

    meta_status = meta.get("solver_status")
    if meta_status != "unsupported":
        _fail(f"runner_meta.json solver_status expected 'unsupported', got: {meta_status!r}")
    _ok("runner_meta.json solver_status=unsupported")


def test_legacy_regression() -> None:
    print("\n[3/3] Legacy regression (no solver_profile, stock has holes — existing check.sh style)")
    run_dir, meta = _run_vrs_runner(LEGACY_FIXTURE)

    output = json.loads((run_dir / "solver_output.json").read_text(encoding="utf-8"))
    status = output.get("status")
    if status not in {"ok", "partial"}:
        _fail(f"Legacy regression: expected ok/partial, got: {status}")
    _ok(f"Legacy status={status}")

    placements = output.get("placements", [])
    if not placements:
        _fail("Legacy regression: expected at least one placement (PART_A fits)")
    _ok(f"Legacy placements={len(placements)}")

    _run_validator(run_dir)
    _ok("Exact validator PASS on legacy layout")


def main() -> None:
    print("=== JG-03 outer-only contract smoke ===")
    test_positive_outer_only()
    test_negative_holed_part()
    test_legacy_regression()
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
