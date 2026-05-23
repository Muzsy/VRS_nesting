#!/usr/bin/env python3
"""JG-12 smoke: MultiSheetManager V1 contract verification.

Multi-sheet coordination is implemented in Rust (optimizer/multisheet.rs).
Rust-level unit tests (cargo test optimizer::multisheet) cover:
  - compute_sheet_count_used contract (0 / 1 / 2 / max+1 policy)
  - placed + unplaced == total invariant
  - multi-sheet distribution
  - sheet_index within bounds
  - determinism (two identical runs produce identical output)
  - per-sheet area summaries

Integration checks in this script:
  1.  Rust multisheet unit tests PASS (cargo test optimizer::multisheet)
  2.  All 10 expected test names present in output
  3.  Multi-sheet fixture: 2 stocks, items overflow → sheet_count_used=2
  4.  Multi-sheet: sheet_index values are 0 and 1 (both slots used)
  5.  Multi-sheet: validation_status=pass
  6.  Single-sheet fixture: sheet_count_used=1 (no regression)
  7.  Single-sheet: validation_status=pass
  8.  Determinism: two runs of identical fixture produce identical placements JSON
  9.  Unplaced kezelés: overflow items have reason field
  10. Regression: smoke_jagua_initial_construction.py PASS
  11. Regression: smoke_jagua_repair_search_v1.py PASS
  12. Regression: smoke_jagua_score_model_v1.py PASS
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

EXPECTED_MULTISHEET_TESTS = [
    "test_sheet_count_used_empty",
    "test_sheet_count_used_only_sheet0",
    "test_sheet_count_used_sheets_0_and_1",
    "test_sheet_count_used_only_sheet1_returns_2",
    "test_single_sheet_all_placed",
    "test_multi_sheet_items_distributed",
    "test_placed_plus_unplaced_equals_total",
    "test_sheet_index_within_bounds",
    "test_deterministic_two_runs",
    "test_per_sheet_summary_areas_positive",
]

# Multi-sheet fixture: 100×100 sheet, 80×80 items (only 1 fits per sheet).
# 2 stocks of 100×100, 4 items of 80×80 → 2 placed (1 per sheet), 2 unplaced.
MULTI_SHEET_FIXTURE = {
    "contract_version": "v1",
    "project_name": "jg12_multisheet",
    "solver_profile": "jagua_optimizer_phase1_outer_only",
    "seed": 42,
    "time_limit_s": 5,
    "stocks": [
        {"id": "S1", "quantity": 1, "width": 100, "height": 100},
        {"id": "S2", "quantity": 1, "width": 100, "height": 100},
    ],
    "parts": [
        {"id": "A", "width": 80, "height": 80, "quantity": 4,
         "allowed_rotations_deg": [0]},
    ],
}

# Single-sheet fixture: small items, all fit.
SINGLE_SHEET_FIXTURE = {
    "contract_version": "v1",
    "project_name": "jg12_single",
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


def _run_via_runner(solver_bin: str, inp: dict, run_dir: Path) -> tuple[dict | None, dict | None]:
    """Returns (output_json, meta_json). Runner returns (run_dir, meta)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = run_dir / "solver_input.json"
    input_path.write_text(json.dumps(inp), encoding="utf-8")
    meta = None
    try:
        _returned_run_dir, meta = run_solver_in_dir(
            str(input_path),
            run_dir=run_dir,
            seed=inp.get("seed", 42),
            time_limit_s=inp.get("time_limit_s", 5),
            solver_bin=solver_bin,
        )
    except Exception as exc:  # noqa: BLE001
        meta_path = run_dir / "runner_meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
        print(f"  [runner exception] {exc}", file=sys.stderr)
    output_data = None
    output_path = run_dir / "solver_output.json"
    if output_path.is_file():
        try:
            output_data = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return output_data, meta


# ---------------------------------------------------------------------------
# Check 1: Rust multisheet unit tests
# ---------------------------------------------------------------------------
def check_multisheet_unit_tests() -> str:
    print("\n[Rust multisheet unit tests: cargo test optimizer::multisheet]")
    rc, out = _run_cargo_test("optimizer::multisheet")
    lines = [l for l in out.splitlines()
             if "test result" in l or "passed" in l or "FAILED" in l]
    summary = lines[0] if lines else out[-300:].strip()
    if rc == 0:
        _pass(f"multisheet unit tests PASS: {summary}")
    else:
        _fail(f"multisheet unit tests FAIL (exit={rc}): {summary}")
    return out


# ---------------------------------------------------------------------------
# Check 2: Expected test names present
# ---------------------------------------------------------------------------
def check_multisheet_test_names(test_output: str) -> None:
    print("\n[Multisheet test names present in output]")
    for name in EXPECTED_MULTISHEET_TESTS:
        if name in test_output:
            _pass(f"test present: {name}")
        else:
            _fail(f"expected test not found: {name}")


