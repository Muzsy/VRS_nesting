#!/usr/bin/env python3
"""SGH-Q33 smoke — TechnologyClearancePolicy bridge validator.

Validates static code invariants AND runs a mini synthetic smoke run.

Checks:
  - rust/vrs_solver/src/technology/clearance.rs exists
  - TechnologyClearancePolicy struct is defined
  - from_solver_input is defined
  - io.rs contains spacing_mm and kerf_mm optional fields
  - OptimizerDiagnosticsOutput contains technology_* fields
  - adapter.rs fills these fields in sparrow_cde_multisheet
  - No compression wired in via technology module
  - No legacy multisheet import caused by technology module
  - Q31 base-shape cache fields not regressed
  - Q32 sparrow_cde_multisheet pipeline not regressed
  - Mini synthetic run: technology_policy_active=true, correct values

Exit codes:
  0  PASS
  2  FAIL
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
INPUT_JSON = ROOT / "artifacts" / "benchmarks" / "sgh_q33" / "inputs" / "technology_policy_smoke.json"
OUTPUT_JSON = ROOT / "artifacts" / "benchmarks" / "sgh_q33" / "outputs" / "technology_policy_smoke_output.json"

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


# ── Static code invariants ────────────────────────────────────────────────────

def check_static_invariants() -> None:
    print("\n--- Static code invariants ---")

    clearance_rs_path = ROOT / "rust/vrs_solver/src/technology/clearance.rs"
    mod_rs_path = ROOT / "rust/vrs_solver/src/technology/mod.rs"
    io_rs_path = ROOT / "rust/vrs_solver/src/io.rs"
    adapter_rs_path = ROOT / "rust/vrs_solver/src/adapter.rs"
    lib_rs_path = ROOT / "rust/vrs_solver/src/lib.rs"

    clearance_rs = strip_comments(read(clearance_rs_path))
    mod_rs = strip_comments(read(mod_rs_path))
    io_rs = strip_comments(read(io_rs_path))
    adapter_rs = strip_comments(read(adapter_rs_path))
    lib_rs = strip_comments(read(lib_rs_path))

    # 1. File existence
    check(clearance_rs_path.exists(), "technology/clearance.rs exists")
    check(mod_rs_path.exists(), "technology/mod.rs exists")

    # 2. TechnologyClearancePolicy struct
    check("TechnologyClearancePolicy" in clearance_rs, "clearance.rs: TechnologyClearancePolicy struct defined")

    # 3. from_solver_input method
    check("from_solver_input" in clearance_rs, "clearance.rs: from_solver_input method defined")

    # 4. effective_* methods
    check("effective_sheet_margin_mm" in clearance_rs, "clearance.rs: effective_sheet_margin_mm defined")
    check("effective_part_spacing_mm" in clearance_rs, "clearance.rs: effective_part_spacing_mm defined")
    check("effective_kerf_mm" in clearance_rs, "clearance.rs: effective_kerf_mm defined")

    # 5. validate method
    check("fn validate" in clearance_rs, "clearance.rs: validate method defined")

    # 6. io.rs: spacing_mm and kerf_mm optional fields in SolverInput
    check("spacing_mm" in io_rs and "Option<f64>" in io_rs, "io.rs: spacing_mm: Option<f64> in SolverInput")
    check("kerf_mm" in io_rs and "Option<f64>" in io_rs, "io.rs: kerf_mm: Option<f64> in SolverInput")

    # 7. io.rs: technology_* fields in OptimizerDiagnosticsOutput
    check("technology_policy_active" in io_rs, "io.rs: technology_policy_active in OptimizerDiagnosticsOutput")
    check("technology_margin_mm" in io_rs, "io.rs: technology_margin_mm in OptimizerDiagnosticsOutput")
    check("technology_spacing_mm" in io_rs, "io.rs: technology_spacing_mm in OptimizerDiagnosticsOutput")
    check("technology_kerf_mm" in io_rs, "io.rs: technology_kerf_mm in OptimizerDiagnosticsOutput")
    check("technology_effective_sheet_margin_mm" in io_rs, "io.rs: technology_effective_sheet_margin_mm in OptimizerDiagnosticsOutput")
    check("technology_effective_part_spacing_mm" in io_rs, "io.rs: technology_effective_part_spacing_mm in OptimizerDiagnosticsOutput")
    check("technology_effective_kerf_mm" in io_rs, "io.rs: technology_effective_kerf_mm in OptimizerDiagnosticsOutput")

    # 8. adapter.rs: TechnologyClearancePolicy imported and used
    check("TechnologyClearancePolicy" in adapter_rs, "adapter.rs: TechnologyClearancePolicy imported/used")
    check("technology_policy" in adapter_rs, "adapter.rs: technology_policy created in solve/pipeline")
    check("technology_policy_active: Some(true)" in adapter_rs, "adapter.rs: technology_policy_active=Some(true) set in multisheet diag")

    # 9. lib.rs: technology module exported
    check("pub mod technology" in lib_rs, "lib.rs: pub mod technology exported")

    # 10. No compression wired via technology module
    raw_clearance = read(clearance_rs_path)
    raw_mod = read(mod_rs_path)
    check("compress" not in raw_clearance.lower(), "clearance.rs: no compression wired")
    check("compress" not in raw_mod.lower(), "technology/mod.rs: no compression wired")

    # 11. No legacy multisheet manager import in technology module
    check("MultiSheetManager" not in raw_clearance, "clearance.rs: no legacy MultiSheetManager import")

    # 12. Q31 base-shape cache fields not regressed
    check("sparrow_q31_base_shape_cache_build_ms" in io_rs, "io.rs: Q31 base-shape cache fields present (not regressed)")

    # 13. Q32 sparrow_cde_multisheet pipeline not regressed
    check("SparrowCdeMultisheet" in io_rs, "io.rs: Q32 SparrowCdeMultisheet enum variant present (not regressed)")
    check("sparrow_ms_active" in io_rs, "io.rs: Q32 sparrow_ms_active field present (not regressed)")

    # 14. No standalone part_spacing_mm or sheet_margin_mm field introduced (spec forbids these).
    # Check that pub field declarations with these exact names don't exist.
    raw_io = read(io_rs_path)
    check("pub part_spacing_mm" not in raw_io, "io.rs: no pub part_spacing_mm field (spec-forbidden)")
    check("pub sheet_margin_mm" not in raw_io, "io.rs: no pub sheet_margin_mm field (spec-forbidden)")


# ── Mini synthetic run ────────────────────────────────────────────────────────

def check_mini_run() -> None:
    print("\n--- Mini synthetic smoke run ---")

    if not SOLVER_BIN.exists():
        check(False, f"solver binary exists: {SOLVER_BIN}")
        return

    check(INPUT_JSON.exists(), f"smoke input exists: {INPUT_JSON.name}")
    if not INPUT_JSON.exists():
        return

    # Run the solver using --input / --output flags
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [str(SOLVER_BIN), "--input", str(INPUT_JSON), "--output", str(OUTPUT_JSON)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        check(False, "solver run completed within 60s timeout")
        return

    check(result.returncode == 0, f"solver exit code 0 (got {result.returncode})")
    if result.returncode != 0:
        print(f"    stderr: {result.stderr[:400]}")
        return

    try:
        output = load_json(OUTPUT_JSON)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        check(False, f"solver output is valid JSON: {e}")
        return

    # Acceptance checks
    status = output.get("status")
    check(status == "ok", f"status == ok (got {status!r})")

    od = output.get("optimizer_diagnostics") or {}

    check(od.get("technology_policy_active") is True, "optimizer_diagnostics.technology_policy_active == true")
    check(od.get("technology_margin_mm") == 10.0, f"technology_margin_mm == 10.0 (got {od.get('technology_margin_mm')})")
    check(od.get("technology_spacing_mm") == 2.0, f"technology_spacing_mm == 2.0 (got {od.get('technology_spacing_mm')})")
    check(od.get("technology_kerf_mm") == 0.15, f"technology_kerf_mm == 0.15 (got {od.get('technology_kerf_mm')})")
    check(od.get("technology_effective_sheet_margin_mm") == 10.0,
          f"technology_effective_sheet_margin_mm == 10.0 (got {od.get('technology_effective_sheet_margin_mm')})")
    check(od.get("technology_effective_part_spacing_mm") == 2.0,
          f"technology_effective_part_spacing_mm == 2.0 (got {od.get('technology_effective_part_spacing_mm')})")
    check(od.get("technology_effective_kerf_mm") == 0.15,
          f"technology_effective_kerf_mm == 0.15 (got {od.get('technology_effective_kerf_mm')})")

    final_pairs = od.get("sparrow_ms_final_pairs")
    boundary = od.get("sparrow_ms_boundary_violations")
    check(final_pairs == 0, f"final_pairs == 0 (got {final_pairs})")
    check(boundary == 0, f"boundary_violations == 0 (got {boundary})")

    # Q31 base-shape cache not regressed
    check("sparrow_q31_base_shape_cache_build_ms" in od, "Q31 base-shape cache field present in output diagnostics")

    # Q32 multisheet active
    check(od.get("sparrow_ms_active") is True, "Q32 sparrow_ms_active == true in output")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("=== SGH-Q33 TechnologyClearancePolicy smoke ===")
    check_static_invariants()
    check_mini_run()

    print(f"\n{'='*48}")
    print(f"  PASS: {PASS_COUNT}   FAIL: {FAIL_COUNT}")
    if FAIL_COUNT > 0:
        print("  RESULT: FAIL")
        sys.exit(2)
    else:
        print("  RESULT: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
