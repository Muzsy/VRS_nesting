#!/usr/bin/env python3
"""JG-15 smoke: irregular sheet capability spike verification.

Checks:
  1.  Fixture exists and is valid JSON.
  2.  Fixture is hole-free (no stock holes_points, no item holes_points).
  3.  Fixture has at least one concave outer_points stock.
  4.  Rust spike bin builds.
  5.  Spike bin runs and outputs all required decision lines.
  6.  NATIVE_BOUNDARY_SUPPORT: NO
  7.  L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES
  8.  CURRENT_BBOX_ONLY_RISK_DETECTED: YES
  9.  DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION
  10. Decision report exists with JG-15_DECISION: line.
  11. Python exact validator rejects notch placement (boundary violation gate).
  12. Item-item collision regression: smoke_jagua_exact_validation_bridge.py PASS.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "egyedi_solver" / "jagua_irregular_l_shape.json"
DECISION_REPORT = ROOT / "docs" / "egyedi_solver" / "jagua_irregular_sheet_spike_decision.md"
CARGO_MANIFEST = ROOT / "rust" / "vrs_solver" / "Cargo.toml"
BIN_NAME = "jagua_irregular_sheet_spike"

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


def _is_concave(points: list) -> bool:
    """Return True if the polygon has at least one reflex (concave) vertex."""
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    pts = [(p[0] if isinstance(p, list) else p["x"], p[1] if isinstance(p, list) else p["y"])
           for p in points]
    n = len(pts)
    if n < 3:
        return False
    signs = set()
    for i in range(n):
        o = pts[i]
        a = pts[(i + 1) % n]
        b = pts[(i + 2) % n]
        c = _cross(o, a, b)
        if abs(c) > 1e-12:
            signs.add(c > 0)
    return len(signs) > 1


# ---------------------------------------------------------------------------
# Check 1: fixture exists and is valid JSON
# ---------------------------------------------------------------------------
def check_fixture_exists() -> dict | None:
    print("\n[Check 1: Fixture exists and is valid JSON]")
    if not FIXTURE_PATH.is_file():
        _fail(f"fixture not found: {FIXTURE_PATH}")
        return None
    try:
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        _pass(f"fixture exists and is valid JSON: {FIXTURE_PATH.name}")
        return data
    except Exception as exc:  # noqa: BLE001
        _fail(f"fixture JSON parse error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Check 2: hole-free
# ---------------------------------------------------------------------------
def check_hole_free(data: dict) -> None:
    print("\n[Check 2: Fixture is hole-free]")
    for i, stock in enumerate(data.get("stocks", [])):
        holes = stock.get("holes_points")
        if holes:
            _fail(f"stock[{i}] has holes_points — fixture must be hole-free")
            return
    for i, part in enumerate(data.get("parts", [])):
        holes = part.get("holes_points") or part.get("prepared_holes_points")
        if holes:
            _fail(f"part[{i}] has holes_points — fixture must be hole-free")
            return
    _pass("fixture is hole-free (no stock holes, no part holes)")


# ---------------------------------------------------------------------------
# Check 3: at least one concave outer_points stock
# ---------------------------------------------------------------------------
def check_concave_stock(data: dict) -> None:
    print("\n[Check 3: Fixture has at least one concave outer_points stock]")
    found = False
    for i, stock in enumerate(data.get("stocks", [])):
        pts = stock.get("outer_points")
        if pts and _is_concave(pts):
            _pass(f"stock[{i}] (id={stock.get('id')}) has concave outer_points ({len(pts)} points)")
            found = True
    if not found:
        _fail("no stock with concave outer_points found in fixture")


# ---------------------------------------------------------------------------
# Check 4: Rust spike bin builds
# ---------------------------------------------------------------------------
def check_bin_builds() -> bool:
    print(f"\n[Check 4: Rust spike bin builds (cargo build --bin {BIN_NAME})]")
    r = subprocess.run(
        ["cargo", "build", "--manifest-path", str(CARGO_MANIFEST), "--bin", BIN_NAME],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass(f"cargo build --bin {BIN_NAME} PASS")
        return True
    _fail(f"cargo build --bin {BIN_NAME} FAIL (exit={r.returncode})")
    print(r.stderr[-400:], file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# Check 5-9: run spike bin and parse decision lines
# ---------------------------------------------------------------------------
def check_spike_output() -> str | None:
    print(f"\n[Check 5-9: Run spike bin and check decision lines]")
    r = subprocess.run(
        ["cargo", "run", "--manifest-path", str(CARGO_MANIFEST), "--bin", BIN_NAME],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    output = r.stdout + r.stderr
    if r.returncode != 0:
        _fail(f"spike bin exited {r.returncode}")
        print(output[-400:], file=sys.stderr)
        return None
    _pass("spike bin ran without error")

    def _grep(key: str) -> str | None:
        for line in output.splitlines():
            if line.startswith(key + ":"):
                return line.split(":", 1)[1].strip()
        return None

    # Check 6
    native = _grep("NATIVE_BOUNDARY_SUPPORT")
    if native == "NO":
        _pass("NATIVE_BOUNDARY_SUPPORT: NO (no native jagua container boundary API)")
    else:
        _fail(f"expected NATIVE_BOUNDARY_SUPPORT: NO, got {native!r}")

    # Check 7
    violation = _grep("L_SHAPE_BOUNDARY_VIOLATION_DETECTED")
    if violation == "YES":
        _pass("L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES")
    else:
        _fail(f"expected L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES, got {violation!r}")

    # Check 8
    risk = _grep("CURRENT_BBOX_ONLY_RISK_DETECTED")
    if risk == "YES":
        _pass("CURRENT_BBOX_ONLY_RISK_DETECTED: YES (bbox-only check passes notch placement)")
    else:
        _fail(f"expected CURRENT_BBOX_ONLY_RISK_DETECTED: YES, got {risk!r}")

    # Check 9
    decision = _grep("DECISION")
    if decision == "OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION":
        _pass("DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION")
    else:
        _fail(f"expected DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION, got {decision!r}")

    return decision


# ---------------------------------------------------------------------------
# Check 10: decision report has JG-15_DECISION line
# ---------------------------------------------------------------------------
def check_decision_report() -> None:
    print("\n[Check 10: Decision report has JG-15_DECISION line]")
    if not DECISION_REPORT.is_file():
        _fail(f"decision report not found: {DECISION_REPORT}")
        return
    content = DECISION_REPORT.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("JG-15_DECISION:"):
            _pass(f"decision report has: {line.strip()}")
            return
    _fail("decision report missing JG-15_DECISION: line")


# ---------------------------------------------------------------------------
# Check 11: Python exact validator rejects notch placement
# ---------------------------------------------------------------------------
def check_exact_validator_rejects_notch() -> None:
    print("\n[Check 11: Python exact validator rejects notch placement on L-shape stock]")
    try:
        from vrs_nesting.nesting.instances import validate_multi_sheet_output
    except ImportError as exc:
        _fail(f"cannot import validate_multi_sheet_output: {exc}")
        return

    # Construct a minimal v1 input with L-shape stock
    l_input = {
        "contract_version": "v1",
        "project_name": "jg15_notch_test",
        "stocks": [{
            "id": "L1", "quantity": 1,
            "outer_points": [[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]],
        }],
        "parts": [{"id": "A", "width": 20, "height": 20, "quantity": 1,
                   "allowed_rotations_deg": [0]}],
    }
    # Notch placement — item 20×20 at (60,60), fully inside bbox but in the notch
    l_output_notch = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [{
            "instance_id": "A__0001", "part_id": "A",
            "sheet_index": 0, "x": 60.0, "y": 60.0, "rotation_deg": 0,
        }],
        "unplaced": [],
        "metrics": {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "jg15_notch_test"},
    }
    try:
        validate_multi_sheet_output(l_input, l_output_notch)
        _fail("validator accepted notch placement — should have rejected it")
    except Exception as exc:  # noqa: BLE001
        _pass(f"validator correctly rejected notch placement: {type(exc).__name__}: {exc}")

    # Positive control — item 20×20 at (10,10), fully inside L-shape
    l_output_valid = {
        "contract_version": "v1",
        "status": "ok",
        "placements": [{
            "instance_id": "A__0001", "part_id": "A",
            "sheet_index": 0, "x": 10.0, "y": 10.0, "rotation_deg": 0,
        }],
        "unplaced": [],
        "metrics": {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                    "seed": 42, "time_limit_s": 5, "project_name": "jg15_notch_test"},
    }
    try:
        validate_multi_sheet_output(l_input, l_output_valid)
        _pass("validator accepted valid placement (inside L-shape)")
    except Exception as exc:  # noqa: BLE001
        _fail(f"validator rejected valid placement — unexpected: {exc}")


# ---------------------------------------------------------------------------
# Check 12: item-item collision regression
# ---------------------------------------------------------------------------
def check_item_item_regression() -> None:
    print("\n[Check 12: Item-item collision regression (smoke_jagua_exact_validation_bridge.py)]")
    script = ROOT / "scripts" / "smoke_jagua_exact_validation_bridge.py"
    if not script.is_file():
        _fail(f"smoke script not found: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("smoke_jagua_exact_validation_bridge.py PASS (item-item collision regression)")
    else:
        _fail(f"smoke_jagua_exact_validation_bridge.py FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-300:], file=sys.stderr)


def main() -> int:
    print("=== JG-15 Irregular Sheet Capability Spike Smoke ===")

    data = check_fixture_exists()
    if data is not None:
        check_hole_free(data)
        check_concave_stock(data)

    built = check_bin_builds()
    if built:
        check_spike_output()

    check_decision_report()
    check_exact_validator_rejects_notch()
    check_item_item_regression()

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
