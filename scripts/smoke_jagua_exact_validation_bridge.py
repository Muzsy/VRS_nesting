#!/usr/bin/env python3
"""JG-09 smoke: exact validation bridge and metrics contract verification.

Checks:
  1. Valid Phase 1 fixture via runner → validation_status=pass, utilization present
  2. Valid fixture metrics: duration_sec, placed_count, unplaced_count, sheet_count_used, utilization
  3. Overlap-invalid output → validate_multi_sheet_output raises ValueError (bridge rejects)
  4. Out-of-sheet / invalid sheet_index output → bridge rejects
  5. Unsupported hole-containing Phase 1 input → validation_status=skipped_unsupported
  6. Regression: smoke_jagua_initial_construction.py still PASS
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


def _base_valid_input(name: str = "jg09_smoke") -> dict:
    return {
        "contract_version": "v1",
        "project_name": name,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        "parts": [
            {"id": "A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]},
            {"id": "B", "width": 80, "height": 30, "quantity": 1, "allowed_rotations_deg": [0, 90]},
        ],
    }


def _run_via_runner(solver_bin: str, inp: dict, run_dir: Path) -> dict | None:
    """Run solver via runner, return runner_meta dict or None on error."""
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
# Check 1: Valid fixture via runner → validation_status=pass
# ---------------------------------------------------------------------------
def check_valid_runner_pass(solver_bin: str, tmp: Path) -> dict | None:
    print("\n[Valid Phase 1 fixture via runner: validation_status=pass]")
    inp = _base_valid_input()
    meta = _run_via_runner(solver_bin, inp, tmp / "valid_run")
    if meta is None:
        _fail("runner returned no meta")
        return None
    vs = meta.get("validation_status")
    if vs == "pass":
        _pass(f"validation_status=pass")
    else:
        _fail(f"expected validation_status=pass, got {vs!r}")
    ve = meta.get("validation_error")
    if ve is None:
        _pass("validation_error=None on valid run")
    else:
        _fail(f"expected validation_error=None, got {ve!r}")
    return meta


# ---------------------------------------------------------------------------
# Check 2: Metrics fields present in valid run meta
# ---------------------------------------------------------------------------
def check_metrics_presence(meta: dict | None) -> None:
    print("\n[Metrics fields present in valid runner meta]")
    if meta is None:
        _fail("no meta to check")
        return
    required = ["duration_sec", "placements_count", "unplaced_count", "sheet_count_used", "utilization"]
    for field in required:
        val = meta.get(field)
        if val is not None:
            _pass(f"{field}={val!r}")
        else:
            _fail(f"field missing or None: {field}")
    util = meta.get("utilization")
    if isinstance(util, float) and 0.0 <= util <= 1.0:
        _pass(f"utilization in [0,1]: {util}")
    elif util is not None:
        _fail(f"utilization out of expected range or wrong type: {util!r}")


# ---------------------------------------------------------------------------
# Check 3: Overlap-invalid output → bridge raises ValueError
# ---------------------------------------------------------------------------
def check_bridge_rejects_overlap() -> None:
    print("\n[Overlap-invalid output: bridge raises ValueError]")
    inp = _base_valid_input()
    out = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "A__0001", "part_id": "A", "sheet_index": 0, "x": 0.0, "y": 0.0, "rotation_deg": 0},
            {"instance_id": "A__0002", "part_id": "A", "sheet_index": 0, "x": 10.0, "y": 0.0, "rotation_deg": 0},
            {"instance_id": "B__0001", "part_id": "B", "sheet_index": 0, "x": 100.0, "y": 0.0, "rotation_deg": 0},
        ],
        "unplaced": [],
        "metrics": {"placed_count": 3, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "test"},
    }
    try:
        validate_multi_sheet_output(inp, out)
        _fail("bridge accepted overlapping placements (expected ValueError)")
    except ValueError as exc:
        _pass(f"bridge raised ValueError on overlap: {exc}")
    except Exception as exc:
        _fail(f"unexpected exception type {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Check 4: Invalid sheet_index → bridge raises ValueError
# ---------------------------------------------------------------------------
def check_bridge_rejects_invalid_sheet_index() -> None:
    print("\n[Invalid sheet_index: bridge raises ValueError]")
    inp = _base_valid_input()
    out = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [
            {"instance_id": "A__0001", "part_id": "A", "sheet_index": 9999, "x": 0.0, "y": 0.0, "rotation_deg": 0},
            {"instance_id": "A__0002", "part_id": "A", "sheet_index": 0, "x": 60.0, "y": 0.0, "rotation_deg": 0},
            {"instance_id": "B__0001", "part_id": "B", "sheet_index": 0, "x": 130.0, "y": 0.0, "rotation_deg": 0},
        ],
        "unplaced": [],
        "metrics": {"placed_count": 3, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "test"},
    }
    try:
        validate_multi_sheet_output(inp, out)
        _fail("bridge accepted invalid sheet_index=9999 (expected ValueError)")
    except ValueError as exc:
        _pass(f"bridge raised ValueError on invalid sheet_index: {exc}")
    except Exception as exc:
        _fail(f"unexpected exception type {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Check 5: Unsupported hole-containing input → validation_status=skipped_unsupported
# ---------------------------------------------------------------------------
def check_unsupported_branch(solver_bin: str, tmp: Path) -> None:
    print("\n[Unsupported hole-containing Phase 1 input: skipped_unsupported]")
    inp = {
        "contract_version": "v1",
        "project_name": "jg09_unsupported",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 1, "width": 200, "height": 200}],
        "parts": [
            {
                "id": "HOLEY",
                "width": 50, "height": 50,
                "quantity": 1,
                "allowed_rotations_deg": [0],
                "holes_points": [[[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0]]],
            }
        ],
    }
    run_dir = tmp / "unsupported_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = _run_via_runner(solver_bin, inp, run_dir)
    if meta is None:
        _fail("runner returned no meta for unsupported input")
        return
    vs = meta.get("validation_status")
    if vs == "skipped_unsupported":
        _pass("validation_status=skipped_unsupported for hole-containing Phase 1 input")
    else:
        _fail(f"expected validation_status=skipped_unsupported, got {vs!r}")
    ss = meta.get("solver_status")
    if ss == "unsupported":
        _pass("solver_status=unsupported confirmed")
    else:
        _fail(f"expected solver_status=unsupported, got {ss!r}")


# ---------------------------------------------------------------------------
# Check 6: Regression — smoke_jagua_initial_construction.py still PASS
# ---------------------------------------------------------------------------
def check_regression_jg08(tmp: Path) -> None:
    print("\n[Regression: smoke_jagua_initial_construction.py]")
    script = ROOT / "scripts/smoke_jagua_initial_construction.py"
    if not script.is_file():
        _fail(f"smoke script missing: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
        cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("smoke_jagua_initial_construction.py PASS")
    else:
        _fail(f"smoke_jagua_initial_construction.py FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-500:], file=sys.stderr)


def main() -> int:
    print("=== JG-09 Exact Validation Bridge & Metrics Smoke ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    with tempfile.TemporaryDirectory(prefix="jg09_smoke_") as tmp:
        p = Path(tmp)
        meta = check_valid_runner_pass(solver_bin, p)
        check_metrics_presence(meta)
        check_bridge_rejects_overlap()
        check_bridge_rejects_invalid_sheet_index()
        check_unsupported_branch(solver_bin, p)
        check_regression_jg08(p)

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
