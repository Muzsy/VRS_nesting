#!/usr/bin/env python3
"""JG-06 smoke: ItemGeometryStore + rotation cache contract verification.

Checks:
  1. Determinism: same input twice → identical solver output (instance ordering, placements)
  2. Rotation 90° bbox: part fits in rotated orientation but not original
  3. Duplicate rotations [0,0,90] → same result as [0,90]
  4. Unsupported rotation (45°) → solver exits non-zero
  5. All four rotations (0/90/180/270) → valid layout on a fixture
  6. Regression: JG-05 smoke fixture still produces ok status + exact validator PASS
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
        print("cargo build failed", file=sys.stderr)
        sys.exit(1)
    return str(release)


def _run_solver(solver_bin: str, inp: dict, run_dir: Path) -> tuple[int, dict | None]:
    input_path = run_dir / "solver_input.json"
    output_path = run_dir / "solver_output.json"
    input_path.write_text(json.dumps(inp), encoding="utf-8")
    r = subprocess.run(
        [solver_bin, "--input", str(input_path), "--output", str(output_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not output_path.is_file():
        return r.returncode, None
    return 0, json.loads(output_path.read_text(encoding="utf-8"))


def _base_input(**kwargs) -> dict:
    base = {
        "contract_version": "v1",
        "project_name": "jg06_smoke",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
    }
    base.update(kwargs)
    return base


def check_determinism(solver_bin: str, tmp: Path) -> None:
    print("\n[Determinism: same input → identical output]")
    inp = _base_input(
        stocks=[{"id": "S", "quantity": 1, "width": 200, "height": 200}],
        parts=[
            {"id": "A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]},
            {"id": "B", "width": 80, "height": 30, "quantity": 1, "allowed_rotations_deg": [0]},
        ],
    )
    rc1, out1 = _run_solver(solver_bin, inp, tmp / "det1")
    rc2, out2 = _run_solver(solver_bin, inp, tmp / "det2")
    if rc1 != 0 or out1 is None:
        _fail(f"run1 failed (exit={rc1})")
        return
    if rc2 != 0 or out2 is None:
        _fail(f"run2 failed (exit={rc2})")
        return
    placements1 = sorted(out1.get("placements", []), key=lambda p: p["instance_id"])
    placements2 = sorted(out2.get("placements", []), key=lambda p: p["instance_id"])
    if json.dumps(placements1) == json.dumps(placements2):
        _pass(f"identical placements across 2 runs ({len(placements1)} placed)")
    else:
        _fail(f"placements differ between runs: {placements1} vs {placements2}")


def check_rotation_90_bbox(solver_bin: str, tmp: Path) -> None:
    print("\n[Rotation 90°: part fits only when rotated]")
    # Part 30×100, sheet 100×50 — fits at rot=90 (30w×100h→100w×30h? No)
    # Part width=120, height=30: at rot=0 → 120×30, at rot=90 → 30×120
    # Sheet 50×100: rot=0 fails (120>50), rot=90 → 30×120 — 30<=50 but 120>100? No.
    # Let's use: Part width=80, height=30; sheet 40×100
    # rot=0 → 80×30: 80>40 → fails; rot=90 → 30×80: 30<=40, 80<=100 → fits
    inp = _base_input(
        stocks=[{"id": "S", "quantity": 1, "width": 40, "height": 100}],
        parts=[{"id": "P", "width": 80, "height": 30, "quantity": 1, "allowed_rotations_deg": [0, 90]}],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "rot90")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    placements = out.get("placements", [])
    unplaced = out.get("unplaced", [])
    if len(placements) == 1 and placements[0]["rotation_deg"] == 90:
        _pass("part placed at rotation=90 (width=80 > sheet_w=40, only fits rotated)")
    elif len(unplaced) == 1:
        _fail("part went unplaced — rotation 90° not being tried correctly")
    else:
        _fail(f"unexpected: placements={placements}, unplaced={unplaced}")


def check_duplicate_rotation_dedupe(solver_bin: str, tmp: Path) -> None:
    print("\n[Duplicate rotation dedupe: [0,0,90] same as [0,90]]")
    inp_dup = _base_input(
        stocks=[{"id": "S", "quantity": 1, "width": 200, "height": 100}],
        parts=[{"id": "P", "width": 60, "height": 40, "quantity": 2, "allowed_rotations_deg": [0, 0, 90, 90]}],
    )
    inp_clean = _base_input(
        stocks=[{"id": "S", "quantity": 1, "width": 200, "height": 100}],
        parts=[{"id": "P", "width": 60, "height": 40, "quantity": 2, "allowed_rotations_deg": [0, 90]}],
    )
    rc_dup, out_dup = _run_solver(solver_bin, inp_dup, tmp / "dup")
    rc_clean, out_clean = _run_solver(solver_bin, inp_clean, tmp / "clean")
    if rc_dup != 0 or out_dup is None:
        _fail(f"dup input failed (exit={rc_dup})")
        return
    if rc_clean != 0 or out_clean is None:
        _fail(f"clean input failed (exit={rc_clean})")
        return
    p_dup = sorted(out_dup.get("placements", []), key=lambda p: p["instance_id"])
    p_clean = sorted(out_clean.get("placements", []), key=lambda p: p["instance_id"])
    if json.dumps(p_dup) == json.dumps(p_clean):
        _pass("duplicate rotations produce identical placement to deduped list")
    else:
        _fail(f"mismatch: dup={p_dup}, clean={p_clean}")


def check_unsupported_rotation(solver_bin: str, tmp: Path) -> None:
    print("\n[Unsupported rotation 45° → solver exits non-zero]")
    inp = _base_input(
        stocks=[{"id": "S", "quantity": 1, "width": 200, "height": 200}],
        parts=[{"id": "P", "width": 50, "height": 50, "quantity": 1, "allowed_rotations_deg": [45]}],
    )
    rc, _ = _run_solver(solver_bin, inp, tmp / "unsup")
    if rc != 0:
        _pass(f"solver correctly rejected rotation=45 (exit={rc})")
    else:
        _fail("solver accepted unsupported rotation=45 without error")


def check_all_four_rotations(solver_bin: str, tmp: Path) -> None:
    print("\n[All four rotations 0/90/180/270 valid and produce exact PASS]")
    # Use a large sheet, part with all 4 rotations, multiple instances
    inp = _base_input(
        stocks=[{"id": "S", "quantity": 1, "width": 500, "height": 500}],
        parts=[{"id": "P", "width": 100, "height": 40, "quantity": 4, "allowed_rotations_deg": [0, 90, 180, 270]}],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "four_rot")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    placements = out.get("placements", [])
    if len(placements) == 4:
        _pass(f"all 4 instances placed (rotations used: {sorted({p['rotation_deg'] for p in placements})})")
    else:
        _fail(f"expected 4 placed, got {len(placements)}")
    # Exact validator
    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS on 4-rotation layout")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")


def check_regression_jg05_smoke(solver_bin: str, tmp: Path) -> None:
    print("\n[Regression: JG-05 smoke fixture still valid]")
    fixture = ROOT / "tests/fixtures/egyedi_solver/jagua_rect_smoke.json"
    if not fixture.is_file():
        _fail(f"JG-05 smoke fixture missing: {fixture}")
        return
    inp = json.loads(fixture.read_text(encoding="utf-8"))
    rc, out = _run_solver(solver_bin, inp, tmp / "jg05_reg")
    if rc != 0 or out is None:
        _fail(f"solver failed on JG-05 fixture (exit={rc})")
        return
    if out.get("status") != "ok":
        _fail(f"unexpected status: {out.get('status')}")
        return
    _pass("solver status=ok")
    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS on JG-05 smoke fixture")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")


def main() -> int:
    print("=== JG-06 Item Geometry Store Smoke ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    with tempfile.TemporaryDirectory(prefix="jg06_smoke_") as tmp:
        p = Path(tmp)
        for d in ["det1", "det2", "rot90", "dup", "clean", "unsup", "four_rot", "jg05_reg"]:
            (p / d).mkdir()

        check_determinism(solver_bin, p)
        check_rotation_90_bbox(solver_bin, p)
        check_duplicate_rotation_dedupe(solver_bin, p)
        check_unsupported_rotation(solver_bin, p)
        check_all_four_rotations(solver_bin, p)
        check_regression_jg05_smoke(solver_bin, p)

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
