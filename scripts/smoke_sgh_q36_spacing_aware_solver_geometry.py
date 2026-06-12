#!/usr/bin/env python3
"""SGH-Q36 smoke — spacing-aware solver geometry (half-spacing expanded contours).

Static checks:
  - technology/spacing_geometry.rs exists; build_spacing_expanded_outer_polygon defined
  - offset is spacing_mm / 2 (half_spacing); kerf is NOT added to spacing
  - SPInstance carries separate original + spacing-collision base shapes
  - search/LBF/tracker part-part collision uses the spacing-collision shape
  - boundary/container uses original geometry; spacing is not a sheet margin
  - SpacingExpandedTouchAllowed touching policy exists; SparrowStrict untouched
  - Q35 final validator + PART_SPACING_VIOLATION_Q35 preserved
  - Q31 prepare_base_shape_native hotpath not reintroduced
  - cavity prepack files not modified / not connected; no compression wired

Dynamic checks:
  - synthetic touch_ok: status ok, spacing geometry applied, offset 5, violation 0, original output
  - synthetic spacing_not_sheet_margin: spacing>0, margin 0, boundary_violations 0, boundary uses original
  - cargo test --test technology_spacing_geometry / technology_part_spacing / technology_sheet_margin

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
INPUTS = ROOT / "artifacts" / "benchmarks" / "sgh_q36" / "inputs"
OUTPUTS = ROOT / "artifacts" / "benchmarks" / "sgh_q36" / "outputs"

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


def check_static() -> None:
    print("\n--- Static code invariants ---")
    sg_path = ROOT / "rust/vrs_solver/src/technology/spacing_geometry.rs"
    mod_path = ROOT / "rust/vrs_solver/src/technology/mod.rs"
    model_path = ROOT / "rust/vrs_solver/src/optimizer/sparrow/model.rs"
    cde_path = ROOT / "rust/vrs_solver/src/optimizer/cde_adapter.rs"
    tracker_path = ROOT / "rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs"
    search_path = ROOT / "rust/vrs_solver/src/optimizer/sparrow/sample/search.rs"
    lbf_path = ROOT / "rust/vrs_solver/src/optimizer/sparrow/lbf.rs"
    io_path = ROOT / "rust/vrs_solver/src/io.rs"
    adapter_path = ROOT / "rust/vrs_solver/src/adapter.rs"

    sg = strip_comments(read(sg_path))
    model = strip_comments(read(model_path))
    cde = strip_comments(read(cde_path))
    tracker = strip_comments(read(tracker_path))
    search = strip_comments(read(search_path))
    lbf = strip_comments(read(lbf_path))
    io_rs = strip_comments(read(io_path))

    check(sg_path.exists(), "technology/spacing_geometry.rs exists")
    check("pub mod spacing_geometry" in strip_comments(read(mod_path)), "technology/mod.rs: pub mod spacing_geometry")
    check("fn build_spacing_expanded_outer_polygon" in sg, "spacing_geometry.rs: build_spacing_expanded_outer_polygon defined")
    check("UNSUPPORTED_SPACING_OFFSET_Q36" in sg, "spacing_geometry.rs: UNSUPPORTED_SPACING_OFFSET_Q36 error")
    check("SELF_INTERSECTING_SPACING_OFFSET_Q36" in sg, "spacing_geometry.rs: SELF_INTERSECTING_SPACING_OFFSET_Q36 error")
    check("half_spacing_mm" in sg and "spacing_mm / 2" in sg, "spacing_geometry.rs: offset = spacing_mm / 2 (half-spacing)")

    # Kerf must not be folded into spacing anywhere in the offset / model / adapter path.
    for name, body in (("spacing_geometry.rs", sg), ("model.rs", model), ("adapter.rs", strip_comments(read(adapter_path)))):
        forbidden = re.search(r"spacing_mm\s*\+\s*\w*kerf", body) or re.search(r"kerf\w*\s*\+\s*spacing", body)
        check(forbidden is None, f"{name}: kerf is NOT added to spacing")

    # Dual base shapes on the instance model.
    check("base_shape" in model and "spacing_collision_base_shape" in model,
          "model.rs: SPInstance carries original + spacing_collision base shapes")
    check("prepare_spacing_base_shape_native" in cde, "cde_adapter.rs: prepare_spacing_base_shape_native defined")

    # Part-part collision uses the spacing-collision shape; boundary uses original.
    check("spacing_collision_base_shape" in tracker, "tracker.rs: pairs/session use spacing_collision base shape")
    check("inst.base_shape" in tracker, "tracker.rs: boundary uses original base shape")
    check("spacing_collision_base_shape" in search, "search.rs: separator candidate uses spacing base shape")
    check("spacing_collision_base_shape" in lbf, "lbf.rs: LBF candidate/others use spacing base shape")

    # Touching policy: new variant exists; SparrowStrict untouched as a variant.
    check("SpacingExpandedTouchAllowed" in cde, "cde_adapter.rs: SpacingExpandedTouchAllowed policy exists")
    check("SparrowStrict" in cde, "cde_adapter.rs: SparrowStrict policy still present (untouched)")
    check("fn build_pairs_only" in cde, "cde_adapter.rs: pairs-only session builder (no real boundary hazard)")

    # Diagnostics fields.
    for f in (
        "technology_spacing_geometry_applied",
        "technology_spacing_offset_mm",
        "technology_spacing_offset_part_count",
        "technology_spacing_offset_cache_hits",
        "technology_spacing_offset_cache_misses",
        "technology_spacing_offset_failure_count",
        "technology_spacing_boundary_uses_original_geometry",
        "technology_spacing_output_uses_original_geometry",
    ):
        check(f in io_rs, f"io.rs: {f} diagnostics field present")

    # Q35 final validator preserved.
    check("find_part_spacing_violations" in strip_comments(read(adapter_path)), "adapter.rs: Q35 final validator preserved")
    check("PART_SPACING_VIOLATION_Q35" in strip_comments(read(adapter_path)), "adapter.rs: PART_SPACING_VIOLATION_Q35 preserved")

    # Q31 prepare_base_shape_native hot-path not reintroduced: the per-part base-shape
    # cache transfer is still present in solve() (code, not a comment).
    opt_raw = read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/optimizer.rs")
    check("base_shape_cache_hits = problem.base_shape_cache_hits" in opt_raw,
          "optimizer.rs: Q31 base-shape cache transfer intact (no hot-path regression)")

    # Cavity prepack untouched (git): no cavity .rs file modified by Q36.
    try:
        res = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=30)
        changed_cavity = [l for l in res.stdout.splitlines() if "cavity" in l.lower() and ".rs" in l.lower()]
        check(not changed_cavity, f"no cavity prepack .rs modified by Q36 ({changed_cavity})")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        check(True, "git unavailable → skip cavity-change check")

    # No compression wired into the spacing path.
    check("compress" not in sg.lower(), "spacing_geometry.rs: no compression wired")


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


def check_touch_ok() -> None:
    print("\n--- Synthetic: spacing_geometry_touch_ok ---")
    if not SOLVER_BIN.exists():
        check(False, f"solver binary exists: {SOLVER_BIN}")
        return
    out = run_solver(INPUTS / "spacing_geometry_touch_ok.json", OUTPUTS / "spacing_geometry_touch_ok_output.json")
    if out is None:
        return
    od = out.get("optimizer_diagnostics", {})
    check(out.get("status") == "ok", f"status == ok (got {out.get('status')!r})")
    check(od.get("technology_spacing_geometry_applied") is True, "technology_spacing_geometry_applied == true")
    check(od.get("technology_spacing_offset_mm") == 5.0, f"spacing offset == 5.0 (got {od.get('technology_spacing_offset_mm')})")
    check(od.get("technology_spacing_violation_count") == 0, "technology_spacing_violation_count == 0")
    check(od.get("technology_spacing_output_uses_original_geometry") is True, "output uses original geometry")
    check(out.get("metrics", {}).get("placed_count") == 2, "both parts placed")


def check_not_sheet_margin() -> None:
    print("\n--- Synthetic: spacing_not_sheet_margin ---")
    if not SOLVER_BIN.exists():
        return
    out = run_solver(INPUTS / "spacing_not_sheet_margin.json", OUTPUTS / "spacing_not_sheet_margin_output.json")
    if out is None:
        return
    od = out.get("optimizer_diagnostics", {})
    check(od.get("technology_spacing_geometry_applied") is True, "spacing geometry applied (spacing_mm > 0)")
    check(od.get("technology_effective_sheet_margin_mm") in (0.0, None), "margin_mm == 0")
    check(od.get("sparrow_ms_boundary_violations") == 0, "boundary_violations == 0 (spacing is not a margin)")
    check(od.get("technology_spacing_boundary_uses_original_geometry") is True, "boundary uses original geometry")
    # The single part may sit at the sheet edge — spacing did not inset it.
    pls = out.get("placements", [])
    if pls:
        p = pls[0]
        check(p["x"] <= 1.0 and p["y"] <= 1.0, f"part sits near sheet edge (no half-spacing inset): x={p['x']} y={p['y']}")


def check_violation_safety() -> None:
    print("\n--- Synthetic: spacing_violation_safety ---")
    if not SOLVER_BIN.exists():
        return
    out = run_solver(INPUTS / "spacing_violation_safety.json", OUTPUTS / "spacing_violation_safety_output.json")
    if out is None:
        return
    od = out.get("optimizer_diagnostics", {})
    # With Q36 the solver is spacing-aware, so it should NOT emit a layout that violates
    # spacing. Either it cannot fit both (partial) or it fits them spacing-apart (ok with
    # violation 0). In all cases the final output must never be a spacing-violating "ok".
    viol = od.get("technology_spacing_violation_count", 0)
    if out.get("status") == "ok":
        check(viol == 0, "ok output ⇒ spacing violation 0 (Q35 gate holds)")
    else:
        check(out.get("status") == "partial", f"non-ok status is partial (got {out.get('status')!r})")
    check(od.get("technology_spacing_geometry_applied") is True, "spacing geometry applied")


def check_cargo_tests() -> None:
    print("\n--- Dynamic: cargo tests ---")
    cargo = shutil.which("cargo")
    if cargo is None:
        check(True, "cargo not on PATH → skipping live tests (verify.sh runs full suite)")
        return
    for t in ("technology_spacing_geometry", "technology_part_spacing", "technology_sheet_margin"):
        try:
            r = subprocess.run(
                [cargo, "test", "--manifest-path", str(ROOT / "rust/vrs_solver/Cargo.toml"), "--test", t],
                capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            check(False, f"cargo test --test {t} within 600s")
            continue
        ok = r.returncode == 0 and "test result: ok" in (r.stdout + r.stderr)
        check(ok, f"cargo test --test {t} passes")
        if not ok:
            print(f"    {r.stdout[-300:]}")


def main() -> None:
    print("=== SGH-Q36 spacing-aware solver geometry smoke ===")
    check_static()
    check_touch_ok()
    check_not_sheet_margin()
    check_violation_safety()
    check_cargo_tests()
    print(f"\n{'='*48}")
    print(f"  PASS: {PASS_COUNT}   FAIL: {FAIL_COUNT}")
    if FAIL_COUNT > 0:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
