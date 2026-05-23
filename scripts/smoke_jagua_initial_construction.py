#!/usr/bin/env python3
"""JG-08 smoke: initial construction placer V1 contract verification.

Checks:
  1. Small fixture: all parts placed, exact validator PASS
  2. Medium fixture: status ok or partial, exact validator PASS
  3. placed_count + unplaced_count == total instance count
  4. Determinism: same input + seed → identical placement list (two runs)
  5. Negative: mutable output with overlap → validator raises ValueError
  6. Negative: invalid sheet_index → validator raises ValueError
  7. Regression: JG-06 item geometry store smoke fixture still valid
  8. Regression: JG-05 rectangular sheet provider medium fixture still valid
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
        sys.exit(1)
    return str(release)


def _run_solver(solver_bin: str, inp: dict, run_dir: Path) -> tuple[int, dict | None]:
    run_dir.mkdir(parents=True, exist_ok=True)
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


def _base(name: str = "jg08_smoke", **kwargs) -> dict:
    base = {
        "contract_version": "v1",
        "project_name": name,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "seed": 42,
        "time_limit_s": 5,
    }
    base.update(kwargs)
    return base


def _total_instances(inp: dict) -> int:
    return sum(p["quantity"] for p in inp["parts"])


# ---------------------------------------------------------------------------
# Check 1: small fixture — all parts placed, exact validator PASS
# ---------------------------------------------------------------------------
def check_small_fixture(solver_bin: str, tmp: Path) -> None:
    print("\n[Small fixture: all parts placed + exact validator PASS]")
    inp = _base(
        stocks=[{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        parts=[
            {"id": "A", "width": 50, "height": 50, "quantity": 3, "allowed_rotations_deg": [0]},
            {"id": "B", "width": 80, "height": 30, "quantity": 2, "allowed_rotations_deg": [0, 90]},
        ],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "small")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    placed = out.get("placements", [])
    unplaced = out.get("unplaced", [])
    total = _total_instances(inp)
    if len(placed) == total and len(unplaced) == 0:
        _pass(f"all {total} instances placed (status={out.get('status')})")
    else:
        _fail(f"expected {total} placed, got placed={len(placed)}, unplaced={len(unplaced)}")
    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS on small fixture")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")


# ---------------------------------------------------------------------------
# Check 2: medium fixture — status ok/partial, exact validator PASS
# ---------------------------------------------------------------------------
def check_medium_fixture(solver_bin: str, tmp: Path) -> None:
    print("\n[Medium fixture: status ok/partial + exact validator PASS]")
    inp = _base(
        name="jg08_medium",
        stocks=[
            {"id": "SHEET_A", "quantity": 2, "width": 100, "height": 100},
            {"id": "SHEET_B", "quantity": 1, "width": 200, "height": 150},
        ],
        parts=[
            {"id": "PART_A", "width": 90, "height": 90, "quantity": 2, "allowed_rotations_deg": [0]},
            {"id": "PART_B", "width": 180, "height": 130, "quantity": 1, "allowed_rotations_deg": [0]},
        ],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "medium")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    if out.get("status") in ("ok", "partial"):
        _pass(f"status={out.get('status')}")
    else:
        _fail(f"unexpected status: {out.get('status')}")
    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS on medium fixture")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")


# ---------------------------------------------------------------------------
# Check 3: placed + unplaced == total instance count
# ---------------------------------------------------------------------------
def check_count_invariant(solver_bin: str, tmp: Path) -> None:
    print("\n[Count invariant: placed_count + unplaced_count == total]")
    inp = _base(
        stocks=[{"id": "S", "quantity": 1, "width": 80, "height": 80}],
        parts=[
            {"id": "A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]},
            {"id": "B", "width": 200, "height": 200, "quantity": 1, "allowed_rotations_deg": [0]},  # too big
        ],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "count")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    placed = len(out.get("placements", []))
    unplaced = len(out.get("unplaced", []))
    total = _total_instances(inp)
    if placed + unplaced == total:
        _pass(f"placed={placed} + unplaced={unplaced} == total={total}")
    else:
        _fail(f"mismatch: placed={placed} + unplaced={unplaced} != total={total}")


# ---------------------------------------------------------------------------
# Check 4: determinism — two runs with same seed produce identical placements
# ---------------------------------------------------------------------------
def check_determinism(solver_bin: str, tmp: Path) -> None:
    print("\n[Determinism: same input + seed → identical placements]")
    inp = _base(
        stocks=[{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        parts=[
            {"id": "A", "width": 60, "height": 40, "quantity": 3, "allowed_rotations_deg": [0, 90]},
            {"id": "B", "width": 80, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]},
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
    p1 = sorted(out1.get("placements", []), key=lambda p: p["instance_id"])
    p2 = sorted(out2.get("placements", []), key=lambda p: p["instance_id"])
    if json.dumps(p1) == json.dumps(p2):
        _pass(f"identical placements across 2 runs ({len(p1)} placed)")
    else:
        _fail(f"placements differ: {p1} vs {p2}")


# ---------------------------------------------------------------------------
# Check 5: negative — mutable overlap in output → validator rejects
# ---------------------------------------------------------------------------
def check_negative_overlap(solver_bin: str, tmp: Path) -> None:
    print("\n[Negative: artificially overlapping placements → validator rejects]")
    inp = _base(
        stocks=[{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        parts=[{"id": "A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]}],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "neg_overlap")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    # Force overlap by placing second item at same position as first
    if len(out.get("placements", [])) >= 2:
        out["placements"][1]["x"] = out["placements"][0]["x"]
        out["placements"][1]["y"] = out["placements"][0]["y"]
    else:
        # Only 1 placed — inject a duplicate manually
        if out.get("placements"):
            dup = dict(out["placements"][0])
            dup["instance_id"] = "A__0002"
            out.setdefault("placements", []).append(dup)
            out["metrics"]["placed_count"] += 1
    try:
        validate_multi_sheet_output(inp, out)
        _fail("validator accepted overlapping placements (should have raised)")
    except Exception:
        _pass("validator correctly rejected overlapping placements")


# ---------------------------------------------------------------------------
# Check 6: negative — invalid sheet_index → validator rejects
# ---------------------------------------------------------------------------
def check_negative_sheet_index(solver_bin: str, tmp: Path) -> None:
    print("\n[Negative: invalid sheet_index → validator rejects]")
    inp = _base(
        stocks=[{"id": "S", "quantity": 1, "width": 300, "height": 200}],
        parts=[{"id": "A", "width": 50, "height": 50, "quantity": 1, "allowed_rotations_deg": [0]}],
    )
    rc, out = _run_solver(solver_bin, inp, tmp / "neg_sheet")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    if out.get("placements"):
        out["placements"][0]["sheet_index"] = 9999
    try:
        validate_multi_sheet_output(inp, out)
        _fail("validator accepted invalid sheet_index=9999 (should have raised)")
    except Exception:
        _pass("validator correctly rejected invalid sheet_index=9999")


# ---------------------------------------------------------------------------
# Check 7: regression — JG-06 smoke fixture still valid
# ---------------------------------------------------------------------------
def check_regression_jg06(solver_bin: str, tmp: Path) -> None:
    print("\n[Regression: JG-05 smoke fixture (JG-06 regression) still valid]")
    fixture = ROOT / "tests/fixtures/egyedi_solver/jagua_rect_smoke.json"
    if not fixture.is_file():
        _fail(f"fixture missing: {fixture}")
        return
    inp = json.loads(fixture.read_text(encoding="utf-8"))
    rc, out = _run_solver(solver_bin, inp, tmp / "jg06_reg")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    if out.get("status") != "ok":
        _fail(f"unexpected status: {out.get('status')}")
        return
    _pass("status=ok on JG-05 smoke fixture")
    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS on JG-05 smoke fixture")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")


# ---------------------------------------------------------------------------
# Check 8: regression — JG-05 medium fixture still maps to correct sheet indices
# ---------------------------------------------------------------------------
def check_regression_jg05_medium(solver_bin: str, tmp: Path) -> None:
    print("\n[Regression: JG-05 medium fixture sheet_index mapping still correct]")
    fixture = ROOT / "tests/fixtures/egyedi_solver/jagua_rect_medium.json"
    if not fixture.is_file():
        _fail(f"fixture missing: {fixture}")
        return
    inp = json.loads(fixture.read_text(encoding="utf-8"))
    rc, out = _run_solver(solver_bin, inp, tmp / "jg05_med")
    if rc != 0 or out is None:
        _fail(f"solver failed (exit={rc})")
        return
    if out.get("status") == "ok":
        _pass("status=ok on JG-05 medium fixture")
    else:
        _fail(f"unexpected status: {out.get('status')}")
        return
    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS on JG-05 medium fixture")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")
        return
    # Sheet index sanity: all indices in [0, 2]
    placements = out.get("placements", [])
    sheet_indices = {p["sheet_index"] for p in placements}
    max_idx = max(sheet_indices) if sheet_indices else -1
    if max_idx <= 2:
        _pass(f"all sheet indices in valid range [0, 2]: {sorted(sheet_indices)}")
    else:
        _fail(f"unexpected sheet index: max={max_idx}")


def main() -> int:
    print("=== JG-08 Initial Construction Placer Smoke ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    with tempfile.TemporaryDirectory(prefix="jg08_smoke_") as tmp:
        p = Path(tmp)
        check_small_fixture(solver_bin, p)
        check_medium_fixture(solver_bin, p)
        check_count_invariant(solver_bin, p)
        check_determinism(solver_bin, p)
        check_negative_overlap(solver_bin, p)
        check_negative_sheet_index(solver_bin, p)
        check_regression_jg06(solver_bin, p)
        check_regression_jg05_medium(solver_bin, p)

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
