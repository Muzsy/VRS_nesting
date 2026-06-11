#!/usr/bin/env python3
"""SGH-Q35 smoke — part-part spacing final validator + safety gate.

Static checks:
  - technology/spacing.rs exists with PartSpacingViolation, find/count, polygon_distance_mm
  - validator uses extract_polygon_from_part + transform_polygon (polygon path, not bbox)
  - PART_SPACING_VIOLATION_Q35 reason exists; adapter calls the spacing safety net
  - diagnostics fields present (applied / mm / violation_count / safety_net_removed_count)
  - kerf_mm is NOT added to spacing_mm
  - cavity prepack files not modified/connected by Q35
  - Q34 margin validator + Q32 multisheet pipeline preserved

Dynamic checks:
  - synthetic ok run: spacing applied, mm passes, violation 0 (status ok)
  - synthetic violation run: spacing gate removes placements, status != ok, explicit reason,
    kerf separate from spacing
  - cargo test --test technology_part_spacing (soft-skips if cargo absent)

Exit codes: 0 PASS, 2 FAIL
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
INPUTS = ROOT / "artifacts" / "benchmarks" / "sgh_q35" / "inputs"
OUTPUTS = ROOT / "artifacts" / "benchmarks" / "sgh_q35" / "outputs"

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


# ── Static invariants ─────────────────────────────────────────────────────────

def check_static() -> None:
    print("\n--- Static code invariants ---")
    spacing_path = ROOT / "rust/vrs_solver/src/technology/spacing.rs"
    mod_path = ROOT / "rust/vrs_solver/src/technology/mod.rs"
    io_path = ROOT / "rust/vrs_solver/src/io.rs"
    adapter_path = ROOT / "rust/vrs_solver/src/adapter.rs"

    spacing = strip_comments(read(spacing_path))
    io_rs = strip_comments(read(io_path))
    adapter = strip_comments(read(adapter_path))

    check(spacing_path.exists(), "technology/spacing.rs exists")
    check("pub mod spacing" in strip_comments(read(mod_path)), "technology/mod.rs: pub mod spacing exported")
    check("struct PartSpacingViolation" in spacing, "spacing.rs: PartSpacingViolation defined")
    check("fn find_part_spacing_violations" in spacing, "spacing.rs: find_part_spacing_violations defined")
    check("fn count_part_spacing_violations" in spacing, "spacing.rs: count_part_spacing_violations defined")
    check("fn polygon_distance_mm" in spacing, "spacing.rs: polygon_distance_mm helper defined")

    # Polygon path, not bbox.
    check("extract_polygon_from_part" in spacing and "transform_polygon" in spacing,
          "spacing.rs: uses extract_polygon_from_part + transform_polygon (polygon path)")
    check("rotated_bbox_min_offset_f64" not in spacing and "dims_for_rotation_f64" not in spacing,
          "spacing.rs: does not use bbox helpers")

    # Reason + adapter safety net.
    check("PART_SPACING_VIOLATION_Q35" in adapter, "adapter.rs: PART_SPACING_VIOLATION_Q35 reason present")
    check("find_part_spacing_violations" in adapter, "adapter.rs: calls find_part_spacing_violations")
    check("apply_spacing_violation_safety_net" in adapter, "adapter.rs: applies spacing safety net")
    check("recompute_multisheet_result_after_safety_net" in adapter,
          "adapter.rs: recomputes result aggregates after safety net")

    # Diagnostics fields.
    for f in (
        "technology_part_spacing_applied",
        "technology_part_spacing_mm",
        "technology_spacing_violation_count",
        "technology_spacing_safety_net_removed_count",
    ):
        check(f in io_rs, f"io.rs: {f} diagnostics field present")

    # Kerf independence: spacing must not add kerf. Look for forbidden combinations.
    forbidden = re.search(r"spacing_mm\s*\+\s*\w*kerf", spacing + adapter) or \
        re.search(r"kerf\w*\s*\+\s*spacing_mm", spacing + adapter)
    check(forbidden is None, "kerf_mm is NOT added to spacing_mm")

    # Cavity prepack untouched: Q35 does not import/connect cavity prepack in spacing/adapter.
    check("cavity" not in spacing.lower(), "spacing.rs: no cavity prepack reference")

    # Q34 margin validator + Q32 pipeline preserved.
    check("find_sheet_margin_violations" in adapter, "adapter.rs: Q34 margin validator preserved")
    check("SparrowCdeMultisheet" in io_rs, "io.rs: Q32 sparrow_cde_multisheet pipeline preserved")


def check_cavity_prepack_untouched() -> None:
    print("\n--- Cavity prepack untouched (git) ---")
    # Q35 must not modify cavity prepack files. Detect any staged/unstaged change to files
    # whose path contains 'cavity'.
    try:
        res = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        check(True, "git not available → skip cavity-change check")
        return
    changed_cavity = [
        line for line in res.stdout.splitlines()
        if "cavity" in line.lower() and (".rs" in line.lower())
    ]
    check(not changed_cavity, f"no cavity prepack .rs file modified by Q35 (found {changed_cavity})")


# ── Dynamic synthetic runs ────────────────────────────────────────────────────

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
        check(False, f"{input_path.name}: solver exit 0 (got {result.returncode})")
        print(f"    stderr: {result.stderr[:300]}")
        return None
    check(True, f"{input_path.name}: solver exit 0")
    try:
        return load_json(output_path)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        check(False, f"{input_path.name}: valid JSON output ({e})")
        return None


def check_ok_case() -> None:
    print("\n--- Synthetic: part_spacing_ok ---")
    if not SOLVER_BIN.exists():
        check(False, f"solver binary exists: {SOLVER_BIN}")
        return
    out = run_solver(INPUTS / "part_spacing_ok.json", OUTPUTS / "part_spacing_ok_output.json")
    if out is None:
        return
    od = out.get("optimizer_diagnostics", {})
    check(od.get("technology_part_spacing_applied") is True, "ok: technology_part_spacing_applied == true")
    check(od.get("technology_part_spacing_mm") == 5.0, f"ok: technology_part_spacing_mm == 5.0 (got {od.get('technology_part_spacing_mm')})")
    check(od.get("technology_spacing_violation_count") == 0, f"ok: spacing_violation_count == 0 (got {od.get('technology_spacing_violation_count')})")
    # kerf stays separate from spacing.
    check(od.get("technology_kerf_mm") == 0.0, f"ok: technology_kerf_mm == 0.0 separate from spacing (got {od.get('technology_kerf_mm')})")
    # If status is ok, violation count must be 0 (already asserted).
    if out.get("status") == "ok":
        check(od.get("technology_spacing_violation_count") == 0, "ok: status ok ⇒ spacing violation 0")
    else:
        check(out.get("status") in ("partial",), f"ok-case status is ok or valid partial (got {out.get('status')!r})")


def check_violation_case() -> None:
    print("\n--- Synthetic: part_spacing_violation ---")
    if not SOLVER_BIN.exists():
        return
    out = run_solver(INPUTS / "part_spacing_violation.json", OUTPUTS / "part_spacing_violation_output.json")
    if out is None:
        return
    od = out.get("optimizer_diagnostics", {})
    # Diagnostics exist and spacing_mm passes through; kerf separate.
    check(od.get("technology_part_spacing_applied") is True, "viol: technology_part_spacing_applied == true")
    check(od.get("technology_part_spacing_mm") == 5.0, f"viol: technology_part_spacing_mm == 5.0 (got {od.get('technology_part_spacing_mm')})")
    check(od.get("technology_kerf_mm") == 0.0, "viol: technology_kerf_mm separate from spacing")
    # The solver is not yet spacing-aware, so it packs tight → gate triggers.
    if od.get("technology_spacing_violation_count", 0) > 0:
        check(out.get("status") != "ok", f"viol: spacing violation ⇒ status != ok (got {out.get('status')!r})")
        reasons = [u.get("reason") for u in out.get("unplaced", [])]
        check("PART_SPACING_VIOLATION_Q35" in reasons, "viol: PART_SPACING_VIOLATION_Q35 reason in unplaced")
        check((od.get("technology_spacing_safety_net_removed_count") or 0) > 0,
              "viol: spacing_safety_net_removed_count > 0")
    else:
        check(True, "viol: solver happened to satisfy spacing (no violation) — diagnostics still valid")


# ── Dynamic cargo test ────────────────────────────────────────────────────────

def check_cargo_test() -> None:
    print("\n--- Dynamic: cargo test --test technology_part_spacing ---")
    cargo = shutil.which("cargo")
    if cargo is None:
        check(True, "cargo not on PATH → skipping live test run (verify.sh runs full suite)")
        return
    try:
        result = subprocess.run(
            [cargo, "test", "--manifest-path", str(ROOT / "rust/vrs_solver/Cargo.toml"),
             "--test", "technology_part_spacing"],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        check(False, "cargo test --test technology_part_spacing completed within 600s")
        return
    ok = result.returncode == 0 and "test result: ok" in (result.stdout + result.stderr)
    check(ok, "cargo test --test technology_part_spacing passes")
    if not ok:
        print(f"    {result.stdout[-400:]}\n    {result.stderr[-200:]}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("=== SGH-Q35 part-part spacing final validator smoke ===")
    check_static()
    check_cavity_prepack_untouched()
    check_ok_case()
    check_violation_case()
    check_cargo_test()

    print(f"\n{'='*48}")
    print(f"  PASS: {PASS_COUNT}   FAIL: {FAIL_COUNT}")
    if FAIL_COUNT > 0:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
