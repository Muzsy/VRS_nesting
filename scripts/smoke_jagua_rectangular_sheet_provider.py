#!/usr/bin/env python3
"""JG-05 smoke: rectangular sheet provider contract verification.

Checks:
  1. smoke fixture (single sheet) — solver + exact validator PASS
  2. medium fixture (3-sheet multi-stock) — solver + exact validator PASS
  3. sheet_index range and mapping evidence (medium: indices 0,1,2 all used)
  4. Negative: injected invalid sheet_index rejected by validator
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

FIXTURE_SMOKE = ROOT / "tests/fixtures/egyedi_solver/jagua_rect_smoke.json"
FIXTURE_MEDIUM = ROOT / "tests/fixtures/egyedi_solver/jagua_rect_medium.json"

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
        _fail(f"VRS_SOLVER_BIN set but not executable: {explicit}")
        sys.exit(1)

    release_bin = ROOT / "rust/vrs_solver/target/release/vrs_solver"
    if release_bin.is_file() and os.access(release_bin, os.X_OK):
        return str(release_bin)

    which = shutil.which("vrs_solver")
    if which:
        return which

    print("Solver binary not found — building release binary...", flush=True)
    result = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(ROOT / "rust/vrs_solver/Cargo.toml")],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        _fail("cargo build failed")
        sys.exit(1)
    if release_bin.is_file():
        return str(release_bin)
    _fail("cargo build succeeded but binary not found")
    sys.exit(1)


def _run_solver(solver_bin: str, fixture: Path, run_dir: Path) -> dict:
    input_copy = run_dir / "solver_input.json"
    shutil.copy2(fixture, input_copy)
    output_path = run_dir / "solver_output.json"

    cmd = [solver_bin, "--input", str(input_copy), "--output", str(output_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"solver non-zero exit {result.returncode}: {result.stderr.strip()}")
    if not output_path.is_file():
        raise RuntimeError("solver output not written")
    return json.loads(output_path.read_text(encoding="utf-8"))


def _check_fixture(label: str, solver_bin: str, fixture: Path, run_dir: Path) -> dict | None:
    print(f"\n[{label}]")
    try:
        inp = json.loads(fixture.read_text(encoding="utf-8"))
        out = _run_solver(solver_bin, fixture, run_dir)
    except Exception as exc:
        _fail(f"solver run failed: {exc}")
        return None

    status = out.get("status")
    if status not in ("ok", "partial"):
        _fail(f"unexpected solver status: {status!r}")
        return None
    _pass(f"solver status={status}")

    try:
        validate_multi_sheet_output(inp, out)
        _pass("exact validator PASS")
    except Exception as exc:
        _fail(f"exact validator raised: {exc}")
        return None

    return out


def _check_sheet_index_range(label: str, output: dict, expected_count: int, expected_indices: set[int]) -> None:
    print(f"\n[{label}: sheet_index range]")
    placements = output.get("placements", [])
    indices = {p["sheet_index"] for p in placements if isinstance(p, dict)}
    sheet_count_used = output.get("metrics", {}).get("sheet_count_used", -1)

    if indices.issubset(set(range(expected_count))):
        _pass(f"all sheet indices in [0,{expected_count - 1}]: {sorted(indices)}")
    else:
        _fail(f"out-of-range sheet indices: {indices} (expected max={expected_count - 1})")

    if indices == expected_indices:
        _pass(f"sheet_index mapping correct: {sorted(indices)}")
    else:
        _fail(f"sheet_index mapping mismatch: got {sorted(indices)}, expected {sorted(expected_indices)}")

    if sheet_count_used == expected_count:
        _pass(f"sheet_count_used={sheet_count_used} matches expected={expected_count}")
    else:
        _fail(f"sheet_count_used={sheet_count_used}, expected={expected_count}")


def _negative_invalid_sheet_index(fixture_path: Path, valid_output: dict) -> None:
    print("\n[Negative: invalid sheet_index rejected]")
    inp = json.loads(fixture_path.read_text(encoding="utf-8"))

    # Inject an out-of-range sheet_index into the first placement
    tampered = json.loads(json.dumps(valid_output))
    if not tampered.get("placements"):
        _fail("no placements to tamper")
        return

    original_idx = tampered["placements"][0]["sheet_index"]
    tampered["placements"][0]["sheet_index"] = 9999

    try:
        validate_multi_sheet_output(inp, tampered)
        _fail(f"validator accepted invalid sheet_index=9999 (was {original_idx}) — should have raised")
    except (ValueError, Exception) as exc:
        _pass(f"validator correctly rejected invalid sheet_index=9999: {type(exc).__name__}: {exc}")


def main() -> int:
    print("=== JG-05 Rectangular Sheet Provider Smoke ===")

    for fixture in (FIXTURE_SMOKE, FIXTURE_MEDIUM):
        if not fixture.is_file():
            print(f"FATAL: fixture missing: {fixture}", file=sys.stderr)
            return 1

    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    with tempfile.TemporaryDirectory(prefix="jg05_smoke_") as tmp:
        tmp_path = Path(tmp)

        smoke_run = tmp_path / "smoke"
        smoke_run.mkdir()
        smoke_out = _check_fixture("smoke", solver_bin, FIXTURE_SMOKE, smoke_run)
        if smoke_out is not None:
            _check_sheet_index_range("smoke", smoke_out, expected_count=1, expected_indices={0})

        medium_run = tmp_path / "medium"
        medium_run.mkdir()
        medium_out = _check_fixture("medium", solver_bin, FIXTURE_MEDIUM, medium_run)
        if medium_out is not None:
            _check_sheet_index_range("medium", medium_out, expected_count=3, expected_indices={0, 1, 2})
            _negative_invalid_sheet_index(FIXTURE_MEDIUM, medium_out)

    print(f"\n=== RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL ===")
    if FAIL_COUNT == 0:
        print("OVERALL: PASS")
        return 0
    else:
        print("OVERALL: FAIL", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
