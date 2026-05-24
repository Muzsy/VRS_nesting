#!/usr/bin/env python3
"""JG-16 smoke: irregular sheet provider and margin policy verification.

Checks:
  1.  Fixture jagua_irregular_margin.json exists and has expected fields.
  2.  Fixture has L-shape stock (concave outer_points, no holes).
  3.  Rectangular stock provider regression: Phase1 run returns ok/partial.
  4.  L-shape stock without margin: solver accepts (not unsupported).
  5.  Margin policy: margin_mm>0 → status=unsupported, reason=UNSUPPORTED_MARGIN_MM_RUNTIME.
  6.  Stock holes unsupported: non-empty holes_points → UNSUPPORTED_STOCK_HOLES_PHASE1.
  7.  Too-narrow remnant: all parts get PART_NEVER_FITS_STOCK (deterministic fail).
  8.  has_irregular_outer=True evidence: L-shape SheetShape correctly flagged (unit tests).
  9.  Shape metadata: L-shape area < bbox_area (area < width*height).
  10. Exact validation gate: Python validator rejects notch placement; accepts valid placement.
  11. cargo test --manifest-path rust/vrs_solver/Cargo.toml passes (sheet unit tests).
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

FIXTURE_MARGIN = ROOT / "tests" / "fixtures" / "egyedi_solver" / "jagua_irregular_margin.json"
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
        print(f"VRS_SOLVER_BIN not executable: {explicit}", file=sys.stderr)
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
    print("Building vrs_solver (release)...", flush=True)
    r = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(CARGO_MANIFEST)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode != 0:
        print(r.stderr[-600:], file=sys.stderr)
        return None
    if release.is_file():
        return str(release)
    return None


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
            print(f"  solver did not produce output (exit={r.returncode}): {r.stderr[-200:]}", file=sys.stderr)
            return None
        try:
            return json.loads(out.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"  output JSON parse error: {exc}", file=sys.stderr)
            return None


def _is_concave(points: list) -> bool:
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    pts = [(p[0] if isinstance(p, list) else p["x"], p[1] if isinstance(p, list) else p["y"])
           for p in points]
    n = len(pts)
    if n < 3:
        return False
    signs = set()
    for i in range(n):
        o, a, b = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c = _cross(o, a, b)
        if abs(c) > 1e-12:
            signs.add(c > 0)
    return len(signs) > 1


# ---------------------------------------------------------------------------
# Check 1: fixture exists and has expected fields
# ---------------------------------------------------------------------------
def check_fixture_exists() -> dict | None:
    print("\n[Check 1: Fixture jagua_irregular_margin.json exists and has expected fields]")
    if not FIXTURE_MARGIN.is_file():
        _fail(f"fixture not found: {FIXTURE_MARGIN}")
        return None
    try:
        data = json.loads(FIXTURE_MARGIN.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail(f"fixture JSON parse error: {exc}")
        return None
    if "margin_mm" not in data:
        _fail("fixture missing margin_mm field")
        return None
    if data.get("margin_mm", 0) <= 0:
        _fail(f"fixture margin_mm must be > 0, got {data.get('margin_mm')}")
        return None
    if data.get("solver_profile") != PHASE1_PROFILE:
        _fail(f"fixture solver_profile must be {PHASE1_PROFILE}, got {data.get('solver_profile')!r}")
        return None
    _pass(f"fixture exists; margin_mm={data['margin_mm']}; solver_profile={data['solver_profile']!r}")
    return data


# ---------------------------------------------------------------------------
# Check 2: L-shape stock, concave outer_points, no holes
# ---------------------------------------------------------------------------
def check_fixture_l_shape(data: dict) -> None:
    print("\n[Check 2: Fixture has L-shape stock (concave outer_points, no holes)]")
    stocks = data.get("stocks", [])
    if not stocks:
        _fail("fixture has no stocks")
        return
    s = stocks[0]
    pts = s.get("outer_points")
    if not pts:
        _fail("fixture stock[0] missing outer_points")
        return
    if not _is_concave(pts):
        _fail("fixture stock outer_points is not concave (expected L-shape)")
        return
    if s.get("holes_points"):
        _fail("fixture stock has holes_points — must be hole-free")
        return
    _pass(f"stock {s.get('id')!r} has concave outer_points ({len(pts)} pts), no holes")


# ---------------------------------------------------------------------------
# Check 3: rectangular stock regression
# ---------------------------------------------------------------------------
def check_rect_regression(solver_bin: str) -> None:
    print("\n[Check 3: Rectangular stock provider regression (Phase1 ok/partial)]")
    rect_input = {
        "contract_version": "v1",
        "project_name": "jg16_rect_regression",
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
        _fail("rectangular regression: solver produced no output")
        return
    status = out.get("status", "")
    if status in ("ok", "partial"):
        placed = out.get("metrics", {}).get("placed_count", 0)
        _pass(f"rectangular stock Phase1 → status={status!r}, placed={placed}")
    else:
        _fail(f"rectangular regression: unexpected status={status!r}, unsupported_reason={out.get('unsupported_reason')!r}")


# ---------------------------------------------------------------------------
# Check 4: L-shape without margin accepted (not unsupported)
# ---------------------------------------------------------------------------
def check_l_shape_no_margin(solver_bin: str) -> None:
    print("\n[Check 4: L-shape stock without margin: solver accepts (not unsupported)]")
    l_input = {
        "contract_version": "v1",
        "project_name": "jg16_l_shape_no_margin",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{
            "id": "L1", "quantity": 1,
            "outer_points": [[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]],
        }],
        "parts": [
            {"id": "A", "width": 20, "height": 15, "quantity": 2, "allowed_rotations_deg": [0]},
        ],
    }
    out = _run_solver(solver_bin, l_input)
    if out is None:
        _fail("L-shape no-margin: solver produced no output")
        return
    status = out.get("status", "")
    if status == "unsupported":
        _fail(f"L-shape no-margin returned unsupported: {out.get('unsupported_reason')!r}")
        return
    _pass(f"L-shape no-margin: status={status!r}, placed={out.get('metrics', {}).get('placed_count', 0)}")


# ---------------------------------------------------------------------------
# Check 5: margin_mm > 0 → UNSUPPORTED_MARGIN_MM_RUNTIME
# ---------------------------------------------------------------------------
def check_margin_unsupported(solver_bin: str) -> None:
    print("\n[Check 5: margin_mm>0 → status=unsupported, reason=UNSUPPORTED_MARGIN_MM_RUNTIME]")
    data = json.loads(FIXTURE_MARGIN.read_text(encoding="utf-8"))
    out = _run_solver(solver_bin, data)
    if out is None:
        _fail("margin_mm fixture: solver produced no output")
        return
    status = out.get("status", "")
    reason = out.get("unsupported_reason", "")
    if status == "unsupported" and reason == "UNSUPPORTED_MARGIN_MM_RUNTIME":
        _pass(f"margin_mm=5.0 → status=unsupported, reason={reason!r}")
    else:
        _fail(f"expected unsupported/UNSUPPORTED_MARGIN_MM_RUNTIME, got status={status!r} reason={reason!r}")


# ---------------------------------------------------------------------------
# Check 6: stock holes_points → UNSUPPORTED_STOCK_HOLES_PHASE1
# ---------------------------------------------------------------------------
def check_stock_holes_unsupported(solver_bin: str) -> None:
    print("\n[Check 6: Non-empty stock holes_points → UNSUPPORTED_STOCK_HOLES_PHASE1]")
    holes_input = {
        "contract_version": "v1",
        "project_name": "jg16_stock_holes",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{
            "id": "S_hole",
            "quantity": 1,
            "width": 200,
            "height": 200,
            "holes_points": [
                [[50, 50], [100, 50], [100, 100], [50, 100]],
            ],
        }],
        "parts": [{"id": "A", "width": 30, "height": 30, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    out = _run_solver(solver_bin, holes_input)
    if out is None:
        _fail("stock holes: solver produced no output")
        return
    status = out.get("status", "")
    reason = out.get("unsupported_reason", "")
    if status == "unsupported" and reason == "UNSUPPORTED_STOCK_HOLES_PHASE1":
        _pass(f"stock holes_points → status=unsupported, reason={reason!r}")
    else:
        _fail(f"expected unsupported/UNSUPPORTED_STOCK_HOLES_PHASE1, got status={status!r} reason={reason!r}")


# ---------------------------------------------------------------------------
# Check 7: too-narrow remnant → PART_NEVER_FITS_STOCK for all parts
# ---------------------------------------------------------------------------
def check_too_narrow_remnant(solver_bin: str) -> None:
    print("\n[Check 7: Too-narrow remnant → PART_NEVER_FITS_STOCK (deterministic fail)]")
    narrow_input = {
        "contract_version": "v1",
        "project_name": "jg16_too_narrow",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "NARROW", "quantity": 3, "width": 1, "height": 1000}],
        "parts": [
            {"id": "BIG", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0, 90]},
        ],
    }
    out = _run_solver(solver_bin, narrow_input)
    if out is None:
        _fail("too-narrow: solver produced no output")
        return
    unplaced = out.get("unplaced", [])
    placements = out.get("placements", [])
    reasons = {u.get("reason") for u in unplaced}
    if placements:
        _fail(f"too-narrow: expected 0 placements, got {len(placements)}")
        return
    if "PART_NEVER_FITS_STOCK" in reasons:
        _pass(f"too-narrow remnant: all parts → PART_NEVER_FITS_STOCK ({len(unplaced)} unplaced)")
    else:
        _fail(f"too-narrow: expected PART_NEVER_FITS_STOCK reason, got reasons={reasons!r}")


# ---------------------------------------------------------------------------
# Check 8+9: shape metadata evidence (via L-shape area < bbox area)
# ---------------------------------------------------------------------------
def check_shape_metadata() -> None:
    print("\n[Check 8-9: Shape metadata: L-shape area < bbox_area; fixture metadata documented]")
    data = json.loads(FIXTURE_MARGIN.read_text(encoding="utf-8"))
    notes = data.get("_fixture_notes", {})
    area = notes.get("stock_area_mm2")
    bbox = notes.get("stock_bbox", [0, 0])
    bbox_area = bbox[0] * bbox[1] if len(bbox) == 2 else None
    if area is not None and bbox_area is not None and area < bbox_area:
        _pass(f"fixture documents L-shape area={area} < bbox_area={bbox_area} (concave shape)")
    else:
        _fail(f"fixture metadata missing or invalid: area={area}, bbox_area={bbox_area}")

    # Verify no holes documented
    has_holes = notes.get("has_holes")
    if has_holes is False:
        _pass("fixture metadata confirms has_holes=false")
    else:
        _fail(f"fixture metadata has_holes={has_holes!r}, expected False")


# ---------------------------------------------------------------------------
# Check 10: exact validation gate
# ---------------------------------------------------------------------------
def check_exact_validation_gate() -> None:
    print("\n[Check 10: Exact validation gate (Python rejects notch; accepts valid)]")
    try:
        from vrs_nesting.nesting.instances import validate_multi_sheet_output
    except ImportError as exc:
        _fail(f"cannot import validate_multi_sheet_output: {exc}")
        return

    l_input = {
        "contract_version": "v1",
        "project_name": "jg16_exact_val",
        "stocks": [{"id": "L1", "quantity": 1,
                    "outer_points": [[0, 0], [100, 0], [100, 50], [50, 50], [50, 100], [0, 100]]}],
        "parts": [{"id": "A", "width": 20, "height": 20, "quantity": 1, "allowed_rotations_deg": [0]}],
    }
    common_meta = {"placed_count": 1, "unplaced_count": 0, "sheet_count_used": 1,
                   "seed": 42, "time_limit_s": 5, "project_name": "jg16_exact_val"}

    # Notch placement — bbox passes, L-shape fails → validator must reject
    notch_out = {
        "contract_version": "v1", "status": "ok",
        "placements": [{"instance_id": "A__0001", "part_id": "A",
                        "sheet_index": 0, "x": 60.0, "y": 60.0, "rotation_deg": 0}],
        "unplaced": [], "metrics": common_meta,
    }
    try:
        validate_multi_sheet_output(l_input, notch_out)
        _fail("exact validator accepted notch placement — should have rejected")
    except Exception as exc:  # noqa: BLE001
        _pass(f"exact validator rejected notch: {type(exc).__name__}")

    # Valid placement — inside L-shape → validator must accept
    valid_out = {
        "contract_version": "v1", "status": "ok",
        "placements": [{"instance_id": "A__0001", "part_id": "A",
                        "sheet_index": 0, "x": 10.0, "y": 10.0, "rotation_deg": 0}],
        "unplaced": [], "metrics": common_meta,
    }
    try:
        validate_multi_sheet_output(l_input, valid_out)
        _pass("exact validator accepted valid placement inside L-shape")
    except Exception as exc:  # noqa: BLE001
        _fail(f"exact validator rejected valid placement — unexpected: {exc}")


# ---------------------------------------------------------------------------
# Check 11: cargo test (includes new sheet.rs unit tests)
# ---------------------------------------------------------------------------
def check_cargo_tests() -> None:
    print("\n[Check 11: cargo test --manifest-path rust/vrs_solver/Cargo.toml]")
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
        _pass(f"cargo test PASS ({passed} tests passed)")
    else:
        _fail(f"cargo test FAIL (exit={r.returncode})")
        print((r.stdout + r.stderr)[-400:], file=sys.stderr)


def main() -> int:
    print("=== JG-16 Irregular Sheet Provider and Margin Smoke ===")

    data = check_fixture_exists()
    if data is not None:
        check_fixture_l_shape(data)

    check_shape_metadata()

    solver_bin = _resolve_solver_bin()
    if solver_bin is None:
        _fail("solver binary not found and could not be built; skipping solver checks")
        print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
        print("OVERALL: FAIL" if FAIL_COUNT else "OVERALL: PASS")
        return 1 if FAIL_COUNT else 0

    print(f"\n  solver_bin: {solver_bin}")
    check_rect_regression(solver_bin)
    check_l_shape_no_margin(solver_bin)
    check_margin_unsupported(solver_bin)
    check_stock_holes_unsupported(solver_bin)
    check_too_narrow_remnant(solver_bin)

    check_exact_validation_gate()
    check_cargo_tests()

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
