#!/usr/bin/env python3
"""JG-10 smoke: repair search V1 contract verification.

Repair-only initial state cannot be injected directly via the solver CLI
(the CLI always runs construction then repair). Therefore, the repair-specific
checks (overlap fix, boundary fix, count invariant, determinism, stopping policy)
are proven via Rust unit tests run in this script. Integration evidence is proven
via the Phase 1 solver CLI (which now includes the repair pass after construction).

Checks:
  1. Rust repair unit tests PASS (cargo test optimizer::repair)
  2. Rust stopping unit tests PASS (cargo test optimizer::stopping)
  3. Integration: valid Phase 1 fixture → solver exit 0, validation_status=pass
  4. Integration: validation_status=pass in runner meta (exact validation bridge live)
  5. Integration: metrics present (utilization, placed_count, sheet_count_used)
  6. Overlap evidence via validate_multi_sheet_output (bridge rejects overlap)
  7. Boundary evidence via validate_multi_sheet_output (bridge rejects out-of-sheet)
  8. Regression: smoke_jagua_initial_construction.py PASS
  9. Regression: smoke_jagua_exact_validation_bridge.py PASS
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.nesting.instances import validate_multi_sheet_output  # noqa: E402
from vrs_nesting.runner.vrs_solver_runner import run_solver_in_dir  # noqa: E402

FAIL_COUNT = 0
PASS_COUNT = 0


def _fail(msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  FAIL: {msg}", file=sys.stderr)


def _pass(label: str) -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  PASS: {label}")


def _resolve_solver_bin() -> str:
    explicit = os.environ.get("VRS_SOLVER_BIN")
    if explicit:
        p = Path(explicit)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        print(f"VRS_SOLVER_BIN not executable: {explicit}", file=sys.stderr)
        sys.exit(1)
    release = ROOT / "rust/vrs_solver/target/release/vrs_solver"
    if release.is_file() and os.access(release, os.X_OK):
        return str(release)
    which = shutil.which("vrs_solver")
    if which:
        return which
    print("Building vrs_solver release...", flush=True)
    r = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(ROOT / "rust/vrs_solver/Cargo.toml")],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(1)
    return str(release)


def _run_cargo_test(filter_: str) -> tuple[int, str]:
    r = subprocess.run(
        ["cargo", "test", "--manifest-path", str(ROOT / "rust/vrs_solver/Cargo.toml"), filter_],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return r.returncode, r.stdout + r.stderr


def _run_via_runner(solver_bin: str, inp: dict, run_dir: Path) -> dict | None:
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = run_dir / "solver_input.json"
    input_path.write_text(json.dumps(inp), encoding="utf-8")
    try:
        _, meta = run_solver_in_dir(
            str(input_path),
            run_dir=run_dir,
            seed=inp.get("seed", 42),
            time_limit_s=inp.get("time_limit_s", 5),
            solver_bin=solver_bin,
        )
        return meta
    except Exception as exc:  # noqa: BLE001
        meta_path = run_dir / "runner_meta.json"
        if meta_path.is_file():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
        print(f"  [runner exception] {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Check 1: Repair unit tests via cargo test
# ---------------------------------------------------------------------------
def check_repair_unit_tests() -> None:
    print("\n[Rust repair unit tests: cargo test optimizer::repair]")
    rc, out = _run_cargo_test("optimizer::repair")
    lines = [l for l in out.splitlines() if "test result" in l or "passed" in l or "FAILED" in l]
    summary = lines[0] if lines else out[-200:].strip()
    if rc == 0:
        _pass(f"repair unit tests PASS: {summary}")
    else:
        _fail(f"repair unit tests FAIL (exit={rc}): {summary}")


# ---------------------------------------------------------------------------
# Check 2: Stopping policy unit tests
# ---------------------------------------------------------------------------
def check_stopping_unit_tests() -> None:
    print("\n[Rust stopping unit tests: cargo test optimizer::stopping]")
    rc, out = _run_cargo_test("optimizer::stopping")
    lines = [l for l in out.splitlines() if "test result" in l or "passed" in l or "FAILED" in l]
    summary = lines[0] if lines else out[-200:].strip()
    if rc == 0:
        _pass(f"stopping unit tests PASS: {summary}")
    else:
        _fail(f"stopping unit tests FAIL (exit={rc}): {summary}")


# ---------------------------------------------------------------------------
# Check 3 + 4 + 5: Integration via runner (includes repair pass)
# ---------------------------------------------------------------------------
def check_integration_valid(solver_bin: str, tmp: Path) -> dict | None:
    print("\n[Integration: valid Phase 1 fixture → runner, repair active]")
    inp = {
        "contract_version": "v1",
        "project_name": "jg10_smoke",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        "parts": [
            {"id": "A", "width": 50, "height": 50, "quantity": 3, "allowed_rotations_deg": [0]},
            {"id": "B", "width": 80, "height": 30, "quantity": 2, "allowed_rotations_deg": [0, 90]},
        ],
    }
    meta = _run_via_runner(solver_bin, inp, tmp / "integration")
    if meta is None:
        _fail("runner returned no meta")
        return None

    vs = meta.get("validation_status")
    if vs == "pass":
        _pass("validation_status=pass (JG-09 bridge still active with JG-10 repair)")
    else:
        _fail(f"expected validation_status=pass, got {vs!r}")

    for field in ["duration_sec", "placements_count", "unplaced_count", "sheet_count_used", "utilization"]:
        val = meta.get(field)
        if val is not None:
            _pass(f"{field}={val!r}")
        else:
            _fail(f"metrics field missing: {field}")

    return meta


# ---------------------------------------------------------------------------
# Check 6: Overlap evidence via bridge
# ---------------------------------------------------------------------------
def check_overlap_evidence() -> None:
    print("\n[Overlap evidence: validate_multi_sheet_output raises on overlap]")
    inp = {
        "contract_version": "v1",
        "project_name": "overlap_test",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 1, "width": 200, "height": 200}],
        "parts": [{"id": "A", "width": 40, "height": 40, "quantity": 2, "allowed_rotations_deg": [0]}],
    }
    out = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "A__0001", "part_id": "A", "sheet_index": 0, "x": 0.0, "y": 0.0, "rotation_deg": 0},
            {"instance_id": "A__0002", "part_id": "A", "sheet_index": 0, "x": 10.0, "y": 10.0, "rotation_deg": 0},
        ],
        "unplaced": [],
        "metrics": {"placed_count": 2, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "test"},
    }
    try:
        validate_multi_sheet_output(inp, out)
        _fail("bridge accepted overlapping repair output (expected ValueError)")
    except ValueError as exc:
        _pass(f"overlap correctly rejected by bridge: {exc}")


# ---------------------------------------------------------------------------
# Check 7: Boundary/out-of-sheet evidence via bridge
# ---------------------------------------------------------------------------
def check_boundary_evidence() -> None:
    print("\n[Boundary evidence: validate_multi_sheet_output raises on out-of-sheet]")
    inp = {
        "contract_version": "v1",
        "project_name": "boundary_test",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 1, "width": 100, "height": 100}],
        "parts": [{"id": "A", "width": 30, "height": 30, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    out = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "A__0001", "part_id": "A", "sheet_index": 0, "x": 200.0, "y": 200.0, "rotation_deg": 0},
        ],
        "unplaced": [],
        "metrics": {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "test"},
    }
    try:
        validate_multi_sheet_output(inp, out)
        _fail("bridge accepted out-of-sheet placement (expected ValueError)")
    except ValueError as exc:
        _pass(f"out-of-sheet correctly rejected by bridge: {exc}")


# ---------------------------------------------------------------------------
# Check 8: JG-08 regression
# ---------------------------------------------------------------------------
def check_regression_jg08() -> None:
    print("\n[Regression: smoke_jagua_initial_construction.py]")
    script = ROOT / "scripts/smoke_jagua_initial_construction.py"
    if not script.is_file():
        _fail(f"smoke script missing: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("smoke_jagua_initial_construction.py PASS (JG-08 regression)")
    else:
        _fail(f"smoke_jagua_initial_construction.py FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


# ---------------------------------------------------------------------------
# Check 9: JG-09 regression
# ---------------------------------------------------------------------------
def check_regression_jg09() -> None:
    print("\n[Regression: smoke_jagua_exact_validation_bridge.py]")
    script = ROOT / "scripts/smoke_jagua_exact_validation_bridge.py"
    if not script.is_file():
        _fail(f"smoke script missing: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("smoke_jagua_exact_validation_bridge.py PASS (JG-09 regression)")
    else:
        _fail(f"smoke_jagua_exact_validation_bridge.py FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


def main() -> int:
    print("=== JG-10 Repair Search V1 Smoke ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    check_repair_unit_tests()
    check_stopping_unit_tests()

    with tempfile.TemporaryDirectory(prefix="jg10_smoke_") as tmp:
        p = Path(tmp)
        check_integration_valid(solver_bin, p)

    check_overlap_evidence()
    check_boundary_evidence()
    check_regression_jg08()
    check_regression_jg09()

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
