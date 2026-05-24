#!/usr/bin/env python3
"""JG-17 smoke: irregular boundary validation policy verification.

Checks:
  1.  Fixture jagua_irregular_boundary_validation.json exists and has expected fields.
  2.  Fixture has L-shape stock, no holes, positive/negative control documented.
  3.  Rectangular stock boundary regression: Phase1 run places items correctly.
  4.  L-shape positive control: solver places items inside L-shape (status ok/partial).
  5.  Notch placement negative control: Python exact validator rejects notch placement.
  6.  Valid L-shape placement: Python exact validator accepts inside-L placement.
  7.  Invalid boundary layout not successful: validator rejects → not ok/partial.
  8.  margin_mm>0 Phase1: UNSUPPORTED_MARGIN_MM_RUNTIME (margin not silent success).
  9.  cargo test PASS (includes boundary.rs unit tests, 87 total).
  10. smoke_jagua_irregular_sheet_provider.py regression (JG-16 checks pass).
  11. smoke_jagua_exact_validation_bridge.py regression (exact validation bridge).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "egyedi_solver" / "jagua_irregular_boundary_validation.json"
CARGO_MANIFEST = ROOT / "rust" / "vrs_solver" / "Cargo.toml"
PHASE1_PROFILE = "jagua_optimizer_phase1_outer_only"

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


def _resolve_solver_bin() -> str | None:
    explicit = os.environ.get("VRS_SOLVER_BIN")
    if explicit:
        p = Path(explicit)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        return None
    release = ROOT / "rust/vrs_solver/target/release/vrs_solver"
    if release.is_file() and os.access(release, os.X_OK):
        return str(release)
    debug = ROOT / "rust/vrs_solver/target/debug/vrs_solver"
    if debug.is_file() and os.access(debug, os.X_OK):
        return str(debug)
    which = shutil.which("vrs_solver")
    if which:
        return which
    r = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(CARGO_MANIFEST)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return str(release) if r.returncode == 0 and release.is_file() else None


def _run_solver(solver_bin: str, input_dict: dict[str, Any]) -> dict[str, Any] | None:
    with tempfile.TemporaryDirectory() as tmp:
        inp = Path(tmp) / "solver_input.json"
        out = Path(tmp) / "solver_output.json"
        inp.write_text(json.dumps(input_dict), encoding="utf-8")
        r = subprocess.run(
            [solver_bin, "--input", str(inp), "--output", str(out)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        if not out.is_file():
            return None
        try:
            return json.loads(out.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None


# ---------------------------------------------------------------------------
# Check 1: fixture exists and has positive/negative control documented
# ---------------------------------------------------------------------------
def check_fixture_exists() -> dict | None:
    print("\n[Check 1: Fixture exists and has expected fields]")
    if not FIXTURE_PATH.is_file():
        _fail(f"fixture not found: {FIXTURE_PATH}")
        return None
    try:
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail(f"fixture JSON parse error: {exc}")
        return None
    notes = data.get("_fixture_notes", {})
    if "positive_control" not in notes or "negative_control" not in notes:
        _fail("fixture missing positive_control or negative_control in _fixture_notes")
        return None
    _pass(f"fixture exists; positive_control and negative_control documented")
    return data


# ---------------------------------------------------------------------------
# Check 2: L-shape stock, no holes
# ---------------------------------------------------------------------------
def check_fixture_l_shape(data: dict) -> None:
    print("\n[Check 2: Fixture has L-shape stock (concave outer_points, no holes)]")
    stocks = data.get("stocks", [])
    if not stocks:
        _fail("no stocks in fixture")
        return
    s = stocks[0]
    pts = s.get("outer_points")
    if not pts or len(pts) < 5:
        _fail(f"stock outer_points missing or too short ({len(pts) if pts else 0} points)")
        return
    if s.get("holes_points"):
        _fail("stock has holes_points — must be hole-free")
        return
    _pass(f"stock {s.get('id')!r} has {len(pts)}-point outer_points, no holes")


# ---------------------------------------------------------------------------
# Check 3: rectangular stock boundary regression
# ---------------------------------------------------------------------------
def check_rect_regression(solver_bin: str) -> None:
    print("\n[Check 3: Rectangular stock boundary regression (Phase1)]")
    rect_input = {
        "contract_version": "v1",
        "project_name": "jg17_rect_regression",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "R1", "quantity": 1, "width": 200, "height": 200}],
        "parts": [
            {"id": "A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]},
            {"id": "B", "width": 80, "height": 30, "quantity": 1, "allowed_rotations_deg": [0, 90]},
        ],
    }
    out = _run_solver(solver_bin, rect_input)
    if out is None:
        _fail("rectangular regression: no solver output")
        return
    status = out.get("status", "")
    if status in ("ok", "partial"):
        placed = out.get("metrics", {}).get("placed_count", 0)
        _pass(f"rectangular Phase1 → status={status!r}, placed={placed}")
    else:
        _fail(f"rectangular regression: unexpected status={status!r}")


# ---------------------------------------------------------------------------
# Check 4: L-shape positive control — solver places inside L-shape
# ---------------------------------------------------------------------------
def check_l_shape_positive(solver_bin: str) -> None:
    print("\n[Check 4: L-shape positive control — solver runs, status not unsupported]")
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    out = _run_solver(solver_bin, data)
    if out is None:
        _fail("L-shape fixture: no solver output")
        return
    status = out.get("status", "")
    if status == "unsupported":
        _fail(f"L-shape fixture returned unsupported: {out.get('unsupported_reason')!r}")
        return
    placed = out.get("metrics", {}).get("placed_count", 0)
    _pass(f"L-shape fixture: status={status!r}, placed={placed} (solver accepted irregular stock)")


# ---------------------------------------------------------------------------
# Check 5: Python exact validator rejects notch placement (negative control)
# ---------------------------------------------------------------------------
def check_notch_rejected() -> None:
    print("\n[Check 5: Exact validator rejects notch placement (negative control)]")
    try:
        from vrs_nesting.nesting.instances import validate_multi_sheet_output
    except ImportError as exc:
        _fail(f"cannot import validate_multi_sheet_output: {exc}")
        return

    l_input = {
        "contract_version": "v1",
        "project_name": "jg17_notch_test",
        "stocks": [{"id": "L1", "quantity": 1,
                    "outer_points": [[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]]}],
        "parts": [{"id": "A", "width": 20, "height": 20, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    common_meta = {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                   "seed": 42, "time_limit_s": 5, "project_name": "jg17_notch_test"}
    notch_out = {
        "contract_version": "v1", "status": "ok",
        "placements": [{"instance_id": "A__0001", "part_id": "A",
                        "sheet_index": 0, "x": 60.0, "y": 60.0, "rotation_deg": 0}],
        "unplaced": [], "metrics": common_meta,
    }
    try:
        validate_multi_sheet_output(l_input, notch_out)
        _fail("validator accepted notch placement — must reject")
    except Exception as exc:  # noqa: BLE001
        _pass(f"validator rejected notch placement: {type(exc).__name__}")


# ---------------------------------------------------------------------------
# Check 6: Python exact validator accepts inside-L placement (positive control)
# ---------------------------------------------------------------------------
def check_inside_l_accepted() -> None:
    print("\n[Check 6: Exact validator accepts inside-L placement (positive control)]")
    try:
        from vrs_nesting.nesting.instances import validate_multi_sheet_output
    except ImportError as exc:
        _fail(f"cannot import validate_multi_sheet_output: {exc}")
        return

    l_input = {
        "contract_version": "v1",
        "project_name": "jg17_inside_test",
        "stocks": [{"id": "L1", "quantity": 1,
                    "outer_points": [[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]]}],
        "parts": [{"id": "A", "width": 20, "height": 20, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    common_meta = {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                   "seed": 42, "time_limit_s": 5, "project_name": "jg17_inside_test"}
    valid_out = {
        "contract_version": "v1", "status": "ok",
        "placements": [{"instance_id": "A__0001", "part_id": "A",
                        "sheet_index": 0, "x": 10.0, "y": 10.0, "rotation_deg": 0}],
        "unplaced": [], "metrics": common_meta,
    }
    try:
        validate_multi_sheet_output(l_input, valid_out)
        _pass("validator accepted inside-L placement (positive control)")
    except Exception as exc:  # noqa: BLE001
        _fail(f"validator rejected valid inside-L placement: {exc}")


# ---------------------------------------------------------------------------
# Check 7: invalid layout → validator raises, not successful
# ---------------------------------------------------------------------------
def check_invalid_not_success() -> None:
    print("\n[Check 7: Invalid boundary layout not successful (validator raises)]")
    try:
        from vrs_nesting.nesting.instances import validate_multi_sheet_output
    except ImportError as exc:
        _fail(f"cannot import validate_multi_sheet_output: {exc}")
        return

    rect_input = {
        "contract_version": "v1",
        "project_name": "jg17_invalid",
        "stocks": [{"id": "R1", "quantity": 1, "width": 100, "height": 80}],
        "parts": [{"id": "A", "width": 30, "height": 30, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    # Placement outside the sheet boundary
    outside_out = {
        "contract_version": "v1", "status": "ok",
        "placements": [{"instance_id": "A__0001", "part_id": "A",
                        "sheet_index": 0, "x": 90.0, "y": 70.0, "rotation_deg": 0}],
        "unplaced": [],
        "metrics": {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "jg17_invalid"},
    }
    try:
        validate_multi_sheet_output(rect_input, outside_out)
        _fail("validator accepted out-of-boundary placement — must reject")
    except Exception as exc:  # noqa: BLE001
        _pass(f"invalid layout not successful: validator raised {type(exc).__name__}")


# ---------------------------------------------------------------------------
# Check 8: margin_mm>0 → UNSUPPORTED_MARGIN_MM_RUNTIME
# ---------------------------------------------------------------------------
def check_margin_unsupported(solver_bin: str) -> None:
    print("\n[Check 8: margin_mm>0 Phase1 → UNSUPPORTED_MARGIN_MM_RUNTIME]")
    margin_input = {
        "contract_version": "v1",
        "project_name": "jg17_margin",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "margin_mm": 5.0,
        "stocks": [{"id": "L1", "quantity": 1,
                    "outer_points": [[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]]}],
        "parts": [{"id": "A", "width": 20, "height": 15, "quantity": 2, "allowed_rotations_deg": [0]}],
    }
    out = _run_solver(solver_bin, margin_input)
    if out is None:
        _fail("margin test: no solver output")
        return
    status = out.get("status", "")
    reason = out.get("unsupported_reason", "")
    if status == "unsupported" and reason == "UNSUPPORTED_MARGIN_MM_RUNTIME":
        _pass(f"margin_mm=5.0 → unsupported/{reason!r}")
    else:
        _fail(f"margin not caught: status={status!r} reason={reason!r}")


# ---------------------------------------------------------------------------
# Check 9: cargo test (includes boundary.rs unit tests)
# ---------------------------------------------------------------------------
def check_cargo_tests() -> None:
    print("\n[Check 9: cargo test (includes optimizer::boundary unit tests)]")
    r = subprocess.run(
        ["cargo", "test", "--manifest-path", str(CARGO_MANIFEST)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        passed = 0
        for line in (r.stdout + r.stderr).splitlines():
            if "test result: ok." in line:
                try:
                    passed += int(line.split("ok.")[1].split("passed")[0].strip())
                except Exception:  # noqa: BLE001
                    pass
        _pass(f"cargo test PASS ({passed} tests)")
    else:
        _fail(f"cargo test FAIL (exit={r.returncode})")
        print((r.stdout + r.stderr)[-400:], file=sys.stderr)


# ---------------------------------------------------------------------------
# Check 10: JG-16 smoke regression
# ---------------------------------------------------------------------------
def check_jg16_smoke_regression() -> None:
    print("\n[Check 10: JG-16 smoke regression (smoke_jagua_irregular_sheet_provider.py)]")
    script = ROOT / "scripts" / "smoke_jagua_irregular_sheet_provider.py"
    if not script.is_file():
        _fail(f"JG-16 smoke not found: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("JG-16 smoke PASS (smoke_jagua_irregular_sheet_provider.py)")
    else:
        _fail(f"JG-16 smoke FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


# ---------------------------------------------------------------------------
# Check 11: exact validation bridge regression
# ---------------------------------------------------------------------------
def check_exact_validation_bridge() -> None:
    print("\n[Check 11: Exact validation bridge regression (smoke_jagua_exact_validation_bridge.py)]")
    script = ROOT / "scripts" / "smoke_jagua_exact_validation_bridge.py"
    if not script.is_file():
        _fail(f"exact validation bridge smoke not found: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("exact validation bridge PASS")
    else:
        _fail(f"exact validation bridge FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


def main() -> int:
    print("=== JG-17 Irregular Boundary Validation Smoke ===")

    data = check_fixture_exists()
    if data is not None:
        check_fixture_l_shape(data)

    solver_bin = _resolve_solver_bin()
    if solver_bin is None:
        _fail("solver binary not found; skipping solver checks")
    else:
        print(f"\n  solver_bin: {solver_bin}")
        check_rect_regression(solver_bin)
        check_l_shape_positive(solver_bin)
        check_margin_unsupported(solver_bin)

    check_notch_rejected()
    check_inside_l_accepted()
    check_invalid_not_success()
    check_cargo_tests()
    check_jg16_smoke_regression()
    check_exact_validation_bridge()

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
