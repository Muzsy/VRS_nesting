#!/usr/bin/env python3
"""JG-11 smoke: ScoreModel V1 contract verification.

Score internals are Rust-only and not directly callable from Python. Therefore
the score-specific checks (invalid vs valid scoring, unplaced penalty, sheet
count penalty, overlap/boundary penalty, compactness, determinism) are proven
via Rust unit tests run in this script. Integration evidence is proven via the
Phase 1 solver CLI.

Checks:
  1. Rust score unit tests PASS (cargo test optimizer::score)
  2. All 8 expected score test names present in output
  3. Integration: valid Phase 1 fixture → solver exit 0, validation_status=pass
  4. Integration: metrics present (utilization, placed_count, sheet_count_used)
  5. Regression: smoke_jagua_repair_search_v1.py PASS
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

from vrs_nesting.runner.vrs_solver_runner import run_solver_in_dir  # noqa: E402

FAIL_COUNT = 0
PASS_COUNT = 0

EXPECTED_SCORE_TESTS = [
    "test_valid_layout_score_is_stable",
    "test_unplaced_item_increases_cost",
    "test_more_sheets_increases_cost",
    "test_overlap_increases_cost_dramatically",
    "test_boundary_violation_increases_cost_dramatically",
    "test_compactness_is_tiebreaker_only",
    "test_deterministic_score",
    "test_is_better_lower_cost_wins",
]


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
        ["cargo", "build", "--release", "--manifest-path",
         str(ROOT / "rust/vrs_solver/Cargo.toml")],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(1)
    return str(release)


def _run_cargo_test(filter_: str) -> tuple[int, str]:
    r = subprocess.run(
        ["cargo", "test", "--manifest-path",
         str(ROOT / "rust/vrs_solver/Cargo.toml"), filter_],
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
# Check 1: Rust score unit tests via cargo test
# ---------------------------------------------------------------------------
def check_score_unit_tests() -> str:
    print("\n[Rust score unit tests: cargo test optimizer::score]")
    rc, out = _run_cargo_test("optimizer::score")
    lines = [l for l in out.splitlines() if "test result" in l or "passed" in l or "FAILED" in l]
    summary = lines[0] if lines else out[-300:].strip()
    if rc == 0:
        _pass(f"score unit tests PASS: {summary}")
    else:
        _fail(f"score unit tests FAIL (exit={rc}): {summary}")
    return out


# ---------------------------------------------------------------------------
# Check 2: Expected test names present
# ---------------------------------------------------------------------------
def check_score_test_names(test_output: str) -> None:
    print("\n[Score test names present in output]")
    for name in EXPECTED_SCORE_TESTS:
        if name in test_output:
            _pass(f"test present: {name}")
        else:
            _fail(f"expected test not found in output: {name}")


# ---------------------------------------------------------------------------
# Check 3 + 4: Integration via runner
# ---------------------------------------------------------------------------
def check_integration_valid(solver_bin: str, tmp: Path) -> None:
    print("\n[Integration: valid Phase 1 fixture → runner with score active]")
    inp = {
        "contract_version": "v1",
        "project_name": "jg11_smoke",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        "parts": [
            {"id": "A", "width": 50, "height": 50, "quantity": 3,
             "allowed_rotations_deg": [0]},
            {"id": "B", "width": 80, "height": 30, "quantity": 2,
             "allowed_rotations_deg": [0, 90]},
        ],
    }
    meta = _run_via_runner(solver_bin, inp, tmp / "integration")
    if meta is None:
        _fail("runner returned no meta")
        return

    vs = meta.get("validation_status")
    if vs == "pass":
        _pass("validation_status=pass (exact validation bridge active)")
    else:
        _fail(f"expected validation_status=pass, got {vs!r}")

    for field in ["duration_sec", "placements_count", "unplaced_count",
                  "sheet_count_used", "utilization"]:
        val = meta.get(field)
        if val is not None:
            _pass(f"{field}={val!r}")
        else:
            _fail(f"metrics field missing: {field}")


# ---------------------------------------------------------------------------
# Check 5: JG-10 regression
# ---------------------------------------------------------------------------
def check_regression_jg10() -> None:
    print("\n[Regression: smoke_jagua_repair_search_v1.py]")
    script = ROOT / "scripts/smoke_jagua_repair_search_v1.py"
    if not script.is_file():
        _fail(f"smoke script missing: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("smoke_jagua_repair_search_v1.py PASS (JG-10 regression)")
    else:
        _fail(f"smoke_jagua_repair_search_v1.py FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


def main() -> int:
    print("=== JG-11 ScoreModel V1 Smoke ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    test_output = check_score_unit_tests()
    check_score_test_names(test_output)

    with tempfile.TemporaryDirectory(prefix="jg11_smoke_") as tmp:
        check_integration_valid(solver_bin, Path(tmp))

    check_regression_jg10()

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