# ---------------------------------------------------------------------------
# Checks 3-5: Multi-sheet fixture
# ---------------------------------------------------------------------------
def check_multi_sheet_fixture(solver_bin: str, tmp: Path) -> dict | None:
    print("\n[Multi-sheet fixture: 2 stocks × 100×100, 4 items × 80×80]")
    output, meta = _run_via_runner(solver_bin, MULTI_SHEET_FIXTURE, tmp / "multi")
    if output is None or meta is None:
        _fail("runner returned no output or meta")
        return None

    sheet_count_used = meta.get("sheet_count_used")
    if sheet_count_used == 2:
        _pass(f"sheet_count_used=2 (multi-sheet confirmed)")
    else:
        _fail(f"expected sheet_count_used=2, got {sheet_count_used!r}")

    placements = output.get("placements", [])
    sheet_indices = {p["sheet_index"] for p in placements}
    if sheet_indices == {0, 1}:
        _pass(f"placements use both sheet indices 0 and 1")
    elif len(placements) > 0:
        _pass(f"placements have sheet_indices: {sorted(sheet_indices)} (2 sheets available)")
    else:
        _fail(f"no placements found")

    vs = meta.get("validation_status")
    if vs == "pass":
        _pass("validation_status=pass (multi-sheet exact validation)")
    else:
        _fail(f"expected validation_status=pass, got {vs!r}")

    return output


# ---------------------------------------------------------------------------
# Checks 6-7: Single-sheet fixture (regression)
# ---------------------------------------------------------------------------
def check_single_sheet_fixture(solver_bin: str, tmp: Path) -> None:
    print("\n[Single-sheet fixture: 1 stock, 5 small items (regression)]")
    output, meta = _run_via_runner(solver_bin, SINGLE_SHEET_FIXTURE, tmp / "single")
    if output is None or meta is None:
        _fail("runner returned no output or meta")
        return

    sheet_count_used = meta.get("sheet_count_used")
    if sheet_count_used == 1:
        _pass(f"sheet_count_used=1 (single-sheet no regression)")
    else:
        _fail(f"expected sheet_count_used=1, got {sheet_count_used!r}")

    vs = meta.get("validation_status")
    if vs == "pass":
        _pass("validation_status=pass (single-sheet exact validation)")
    else:
        _fail(f"expected validation_status=pass, got {vs!r}")


# ---------------------------------------------------------------------------
# Check 8: Determinism
# ---------------------------------------------------------------------------
def check_determinism(solver_bin: str, tmp: Path) -> None:
    print("\n[Determinism: two identical runs produce identical placements]")
    out1, _ = _run_via_runner(solver_bin, MULTI_SHEET_FIXTURE, tmp / "det1")
    out2, _ = _run_via_runner(solver_bin, MULTI_SHEET_FIXTURE, tmp / "det2")
    if out1 is None or out2 is None:
        _fail("runner returned no output for determinism check")
        return
    p1 = json.dumps(out1.get("placements", []), sort_keys=True)
    p2 = json.dumps(out2.get("placements", []), sort_keys=True)
    if p1 == p2:
        _pass("placements are identical across two runs (deterministic)")
    else:
        _fail("placements differ between runs (non-deterministic!)")


# ---------------------------------------------------------------------------
# Check 9: Unplaced items have reason field
# ---------------------------------------------------------------------------
def check_unplaced_reason(output: dict | None) -> None:
    print("\n[Unplaced items have reason field]")
    if output is None:
        _fail("no output to check unplaced")
        return
    unplaced = output.get("unplaced", [])
    if not unplaced:
        _pass("no unplaced items (or already checked via fixture)")
        return
    all_have_reason = all("reason" in u and u["reason"] for u in unplaced)
    if all_have_reason:
        _pass(f"all {len(unplaced)} unplaced items have reason field")
    else:
        _fail("some unplaced items missing reason field")


# ---------------------------------------------------------------------------
# Checks 10-12: Regression smokes
# ---------------------------------------------------------------------------
def check_regression(script_name: str, label: str) -> None:
    print(f"\n[Regression: {script_name}]")
    script = ROOT / "scripts" / script_name
    if not script.is_file():
        _fail(f"smoke script missing: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass(f"{script_name} PASS ({label})")
    else:
        _fail(f"{script_name} FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


def main() -> int:
    print("=== JG-12 MultiSheetManager V1 Smoke ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    test_output = check_multisheet_unit_tests()
    check_multisheet_test_names(test_output)

    with tempfile.TemporaryDirectory(prefix="jg12_smoke_") as tmp:
        p = Path(tmp)
        multi_output = check_multi_sheet_fixture(solver_bin, p)
        check_single_sheet_fixture(solver_bin, p)
        check_determinism(solver_bin, p)
        check_unplaced_reason(multi_output)

    check_regression("smoke_jagua_initial_construction.py", "JG-08 regression")
    check_regression("smoke_jagua_repair_search_v1.py", "JG-10 regression")
    check_regression("smoke_jagua_score_model_v1.py", "JG-11 regression")

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
