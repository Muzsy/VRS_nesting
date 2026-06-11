#!/usr/bin/env python3
"""SGH-Q34 smoke — sheet margin enforcement validator.

Validates static code invariants AND runs two synthetic cases:
  - sheet_margin_ok: margin 10 on 100×100, 2× 20×20 parts → ok, all inside [10,90].
  - sheet_margin_too_large: 95×95 part with margin 10 → not ok, 0 placed, 1 unplaced.

Static checks:
  - apply_rectangular_sheet_margin exists in sheet.rs
  - count_sheet_margin_violations exists in sheet.rs
  - technology_sheet_margin_applied diagnostics field exists in io.rs
  - technology_margin_violation_count diagnostics field exists in io.rs
  - sparrow_cde_multisheet pipeline still exists
  - TechnologyClearancePolicy still exists
  - no compression wired via margin enforcement
  - no legacy multisheet manager used by the new margin path
  - margin-inset placements all inside the inset rectangle
  - too-large margin case does not return ok

Exit codes:
  0  PASS
  2  FAIL
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
INPUTS = ROOT / "artifacts" / "benchmarks" / "sgh_q34" / "inputs"
OUTPUTS = ROOT / "artifacts" / "benchmarks" / "sgh_q34" / "outputs"

PASS_COUNT = 0
FAIL_COUNT = 0


def check(cond: bool, msg: str) -> None:
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {msg}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_comments(text: str) -> str:
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    return text


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rotated_bbox(width: float, height: float, rot_deg: float) -> tuple[float, float, float, float]:
    """Return (min_x_off, min_y_off, bbox_w, bbox_h) for a rotated rectangle anchored at origin."""
    theta = math.radians(rot_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    corners = [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)]
    xs = [cx * cos_t - cy * sin_t for cx, cy in corners]
    ys = [cx * sin_t + cy * cos_t for cx, cy in corners]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return min_x, min_y, (max_x - min_x), (max_y - min_y)


# ── Static code invariants ────────────────────────────────────────────────────

def check_static_invariants() -> None:
    print("\n--- Static code invariants ---")

    sheet_rs_path = ROOT / "rust/vrs_solver/src/sheet.rs"
    io_rs_path = ROOT / "rust/vrs_solver/src/io.rs"
    adapter_rs_path = ROOT / "rust/vrs_solver/src/adapter.rs"
    clearance_rs_path = ROOT / "rust/vrs_solver/src/technology/clearance.rs"

    sheet_rs = strip_comments(read(sheet_rs_path))
    io_rs = strip_comments(read(io_rs_path))
    adapter_rs = strip_comments(read(adapter_rs_path))

    check("fn apply_rectangular_sheet_margin" in sheet_rs,
          "sheet.rs: apply_rectangular_sheet_margin defined")
    check("fn count_sheet_margin_violations" in sheet_rs,
          "sheet.rs: count_sheet_margin_violations defined")
    check("UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34" in sheet_rs,
          "sheet.rs: UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34 error present")
    check("MARGIN_EXCEEDS_SHEET_DIMENSIONS" in sheet_rs,
          "sheet.rs: MARGIN_EXCEEDS_SHEET_DIMENSIONS error present")

    check("technology_sheet_margin_applied" in io_rs,
          "io.rs: technology_sheet_margin_applied diagnostics field present")
    check("technology_margin_applied_sheet_count" in io_rs,
          "io.rs: technology_margin_applied_sheet_count field present")
    check("technology_margin_usable_sheet_area" in io_rs,
          "io.rs: technology_margin_usable_sheet_area field present")
    check("technology_margin_physical_used_sheet_area" in io_rs,
          "io.rs: technology_margin_physical_used_sheet_area field present")
    check("technology_margin_violation_count" in io_rs,
          "io.rs: technology_margin_violation_count field present")

    check("SparrowCdeMultisheet" in io_rs,
          "io.rs: sparrow_cde_multisheet pipeline still exists")
    check(clearance_rs_path.exists() and "TechnologyClearancePolicy" in read(clearance_rs_path),
          "TechnologyClearancePolicy still exists")

    # adapter.rs wires the margin into the multisheet pipeline
    check("apply_rectangular_sheet_margin" in adapter_rs,
          "adapter.rs: apply_rectangular_sheet_margin used in multisheet pipeline")
    check("count_sheet_margin_violations" in adapter_rs,
          "adapter.rs: count_sheet_margin_violations used as final validator")
    check("solver_sheets_override" in adapter_rs,
          "adapter.rs: solver_sheets_override passed to manager")

    # No compression wired in the margin enforcement path
    check("compression" not in strip_comments(read(sheet_rs_path)).lower(),
          "sheet.rs: no compression wired in margin helpers")
    # No legacy multisheet manager imported into sheet.rs margin path
    check("MultiSheetManager" not in sheet_rs,
          "sheet.rs: no legacy MultiSheetManager usage")

    # No spec-forbidden new offset fields
    check("part_spacing_mm" not in io_rs.replace("technology_effective_part_spacing_mm", ""),
          "io.rs: no standalone part_spacing_mm field")


# ── Synthetic runs ────────────────────────────────────────────────────────────

def run_solver(input_path: Path, output_path: Path, timeout: int = 60) -> dict | None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [str(SOLVER_BIN), "--input", str(input_path), "--output", str(output_path)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        check(False, f"{input_path.name}: solver completed within {timeout}s")
        return None
    if result.returncode != 0:
        check(False, f"{input_path.name}: solver exit code 0 (got {result.returncode})")
        print(f"    stderr: {result.stderr[:300]}")
        return None
    check(True, f"{input_path.name}: solver exit code 0")
    try:
        return load_json(output_path)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        check(False, f"{input_path.name}: output is valid JSON ({e})")
        return None


def check_ok_case() -> None:
    print("\n--- Synthetic: sheet_margin_ok ---")
    if not SOLVER_BIN.exists():
        check(False, f"solver binary exists: {SOLVER_BIN}")
        return
    out = run_solver(INPUTS / "sheet_margin_ok.json", OUTPUTS / "sheet_margin_ok_output.json")
    if out is None:
        return

    check(out.get("status") == "ok", f"status == ok (got {out.get('status')!r})")
    m = out.get("metrics", {})
    check(m.get("placed_count") == 2, f"placed_count == 2 (got {m.get('placed_count')})")
    check(m.get("unplaced_count") == 0, f"unplaced_count == 0 (got {m.get('unplaced_count')})")

    od = out.get("optimizer_diagnostics", {})
    check(od.get("technology_sheet_margin_applied") is True, "technology_sheet_margin_applied == true")
    check(od.get("technology_margin_violation_count") == 0, "technology_margin_violation_count == 0")
    check(od.get("technology_margin_usable_sheet_area") == 6400.0,
          f"usable area == 6400 (got {od.get('technology_margin_usable_sheet_area')})")
    check(od.get("technology_margin_physical_used_sheet_area") == 10000.0,
          f"physical area == 10000 (got {od.get('technology_margin_physical_used_sheet_area')})")

    # Every placement must lie within the inset rectangle [10, 90].
    all_inside = True
    for pl in out.get("placements", []):
        min_x_off, min_y_off, bw, bh = rotated_bbox(20.0, 20.0, float(pl["rotation_deg"]))
        wmin_x = pl["x"] + min_x_off
        wmin_y = pl["y"] + min_y_off
        wmax_x = wmin_x + bw
        wmax_y = wmin_y + bh
        eps = 1e-6
        if wmin_x < 10.0 - eps or wmin_y < 10.0 - eps or wmax_x > 90.0 + eps or wmax_y > 90.0 + eps:
            all_inside = False
            print(f"    OUT OF MARGIN: x=[{wmin_x:.3f},{wmax_x:.3f}] y=[{wmin_y:.3f},{wmax_y:.3f}]")
    check(all_inside, "all placements within margin-inset rectangle [10,90]")


def check_too_large_case() -> None:
    print("\n--- Synthetic: sheet_margin_too_large ---")
    if not SOLVER_BIN.exists():
        return
    out = run_solver(INPUTS / "sheet_margin_too_large.json", OUTPUTS / "sheet_margin_too_large_output.json")
    if out is None:
        return

    check(out.get("status") != "ok", f"status != ok (got {out.get('status')!r})")
    m = out.get("metrics", {})
    check(m.get("placed_count") == 0, f"placed_count == 0 (got {m.get('placed_count')})")
    check(m.get("unplaced_count") == 1, f"unplaced_count == 1 (got {m.get('unplaced_count')})")
    unplaced = out.get("unplaced", [])
    check(len(unplaced) == 1 and bool(unplaced[0].get("reason")),
          f"explicit unplaced reason present (got {unplaced[0].get('reason') if unplaced else None!r})")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("=== SGH-Q34 sheet margin enforcement smoke ===")
    check_static_invariants()
    check_ok_case()
    check_too_large_case()

    print(f"\n{'='*48}")
    print(f"  PASS: {PASS_COUNT}   FAIL: {FAIL_COUNT}")
    if FAIL_COUNT > 0:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
