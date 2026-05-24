#!/usr/bin/env python3
"""JG-19 smoke: remnant/sheet cost score model V1 verification.

Checks:
  1.  Fixture jagua_remnant_score_model_v1.json exists with expected fields.
  2.  Fixture has mixed regular + remnant stocks with different cost_per_use.
  3.  Solver runs fixture → status ok/partial, placed >= 1, score_breakdown present.
  4.  score_breakdown contains all required JG-19 fields.
  5.  usable_area_utilization is in (0, 1] for placed items.
  6.  Rectangular regression: solver runs rect-only fixture, score breakdown present.
  7.  Remnant preference score evidence: remnant sheet score < regular sheet score (unit evidence).
  8.  Invalid layout dominance: overlap/boundary violation layout scores worse than valid.
  9.  cargo test --manifest-path rust/vrs_solver/Cargo.toml passes (includes JG-19 score tests).
  10. JG-18 irregular candidate regression (smoke_jagua_irregular_candidate_generation.py).
  11. JG-17 boundary validation regression (smoke_jagua_irregular_boundary_validation.py).
  12. Default cost_per_use=None backward compatibility: stock without cost_per_use gets cost=1.0.
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

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "egyedi_solver" / "jagua_remnant_score_model_v1.json"
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
# Check 1: fixture exists
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
    if "score_model" not in notes:
        _fail("fixture missing score_model in _fixture_notes")
        return None
    _pass("fixture exists; score_model documented")
    return data


# ---------------------------------------------------------------------------
# Check 2: fixture has mixed regular + remnant stocks
# ---------------------------------------------------------------------------
def check_fixture_mixed_stocks(data: dict) -> None:
    print("\n[Check 2: Fixture has mixed regular + remnant stocks with different cost_per_use]")
    stocks = data.get("stocks", [])
    if len(stocks) < 2:
        _fail(f"fixture must have >= 2 stocks, got {len(stocks)}")
        return
    costs = [s.get("cost_per_use") for s in stocks]
    if len(set(costs)) < 2:
        _fail(f"all stocks have same cost_per_use={costs[0]!r} — need at least 2 different costs")
        return
    _pass(f"fixture has {len(stocks)} stocks with distinct cost_per_use values: {costs}")


# ---------------------------------------------------------------------------
# Check 3: solver runs fixture, placed >= 1, score_breakdown present
# ---------------------------------------------------------------------------
def check_solver_runs_fixture(solver_bin: str, data: dict) -> None:
    print("\n[Check 3: Solver runs mixed fixture → placed >= 1, score_breakdown present]")
    out = _run_solver(solver_bin, data)
    if out is None:
        _fail("mixed fixture: no solver output")
        return
    status = out.get("status", "")
    if status == "unsupported":
        _fail(f"mixed fixture returned unsupported: {out.get('unsupported_reason')!r}")
        return
    placed = out.get("metrics", {}).get("placed_count", 0)
    if placed < 1:
        _fail(f"mixed fixture: placed={placed} — at least 1 must be placed")
        return
    sb = out.get("score_breakdown")
    if sb is None:
        _fail("score_breakdown absent from Phase1 output — expected for jagua_optimizer_phase1_outer_only")
        return
    _pass(f"mixed fixture: status={status!r}, placed={placed}, score_breakdown present")


# ---------------------------------------------------------------------------
# Check 4: score_breakdown has all required JG-19 fields
# ---------------------------------------------------------------------------
def check_score_breakdown_fields(solver_bin: str, data: dict) -> None:
    print("\n[Check 4: score_breakdown has all required JG-19 fields]")
    out = _run_solver(solver_bin, data)
    if out is None or out.get("score_breakdown") is None:
        _fail("no score_breakdown in output")
        return
    sb = out["score_breakdown"]
    required = [
        "total_cost", "placed_area_contribution", "unplaced_contribution",
        "sheet_cost_contribution", "sheet_cost_total", "usable_area_utilization",
        "overlap_contribution", "boundary_contribution", "compactness_contribution",
    ]
    missing = [f for f in required if f not in sb]
    if missing:
        _fail(f"score_breakdown missing fields: {missing}")
        return
    _pass(f"score_breakdown has all {len(required)} required JG-19 fields")
    print(f"    total_cost={sb['total_cost']:.4f} sheet_cost_total={sb['sheet_cost_total']:.4f} "
          f"utilization={sb['usable_area_utilization']:.4f}")


# ---------------------------------------------------------------------------
# Check 5: usable_area_utilization in (0, 1]
# ---------------------------------------------------------------------------
def check_utilization(solver_bin: str, data: dict) -> None:
    print("\n[Check 5: usable_area_utilization in (0, 1] for placed items]")
    out = _run_solver(solver_bin, data)
    if out is None or out.get("score_breakdown") is None:
        _fail("no score_breakdown")
        return
    sb = out["score_breakdown"]
    util = sb.get("usable_area_utilization", 0.0)
    placed = out.get("metrics", {}).get("placed_count", 0)
    if placed > 0 and 0.0 < util <= 1.0:
        _pass(f"usable_area_utilization={util:.6f} in (0, 1] for placed={placed}")
    elif placed == 0 and util == 0.0:
        _pass(f"usable_area_utilization=0.0 for placed=0 (correct)")
    else:
        _fail(f"usable_area_utilization={util:.6f} unexpected for placed={placed}")


# ---------------------------------------------------------------------------
# Check 6: rectangular regression — rect-only fixture runs, score_breakdown present
# ---------------------------------------------------------------------------
def check_rect_regression(solver_bin: str) -> None:
    print("\n[Check 6: Rectangular regression — rect-only fixture, score_breakdown present]")
    rect_input = {
        "contract_version": "v1",
        "project_name": "jg19_rect_regression",
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
    if status not in ("ok", "partial"):
        _fail(f"rectangular regression: unexpected status={status!r}")
        return
    sb = out.get("score_breakdown")
    if sb is None:
        _fail("rectangular regression: score_breakdown absent")
        return
    # cost_per_use not set → sheet_cost_total should equal sheet_count_used (backward compat)
    sheet_count = out.get("metrics", {}).get("sheet_count_used", 0)
    sct = sb.get("sheet_cost_total", -1.0)
    if abs(sct - float(sheet_count)) < 1e-9:
        _pass(f"rectangular regression: status={status!r}, sheet_cost_total={sct} == sheet_count_used={sheet_count} (backward compat)")
    else:
        _fail(f"rectangular regression: sheet_cost_total={sct} != sheet_count_used={sheet_count}")


# ---------------------------------------------------------------------------
# Check 7: remnant preference score evidence
# ---------------------------------------------------------------------------
def check_remnant_preference(solver_bin: str) -> None:
    print("\n[Check 7: Remnant preference score evidence (remnant sheet cost < regular sheet cost)]")
    # Two identical runs: one with regular stock, one with remnant (lower cost)
    # Same items, same geometry, only cost_per_use differs → remnant must have lower total_cost
    base = {
        "contract_version": "v1",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "parts": [{"id": "A", "width": 50, "height": 50, "quantity": 2, "allowed_rotations_deg": [0]}],
    }
    regular_input = {**base, "project_name": "jg19_regular",
                     "stocks": [{"id": "R", "quantity": 1, "width": 200, "height": 200, "cost_per_use": 1.0}]}
    remnant_input = {**base, "project_name": "jg19_remnant",
                     "stocks": [{"id": "Rem", "quantity": 1, "width": 200, "height": 200, "cost_per_use": 0.2}]}
    out_regular = _run_solver(solver_bin, regular_input)
    out_remnant = _run_solver(solver_bin, remnant_input)
    if out_regular is None or out_remnant is None:
        _fail("remnant preference: solver did not produce output for one or both runs")
        return
    sb_r = out_regular.get("score_breakdown")
    sb_rem = out_remnant.get("score_breakdown")
    if sb_r is None or sb_rem is None:
        _fail("remnant preference: score_breakdown absent from one or both runs")
        return
    tc_regular = sb_r["total_cost"]
    tc_remnant = sb_rem["total_cost"]
    sct_regular = sb_r["sheet_cost_total"]
    sct_remnant = sb_rem["sheet_cost_total"]
    if tc_remnant < tc_regular:
        _pass(f"remnant total_cost={tc_remnant:.2f} < regular total_cost={tc_regular:.2f} "
              f"(sheet_cost_total: remnant={sct_remnant:.2f}, regular={sct_regular:.2f})")
    else:
        _fail(f"remnant preference FAIL: remnant total_cost={tc_remnant:.2f} >= regular={tc_regular:.2f}")


# ---------------------------------------------------------------------------
# Check 8: invalid layout dominance — overlap/boundary score worse than valid
# ---------------------------------------------------------------------------
def check_invalid_layout_dominance(solver_bin: str) -> None:
    print("\n[Check 8: Invalid layout dominance — overlap/boundary scores worse than valid remnant]")
    # Run score tests via cargo test
    r = subprocess.run(
        ["cargo", "test", "--manifest-path", str(CARGO_MANIFEST),
         "test_invalid_layout_dominates_over_remnant_benefit"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("test_invalid_layout_dominates_over_remnant_benefit PASS (cargo test)")
    else:
        _fail("test_invalid_layout_dominates_over_remnant_benefit FAIL")
        print((r.stdout + r.stderr)[-200:], file=sys.stderr)


# ---------------------------------------------------------------------------
# Check 9: cargo test
# ---------------------------------------------------------------------------
def check_cargo_tests() -> None:
    print("\n[Check 9: cargo test (includes JG-19 score model tests)]")
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
# Check 10: JG-18 irregular candidate regression
# ---------------------------------------------------------------------------
def check_jg18_regression() -> None:
    print("\n[Check 10: JG-18 irregular candidate regression]")
    script = ROOT / "scripts" / "smoke_jagua_irregular_candidate_generation.py"
    if not script.is_file():
        _fail(f"JG-18 smoke not found: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("JG-18 irregular candidate smoke PASS")
    else:
        _fail(f"JG-18 smoke FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-200:], file=sys.stderr)


# ---------------------------------------------------------------------------
# Check 11: JG-17 boundary validation regression
# ---------------------------------------------------------------------------
def check_jg17_regression() -> None:
    print("\n[Check 11: JG-17 boundary validation regression]")
    script = ROOT / "scripts" / "smoke_jagua_irregular_boundary_validation.py"
    if not script.is_file():
        _fail(f"JG-17 smoke not found: {script}")
        return
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=str(ROOT),
    )
    if r.returncode == 0:
        _pass("JG-17 boundary validation smoke PASS")
    else:
        _fail(f"JG-17 smoke FAIL (exit={r.returncode})")
        if r.stderr.strip():
            print(r.stderr[-200:], file=sys.stderr)


# ---------------------------------------------------------------------------
# Check 12: backward compat — no cost_per_use in stock → sheet_cost_total = sheet_count
# ---------------------------------------------------------------------------
def check_backward_compat(solver_bin: str) -> None:
    print("\n[Check 12: Default cost_per_use backward compat (no cost_per_use → sheet_cost_total=sheet_count)]")
    input_dict = {
        "contract_version": "v1",
        "project_name": "jg19_compat",
        "solver_profile": PHASE1_PROFILE,
        "seed": 42,
        "time_limit_s": 5,
        "stocks": [{"id": "S", "quantity": 2, "width": 200, "height": 200}],
        "parts": [{"id": "A", "width": 150, "height": 150, "quantity": 2, "allowed_rotations_deg": [0]}],
    }
    out = _run_solver(solver_bin, input_dict)
    if out is None or out.get("score_breakdown") is None:
        _fail("compat check: no solver output or no score_breakdown")
        return
    sb = out["score_breakdown"]
    sheet_count = out.get("metrics", {}).get("sheet_count_used", 0)
    sct = sb.get("sheet_cost_total", -1.0)
    if abs(sct - float(sheet_count)) < 1e-9:
        _pass(f"backward compat: sheet_cost_total={sct} == sheet_count_used={sheet_count} (default cost_per_use=1.0)")
    else:
        _fail(f"backward compat FAIL: sheet_cost_total={sct} != sheet_count_used={sheet_count}")


def main() -> int:
    print("=== JG-19 Remnant Score Model V1 Smoke ===")

    data = check_fixture_exists()
    if data is not None:
        check_fixture_mixed_stocks(data)

    solver_bin = _resolve_solver_bin()
    if solver_bin is None:
        _fail("solver binary not found; skipping solver checks")
    else:
        print(f"\n  solver_bin: {solver_bin}")
        if data is not None:
            check_solver_runs_fixture(solver_bin, data)
            check_score_breakdown_fields(solver_bin, data)
            check_utilization(solver_bin, data)
        check_rect_regression(solver_bin)
        check_remnant_preference(solver_bin)
        check_invalid_layout_dominance(solver_bin)
        check_backward_compat(solver_bin)

    check_cargo_tests()
    check_jg18_regression()
    check_jg17_regression()

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    print("OVERALL: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
